"""Scheduled and shared Uzum API sync logic."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from uuid import UUID
import threading

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.access import is_admin_subscription_status_active, subscription_active_reason
from app.db import SessionLocal, qname
from app.settings import get_settings
from app.deps import is_user_admin
from app.routes.imports import import_uzum_api_sync
from app.utils.tenant_shop_allowlist import register_uzum_api_dim_shops
from app.services.uzum_export import UzumApiClient
from app.services.uzum_shop_scope import prepare_sync_shop_scope
from app.services.uzum_api_helpers import (
    INVALID_UZUM_API_KEY,
    UZUM_KEY_INSUFFICIENT_ACCESS,
    UZUM_SHOP_UNAVAILABLE,
    UZUM_SYNC_REPORT_TYPES,
    normalize_api_key,
    uzum_error_means_invalid_key,
    validate_api_key,
    validate_api_key_shops,
)
from app.services.uzum_export import (
    ShopUnavailableError,
    UzumRateLimitError,
    build_report,
    build_xlsx_bytes,
)
from app.services.uzum_time import uz_now
from app.utils.sync_errors import split_sync_error

logger = logging.getLogger(__name__)

SyncStatus = Literal["running", "success", "failed", "skipped"]
SyncTrigger = Literal["scheduled", "manual"]

# Trial sync window matches KPI display clamp (60 calendar days inclusive).
TRIAL_SYNC_LOOKBACK_DAYS = 59

# Incremental API refresh after first successful connect (calendar days inclusive).
INCREMENTAL_SALES_LOOKBACK_DAYS = 29
INCREMENTAL_EXPENSES_LOOKBACK_DAYS = 1

_PAID_SYNC_PLANS = frozenset(
    {
        "gold",
        "gold_plan",
        "month_5",
        "month 5",
        "month5",
        "month_10",
        "month 10",
        "month10",
        "paid",
    }
)


def _user_plan(db: Session, user_id: UUID) -> str:
    row = db.execute(
        text(f"SELECT COALESCE(plan, 'trial') FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"),
        {"uid": str(user_id)},
    ).fetchone()
    return (row[0] or "trial").strip().lower() if row else "trial"


def user_uses_trial_sync_window(db: Session, user_id: UUID) -> bool:
    if is_user_admin(user_id, db):
        return False
    plan = _user_plan(db, user_id)
    if plan in _PAID_SYNC_PLANS:
        return False
    return plan in ("trial", "", None) or not plan


def resolve_uzum_sync_date_range(
    db: Session,
    user_id: UUID,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[str, str]:
    """Default sync range: trial users get last 60 days; paid users get YTD."""
    today = uz_now().date()
    end = (date_to or today.isoformat())[:10]

    if user_uses_trial_sync_window(db, user_id):
        start = (today - timedelta(days=TRIAL_SYNC_LOOKBACK_DAYS)).isoformat()
    elif date_from:
        start = date_from[:10]
    else:
        start = f"{today.year}-01-01"
    return start, end


@dataclass(frozen=True)
class UzumSyncFetchDates:
    mode: Literal["full", "incremental"]
    sales_from: str
    sales_to: str
    expenses_from: str
    expenses_to: str
    sales_replace_from: Optional[str] = None
    expenses_replace_from: Optional[str] = None


def user_has_prior_successful_api_sync(db: Session, user_id: UUID) -> bool:
    row = db.execute(
        text(f"""
            SELECT 1 FROM {qname("uzum_sync_log")}
            WHERE user_id = CAST(:uid AS uuid)
              AND status = 'success'
              AND upload_batch_id IS NOT NULL
            LIMIT 1
        """),
        {"uid": str(user_id)},
    ).fetchone()
    return row is not None


def resolve_full_sync_date_range_ytd(
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[str, str]:
    """Full sync from Jan 1 through today (admin panel)."""
    today = uz_now().date()
    end = (date_to or today.isoformat())[:10]
    start = date_from[:10] if date_from else f"{today.year}-01-01"
    return start, end


def resolve_sync_fetch_dates(
    db: Session,
    user_id: UUID,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    force_full_sync: bool = False,
) -> UzumSyncFetchDates:
    today = uz_now().date()
    end = (date_to or today.isoformat())[:10]

    if force_full_sync:
        start, resolved_end = resolve_full_sync_date_range_ytd(date_from=date_from, date_to=end)
        return UzumSyncFetchDates(
            mode="full",
            sales_from=start,
            sales_to=resolved_end,
            expenses_from=start,
            expenses_to=resolved_end,
        )

    if user_has_prior_successful_api_sync(db, user_id):
        sales_from = (today - timedelta(days=INCREMENTAL_SALES_LOOKBACK_DAYS)).isoformat()
        expenses_from = (today - timedelta(days=INCREMENTAL_EXPENSES_LOOKBACK_DAYS)).isoformat()
        return UzumSyncFetchDates(
            mode="incremental",
            sales_from=sales_from,
            sales_to=end,
            expenses_from=expenses_from,
            expenses_to=end,
            sales_replace_from=sales_from,
            expenses_replace_from=expenses_from,
        )

    start, resolved_end = resolve_uzum_sync_date_range(db, user_id, date_from=date_from, date_to=end)
    return UzumSyncFetchDates(
        mode="full",
        sales_from=start,
        sales_to=resolved_end,
        expenses_from=start,
        expenses_to=resolved_end,
    )


def is_phone_verified_for_sync(user_id: UUID, db: Session, phone: Optional[str], phone_verified_at) -> tuple[bool, str]:
    if is_user_admin(user_id, db):
        return True, ""
    if phone and str(phone).strip() and phone_verified_at is None:
        return False, "Телефон не подтверждён"
    return True, ""


def fetch_uzum_report_files(
    api_key: str,
    *,
    sales_date_from: str,
    sales_date_to: str,
    expenses_date_from: str,
    expenses_date_to: str,
    shop_ids: list[int],
    client: Optional[UzumApiClient] = None,
) -> tuple[dict[str, bytes], dict[str, str], list[str]]:
    files: dict[str, bytes] = {}
    file_names: dict[str, str] = {}
    warnings: list[str] = []
    uzum_client = client or UzumApiClient(api_key)

    report_dates: dict[str, tuple[str, str]] = {
        "sales": (sales_date_from, sales_date_to),
        "expenses": (expenses_date_from, expenses_date_to),
    }

    for report_type in UZUM_SYNC_REPORT_TYPES:
        kwargs: dict[str, Any] = {
            "shop_ids": shop_ids,
            "client": uzum_client,
        }
        if report_type in report_dates:
            df, dt = report_dates[report_type]
            kwargs["date_from"] = df
            kwargs["date_to"] = dt
        columns, rows, filename, report_warnings = build_report(
            report_type, api_key, **kwargs
        )
        files[report_type] = build_xlsx_bytes(report_type, columns, rows)
        file_names[report_type] = filename
        warnings.extend(report_warnings)

    return files, file_names, warnings


def _insert_sync_log(
    db: Session,
    *,
    user_id: UUID,
    started_at: datetime,
    status: SyncStatus,
    trigger: SyncTrigger,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    error_detail: Optional[str] = None,
    upload_batch_id: Optional[str] = None,
) -> str:
    row = db.execute(
        text(f"""
            INSERT INTO {qname("uzum_sync_log")} (
                user_id, started_at, finished_at, status,
                error_message, error_detail, upload_batch_id, trigger
            )
            VALUES (
                CAST(:user_id AS uuid), :started_at, :finished_at, :status,
                :error_message, :error_detail,
                CASE WHEN :upload_batch_id IS NULL THEN NULL ELSE CAST(:upload_batch_id AS uuid) END,
                :trigger
            )
            RETURNING id::text
        """),
        {
            "user_id": str(user_id),
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "error_message": error_message,
            "error_detail": error_detail,
            "upload_batch_id": upload_batch_id,
            "trigger": trigger,
        },
    ).fetchone()
    db.commit()
    return str(row[0])


def _insert_running_sync_log(
    db: Session,
    *,
    user_id: UUID,
    trigger: SyncTrigger,
) -> tuple[str, datetime]:
    started_at = datetime.now(timezone.utc)
    log_id = _insert_sync_log(
        db,
        user_id=user_id,
        started_at=started_at,
        finished_at=None,
        status="running",
        trigger=trigger,
    )
    return log_id, started_at


def _update_sync_log(
    db: Session,
    log_id: str,
    *,
    user_id: UUID,
    status: SyncStatus,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    error_detail: Optional[str] = None,
    upload_batch_id: Optional[str] = None,
) -> None:
    db.execute(
        text(f"""
            UPDATE {qname("uzum_sync_log")}
            SET
                status = :status,
                finished_at = :finished_at,
                error_message = :error_message,
                error_detail = :error_detail,
                upload_batch_id = CASE
                    WHEN :upload_batch_id IS NULL THEN NULL
                    ELSE CAST(:upload_batch_id AS uuid)
                END
            WHERE id = CAST(:log_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
        """),
        {
            "log_id": log_id,
            "user_id": str(user_id),
            "status": status,
            "finished_at": finished_at,
            "error_message": error_message,
            "error_detail": error_detail,
            "upload_batch_id": upload_batch_id,
        },
    )
    db.commit()


def _write_sync_log(
    db: Session,
    *,
    user_id: UUID,
    started_at: datetime,
    status: SyncStatus,
    trigger: SyncTrigger,
    log_id: Optional[str] = None,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
    error_detail: Optional[str] = None,
    upload_batch_id: Optional[str] = None,
) -> str:
    finished = finished_at if finished_at is not None else datetime.now(timezone.utc)
    if log_id:
        _update_sync_log(
            db,
            log_id,
            user_id=user_id,
            status=status,
            finished_at=finished if status != "running" else None,
            error_message=error_message,
            error_detail=error_detail,
            upload_batch_id=upload_batch_id,
        )
        return log_id
    return _insert_sync_log(
        db,
        user_id=user_id,
        started_at=started_at,
        finished_at=finished if status != "running" else None,
        status=status,
        trigger=trigger,
        error_message=error_message,
        error_detail=error_detail,
        upload_batch_id=upload_batch_id,
    )


def _log_sync_failure(
    db: Session,
    *,
    user_id: UUID,
    started_at: datetime,
    trigger: SyncTrigger,
    raw_error: str,
    log_id: Optional[str] = None,
) -> str:
    """Write failed sync log with short summary + full detail."""
    summary, detail = split_sync_error(raw_error)
    return _write_sync_log(
        db,
        user_id=user_id,
        started_at=started_at,
        status="failed",
        trigger=trigger,
        log_id=log_id,
        error_message=summary or raw_error[:300],
        error_detail=detail,
    )


def _set_last_api_sync_at(db: Session, user_id: UUID, ts: datetime) -> None:
    db.execute(
        text(f"""
            UPDATE {qname("users")}
            SET last_api_sync_at = :ts
            WHERE id = CAST(:user_id AS uuid)
        """),
        {"user_id": str(user_id), "ts": ts},
    )
    db.commit()


def _persist_uzum_api_key(db: Session, user_id: UUID, api_key: str) -> None:
    """Save API key after a successful manual sync (replaces previous key)."""
    db.execute(
        text(f"""
            UPDATE {qname("users")}
            SET uzum_seller_api_key = :key, updated_at = now()
            WHERE id = CAST(:user_id AS uuid)
        """),
        {"user_id": str(user_id), "key": api_key},
    )
    db.commit()


def run_uzum_sync_for_user(
    db: Session,
    user_id: UUID,
    *,
    api_key: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    trigger: SyncTrigger = "scheduled",
    skip_access_checks: bool = False,
    skip_key_validation: bool = False,
    log_id: Optional[str] = None,
    force_full_sync: bool = False,
) -> dict[str, Any]:
    """
    Fetch four Uzum reports and import them for one user.
    Writes uzum_sync_log and updates last_api_sync_at on success.
    If log_id is set, updates that running log row instead of inserting a new one.
    """
    started_at = datetime.now(timezone.utc)
    if log_id:
        row_started = db.execute(
            text(f"""
                SELECT started_at FROM {qname("uzum_sync_log")}
                WHERE id = CAST(:log_id AS uuid) AND user_id = CAST(:user_id AS uuid)
            """),
            {"log_id": log_id, "user_id": str(user_id)},
        ).fetchone()
        if row_started and row_started[0]:
            started_at = row_started[0]

    row = db.execute(
        text(f"""
            SELECT uzum_seller_api_key, is_active, trial_ends_at, phone, phone_verified_at
            FROM {qname("users")}
            WHERE id = CAST(:user_id AS uuid)
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    if not row:
        raise ValueError("User not found")

    stored_key, is_active, trial_ends_at, phone, phone_verified_at = row[0], row[1], row[2], row[3], row[4]
    key = normalize_api_key(api_key or (stored_key or ""))
    explicit_key = api_key is not None
    active_log_id = log_id

    def _finish(
        status: SyncStatus,
        *,
        error_message: Optional[str] = None,
        error_detail: Optional[str] = None,
        upload_batch_id: Optional[str] = None,
    ) -> str:
        return _write_sync_log(
            db,
            user_id=user_id,
            started_at=started_at,
            status=status,
            trigger=trigger,
            log_id=active_log_id,
            error_message=error_message,
            error_detail=error_detail,
            upload_batch_id=upload_batch_id,
        )

    if not key:
        finished_log_id = _finish("skipped", error_message="API-ключ отсутствует")
        return {"status": "skipped", "log_id": finished_log_id, "error": "API-ключ отсутствует"}

    if not skip_access_checks:
        sub_ok, sub_reason = subscription_active_reason(
            user_id, db, is_active=bool(is_active), trial_ends_at=trial_ends_at
        )
        if not sub_ok:
            finished_log_id = _finish("skipped", error_message=sub_reason)
            return {"status": "skipped", "log_id": finished_log_id, "error": sub_reason}

        phone_ok, phone_reason = is_phone_verified_for_sync(user_id, db, phone, phone_verified_at)
        if not phone_ok:
            finished_log_id = _finish("skipped", error_message=phone_reason)
            return {"status": "skipped", "log_id": finished_log_id, "error": phone_reason}

    fetch_dates = resolve_sync_fetch_dates(
        db,
        user_id,
        date_from=date_from,
        date_to=date_to,
        force_full_sync=force_full_sync,
    )

    access_probes = None
    if not skip_key_validation:
        key_valid, key_err, _ = validate_api_key_shops(key)
        if not key_valid:
            err = key_err or INVALID_UZUM_API_KEY
            finished_log_id = _finish("failed", error_message=err)
            return {"status": "failed", "log_id": finished_log_id, "error": err}

    if active_log_id is None and trigger == "manual":
        active_log_id, started_at = _insert_running_sync_log(
            db, user_id=user_id, trigger=trigger
        )

    try:
        client = UzumApiClient(key)
        accessible_shop_ids, _name_map = prepare_sync_shop_scope(
            client,
            db,
            user_id,
            prior_probes=access_probes,
        )
        register_uzum_api_dim_shops(
            db,
            user_id,
            client.list_shops(),
            set(accessible_shop_ids),
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        files, file_names, warnings = fetch_uzum_report_files(
            key,
            sales_date_from=fetch_dates.sales_from,
            sales_date_to=fetch_dates.sales_to,
            expenses_date_from=fetch_dates.expenses_from,
            expenses_date_to=fetch_dates.expenses_to,
            shop_ids=accessible_shop_ids,
            client=client,
        )
        result = import_uzum_api_sync(
            db,
            user_id,
            files,
            file_names,
            mode=fetch_dates.mode,
            sales_replace_from=fetch_dates.sales_replace_from,
            expenses_replace_from=fetch_dates.expenses_replace_from,
        )
    except HTTPException as exc:
        err = str(exc.detail) if exc.detail else str(exc)
        finished_log_id = _log_sync_failure(
            db,
            user_id=user_id,
            started_at=started_at,
            trigger=trigger,
            raw_error=err,
            log_id=active_log_id,
        )
        summary, _ = split_sync_error(err)
        return {"status": "failed", "log_id": finished_log_id, "error": summary or err}
    except ShopUnavailableError as exc:
        err = UZUM_SHOP_UNAVAILABLE
        finished_log_id = _finish(
            "failed",
            error_message=err,
            error_detail=str(exc),
        )
        logger.warning("Uzum sync shop unavailable for user %s: %s", user_id, exc)
        return {"status": "failed", "log_id": finished_log_id, "error": err}
    except UzumRateLimitError as exc:
        err = str(exc)
        finished_log_id = _finish("failed", error_message=err)
        return {"status": "failed", "log_id": finished_log_id, "error": err}
    except Exception as exc:
        err = str(exc)
        if uzum_error_means_invalid_key(exc):
            err = INVALID_UZUM_API_KEY
        finished_log_id = _log_sync_failure(
            db,
            user_id=user_id,
            started_at=started_at,
            trigger=trigger,
            raw_error=err,
            log_id=active_log_id,
        )
        logger.error("Uzum sync failed for user %s: %s", user_id, exc, exc_info=True)
        summary, _ = split_sync_error(err)
        return {"status": "failed", "log_id": finished_log_id, "error": summary or err}

    finished = datetime.now(timezone.utc)
    batch_id = result.get("upload_batch_id")
    finished_log_id = _finish(
        "success",
        upload_batch_id=str(batch_id) if batch_id else None,
    )
    if explicit_key:
        _persist_uzum_api_key(db, user_id, key)
    _set_last_api_sync_at(db, user_id, finished)

    if warnings:
        logger.info("Uzum sync warnings for user %s: %s", user_id, warnings)

    return {
        "status": "success",
        "log_id": finished_log_id,
        "upload_batch_id": batch_id,
        "imported": result.get("imported"),
        "date_from": fetch_dates.sales_from,
        "date_to": fetch_dates.sales_to,
        "sync_mode": fetch_dates.mode,
        "warnings": warnings,
    }


def list_users_with_api_key(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(f"""
            SELECT id, uzum_seller_api_key, is_active, trial_ends_at, phone, phone_verified_at, email
            FROM {qname("users")}
            WHERE uzum_seller_api_key IS NOT NULL
              AND trim(uzum_seller_api_key) <> ''
            ORDER BY id
        """)
    ).fetchall()
    return [
        {
            "id": row[0],
            "api_key": row[1],
            "is_active": row[2],
            "trial_ends_at": row[3],
            "phone": row[4],
            "phone_verified_at": row[5],
            "email": row[6],
        }
        for row in rows
    ]


def _scheduled_sync_one_user(
    db: Session,
    user: dict[str, Any],
    stats: dict[str, int],
) -> str:
    """
    Run scheduled sync for one user with eligibility checks.
    Returns status: success, failed, or skipped.

    «Не активен» in admin «Статус» column → silent skip (no uzum_sync_log row).
    «Активен» → sync with log; failed runs are retried once in the cycle.
    """
    user_id = user["id"]
    if not isinstance(user_id, UUID):
        user_id = UUID(str(user_id))

    if not is_admin_subscription_status_active(
        user_id, db, trial_ends_at=user["trial_ends_at"]
    ):
        logger.info(
            "Uzum scheduled sync: user %s not eligible (subscription status inactive)",
            user_id,
        )
        return "skipped"

    phone_ok, phone_reason = is_phone_verified_for_sync(
        user_id, db, user["phone"], user["phone_verified_at"]
    )
    if not phone_ok:
        _insert_sync_log(
            db,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="skipped",
            trigger="scheduled",
            error_message=phone_reason,
        )
        stats["skipped"] += 1
        logger.info("Uzum sync skipped user %s: %s", user_id, phone_reason)
        return "skipped"

    result = run_uzum_sync_for_user(
        db,
        user_id,
        api_key=user["api_key"],
        trigger="scheduled",
    )
    status = str(result.get("status", "failed"))
    if status in stats:
        stats[status] += 1
    logger.info("Uzum sync user %s finished: %s", user_id, status)
    return status


def user_has_running_manual_sync(db: Session, user_id: UUID) -> bool:
    row = db.execute(
        text(f"""
            SELECT 1 FROM {qname("uzum_sync_log")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND trigger = 'manual'
              AND status = 'running'
              AND started_at > now() - INTERVAL '30 minutes'
            LIMIT 1
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    return row is not None


def get_uzum_sync_log_status(db: Session, user_id: UUID, sync_id: str) -> Optional[dict[str, Any]]:
    row = db.execute(
        text(f"""
            SELECT
                id::text,
                status,
                started_at,
                finished_at,
                error_message,
                error_detail,
                upload_batch_id::text
            FROM {qname("uzum_sync_log")}
            WHERE id = CAST(:sync_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
        """),
        {"sync_id": sync_id, "user_id": str(user_id)},
    ).fetchone()
    if not row:
        return None
    return {
        "sync_id": row[0],
        "status": row[1],
        "started_at": row[2].isoformat() if row[2] else None,
        "finished_at": row[3].isoformat() if row[3] else None,
        "error_message": row[4],
        "error_detail": row[5],
        "upload_batch_id": row[6],
    }


def run_manual_uzum_sync_job(
    log_id: str,
    user_id: UUID,
    *,
    api_key: str,
    date_from: str,
    date_to: str,
) -> None:
    """Background worker for manual user-initiated Uzum sync."""
    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {get_settings().DB_SCHEMA}, public"))
        run_uzum_sync_for_user(
            db,
            user_id,
            api_key=api_key,
            date_from=date_from,
            date_to=date_to,
            trigger="manual",
            log_id=log_id,
            skip_key_validation=True,
        )
    except Exception as exc:
        logger.error("Manual uzum sync job failed for user %s log %s: %s", user_id, log_id, exc, exc_info=True)
        try:
            _log_sync_failure(
                db,
                user_id=user_id,
                started_at=datetime.now(timezone.utc),
                trigger="manual",
                raw_error=str(exc),
                log_id=log_id,
            )
        except Exception:
            logger.error("Failed to mark uzum sync log %s as failed", log_id, exc_info=True)
    finally:
        db.close()


def enqueue_manual_uzum_sync_job(
    log_id: str,
    user_id: UUID,
    *,
    api_key: str,
    date_from: str,
    date_to: str,
) -> None:
    """Run manual sync in a daemon thread (used from FastAPI BackgroundTasks)."""
    threading.Thread(
        target=run_manual_uzum_sync_job,
        args=(log_id, user_id),
        kwargs={
            "api_key": api_key,
            "date_from": date_from,
            "date_to": date_to,
        },
        daemon=True,
        name=f"uzum-manual-sync-{log_id}",
    ).start()


def run_admin_uzum_sync_for_tenant(tenant_id: UUID) -> None:
    """Background job: admin-triggered Uzum sync for one tenant."""
    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {get_settings().DB_SCHEMA}, public"))
        row = db.execute(
            text(f"""
                SELECT uzum_seller_api_key
                FROM {qname("users")}
                WHERE id = CAST(:uid AS uuid)
            """),
            {"uid": str(tenant_id)},
        ).fetchone()
        if not row:
            logger.warning("Admin uzum sync: tenant %s not found", tenant_id)
            return

        api_key = normalize_api_key(row[0] or "")
        if not api_key:
            logger.warning("Admin uzum sync: tenant %s has no API key", tenant_id)
            return

        sync_result = run_uzum_sync_for_user(
            db,
            tenant_id,
            api_key=api_key,
            trigger="manual",
            force_full_sync=True,
        )
        logger.info(
            "Admin uzum sync finished for tenant %s: %s",
            tenant_id,
            sync_result.get("status"),
        )
    except Exception as exc:
        logger.error(
            "Admin uzum sync failed for tenant %s: %s",
            tenant_id,
            exc,
            exc_info=True,
        )
    finally:
        db.close()


_admin_uzum_sync_lock = threading.Lock()


def schedule_admin_uzum_sync_for_tenant(tenant_id: UUID) -> tuple[bool, str]:
    """
    Run admin uzum sync in a daemon thread so the API worker stays responsive.
    Only one admin sync at a time.
    """
    if not _admin_uzum_sync_lock.acquire(blocking=False):
        return (
            False,
            "Другая синхронизация Uzum уже выполняется. Подождите несколько минут и попробуйте снова.",
        )

    def _job() -> None:
        try:
            run_admin_uzum_sync_for_tenant(tenant_id)
        finally:
            _admin_uzum_sync_lock.release()

    threading.Thread(
        target=_job,
        name=f"admin-uzum-sync-{tenant_id}",
        daemon=True,
    ).start()
    return (
        True,
        "Синхронизация запущена. Результат появится в логах через несколько минут.",
    )


def run_scheduled_sync_cycle() -> None:
    """Sync all eligible users sequentially. Safe to call from background scheduler."""
    settings = get_settings()
    if not settings.UZUM_SCHEDULED_SYNC_ENABLED:
        logger.debug("Uzum scheduled sync disabled (UZUM_SCHEDULED_SYNC_ENABLED=false)")
        return

    from app.services.uzum_scheduler import try_acquire_cycle_lock, release_cycle_lock

    if not try_acquire_cycle_lock():
        logger.warning("Uzum scheduled sync skipped: previous cycle still running")
        return

    db = SessionLocal()
    try:
        db.execute(text(f"SET search_path TO {get_settings().DB_SCHEMA}, public"))
        users = list_users_with_api_key(db)
        logger.info("Uzum scheduled sync cycle started: %s users with API key", len(users))

        stats = {"success": 0, "failed": 0, "skipped": 0}
        failed_for_retry: list[dict[str, Any]] = []
        user_pause = max(0.0, settings.UZUM_SCHEDULED_USER_PAUSE_SEC)

        for idx, user in enumerate(users):
            if idx > 0 and user_pause > 0:
                logger.info(
                    "Uzum scheduled sync: pause %.0fs before next user (%s/%s)",
                    user_pause,
                    idx + 1,
                    len(users),
                )
                time.sleep(user_pause)
            status = _scheduled_sync_one_user(db, user, stats)
            if status == "failed":
                failed_for_retry.append(user)

        if failed_for_retry:
            retry_pause = max(0.0, settings.UZUM_SCHEDULED_RETRY_PAUSE_SEC)
            if retry_pause > 0:
                logger.info(
                    "Uzum scheduled sync: pause %.0fs before retry pass (%s users)",
                    retry_pause,
                    len(failed_for_retry),
                )
                time.sleep(retry_pause)
            logger.info(
                "Uzum scheduled sync retry pass started: %s users after failed first pass",
                len(failed_for_retry),
            )
            retry_recovered = 0
            retry_still_failed = 0
            for user in failed_for_retry:
                result = run_uzum_sync_for_user(
                    db,
                    user["id"] if isinstance(user["id"], UUID) else UUID(str(user["id"])),
                    api_key=user["api_key"],
                    trigger="scheduled",
                )
                status = str(result.get("status", "failed"))
                user_id = user["id"]
                if status == "success":
                    retry_recovered += 1
                    stats["success"] += 1
                    stats["failed"] -= 1
                    logger.info("Uzum sync retry succeeded for user %s", user_id)
                else:
                    retry_still_failed += 1
                    logger.info("Uzum sync retry still failed for user %s: %s", user_id, status)
            logger.info(
                "Uzum scheduled sync retry pass finished: recovered=%s still_failed=%s",
                retry_recovered,
                retry_still_failed,
            )

        logger.info(
            "Uzum scheduled sync cycle finished: success=%s failed=%s skipped=%s",
            stats.get("success", 0),
            stats.get("failed", 0),
            stats.get("skipped", 0),
        )
    except Exception as exc:
        logger.error("Uzum scheduled sync cycle error: %s", exc, exc_info=True)
    finally:
        db.close()
        release_cycle_lock()
