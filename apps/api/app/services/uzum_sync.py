"""Scheduled and shared Uzum API sync logic."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID
import threading

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.access import _as_utc_aware, _now_utc
from app.db import SessionLocal, qname
from app.deps import is_user_admin
from app.routes.imports import import_uzum_api_sync
from app.services.uzum_api_helpers import (
    INVALID_UZUM_API_KEY,
    UZUM_SYNC_REPORT_TYPES,
    normalize_api_key,
    uzum_error_means_invalid_key,
    validate_api_key,
)
from app.services.uzum_export import (
    ShopUnavailableError,
    UzumRateLimitError,
    build_report,
    build_xlsx_bytes,
)
from app.services.uzum_time import uz_now
from app.settings import get_settings
from app.utils.sync_errors import split_sync_error

logger = logging.getLogger(__name__)

SyncStatus = Literal["success", "failed", "skipped"]
SyncTrigger = Literal["scheduled", "manual"]


def _year_to_date_range() -> tuple[str, str]:
    today = uz_now().date()
    return f"{today.year}-01-01", today.isoformat()


def is_subscription_active(
    user_id: UUID,
    db: Session,
    *,
    is_active: bool,
    trial_ends_at: Optional[datetime],
) -> tuple[bool, str]:
    """Mirror UI «Активен»: admin, trial not expired, or open-ended access."""
    if not is_active:
        return False, "Аккаунт заблокирован"
    if is_user_admin(user_id, db):
        return True, ""
    if trial_ends_at is None:
        return True, ""
    end = _as_utc_aware(trial_ends_at) if isinstance(trial_ends_at, datetime) else None
    if end is None:
        return True, ""
    if end <= _now_utc():
        return False, "Подписка не активна"
    return True, ""


def is_phone_verified_for_sync(user_id: UUID, db: Session, phone: Optional[str], phone_verified_at) -> tuple[bool, str]:
    if is_user_admin(user_id, db):
        return True, ""
    if phone and str(phone).strip() and phone_verified_at is None:
        return False, "Телефон не подтверждён"
    return True, ""


def fetch_uzum_report_files(
    api_key: str,
    *,
    date_from: str,
    date_to: str,
) -> tuple[dict[str, bytes], dict[str, str], list[str]]:
    files: dict[str, bytes] = {}
    file_names: dict[str, str] = {}
    warnings: list[str] = []

    for report_type in UZUM_SYNC_REPORT_TYPES:
        kwargs: dict[str, Any] = {}
        if report_type in ("sales", "expenses"):
            kwargs["date_from"] = date_from
            kwargs["date_to"] = date_to
        columns, rows, filename, report_warnings = build_report(report_type, api_key, **kwargs)
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


def _log_sync_failure(
    db: Session,
    *,
    user_id: UUID,
    started_at: datetime,
    trigger: SyncTrigger,
    raw_error: str,
) -> str:
    """Write failed sync log with short summary + full detail."""
    summary, detail = split_sync_error(raw_error)
    return _insert_sync_log(
        db,
        user_id=user_id,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc),
        status="failed",
        trigger=trigger,
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


def run_uzum_sync_for_user(
    db: Session,
    user_id: UUID,
    *,
    api_key: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    trigger: SyncTrigger = "scheduled",
    skip_access_checks: bool = False,
) -> dict[str, Any]:
    """
    Fetch four Uzum reports and import them for one user.
    Writes uzum_sync_log and updates last_api_sync_at on success.
    """
    started_at = datetime.now(timezone.utc)
    log_id: Optional[str] = None

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
    if not key:
        log_id = _insert_sync_log(
            db,
            user_id=user_id,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
            status="skipped",
            trigger=trigger,
            error_message="API-ключ отсутствует",
        )
        return {"status": "skipped", "log_id": log_id, "error": "API-ключ отсутствует"}

    if not skip_access_checks:
        sub_ok, sub_reason = is_subscription_active(
            user_id, db, is_active=bool(is_active), trial_ends_at=trial_ends_at
        )
        if not sub_ok:
            log_id = _insert_sync_log(
                db,
                user_id=user_id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                status="skipped",
                trigger=trigger,
                error_message=sub_reason,
            )
            return {"status": "skipped", "log_id": log_id, "error": sub_reason}

        phone_ok, phone_reason = is_phone_verified_for_sync(user_id, db, phone, phone_verified_at)
        if not phone_ok:
            log_id = _insert_sync_log(
                db,
                user_id=user_id,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                status="skipped",
                trigger=trigger,
                error_message=phone_reason,
            )
            return {"status": "skipped", "log_id": log_id, "error": phone_reason}

    df, dt = _year_to_date_range()
    date_from = date_from or df
    date_to = date_to or dt

    key_valid, _, _ = validate_api_key(key)
    if not key_valid:
        finished = datetime.now(timezone.utc)
        log_id = _insert_sync_log(
            db,
            user_id=user_id,
            started_at=started_at,
            finished_at=finished,
            status="failed",
            trigger=trigger,
            error_message=INVALID_UZUM_API_KEY,
        )
        return {"status": "failed", "log_id": log_id, "error": INVALID_UZUM_API_KEY}

    try:
        files, file_names, warnings = fetch_uzum_report_files(key, date_from=date_from, date_to=date_to)
        result = import_uzum_api_sync(db, user_id, files, file_names)
    except HTTPException as exc:
        err = str(exc.detail) if exc.detail else str(exc)
        log_id = _log_sync_failure(
            db, user_id=user_id, started_at=started_at, trigger=trigger, raw_error=err
        )
        summary, _ = split_sync_error(err)
        return {"status": "failed", "log_id": log_id, "error": summary or err}
    except ShopUnavailableError as exc:
        finished = datetime.now(timezone.utc)
        err = INVALID_UZUM_API_KEY
        log_id = _insert_sync_log(
            db,
            user_id=user_id,
            started_at=started_at,
            finished_at=finished,
            status="failed",
            trigger=trigger,
            error_message=err,
        )
        logger.warning("Uzum sync shop unavailable for user %s: %s", user_id, exc)
        return {"status": "failed", "log_id": log_id, "error": err}
    except UzumRateLimitError as exc:
        finished = datetime.now(timezone.utc)
        err = str(exc)
        log_id = _insert_sync_log(
            db,
            user_id=user_id,
            started_at=started_at,
            finished_at=finished,
            status="failed",
            trigger=trigger,
            error_message=err,
        )
        return {"status": "failed", "log_id": log_id, "error": err}
    except Exception as exc:
        err = str(exc)
        if uzum_error_means_invalid_key(exc):
            err = INVALID_UZUM_API_KEY
        log_id = _log_sync_failure(
            db, user_id=user_id, started_at=started_at, trigger=trigger, raw_error=err
        )
        logger.error("Uzum sync failed for user %s: %s", user_id, exc, exc_info=True)
        summary, _ = split_sync_error(err)
        return {"status": "failed", "log_id": log_id, "error": summary or err}

    finished = datetime.now(timezone.utc)
    batch_id = result.get("upload_batch_id")
    log_id = _insert_sync_log(
        db,
        user_id=user_id,
        started_at=started_at,
        finished_at=finished,
        status="success",
        trigger=trigger,
        upload_batch_id=str(batch_id) if batch_id else None,
    )
    _set_last_api_sync_at(db, user_id, finished)

    if warnings:
        logger.info("Uzum sync warnings for user %s: %s", user_id, warnings)

    return {
        "status": "success",
        "log_id": log_id,
        "upload_batch_id": batch_id,
        "imported": result.get("imported"),
        "date_from": date_from,
        "date_to": date_to,
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
    """
    user_id = user["id"]
    if not isinstance(user_id, UUID):
        user_id = UUID(str(user_id))

    sub_ok, sub_reason = is_subscription_active(
        user_id,
        db,
        is_active=bool(user["is_active"]),
        trial_ends_at=user["trial_ends_at"],
    )
    if not sub_ok:
        _insert_sync_log(
            db,
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="skipped",
            trigger="scheduled",
            error_message=sub_reason,
        )
        stats["skipped"] += 1
        logger.info("Uzum sync skipped user %s: %s", user_id, sub_reason)
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
        skip_access_checks=True,
    )
    status = str(result.get("status", "failed"))
    if status in stats:
        stats[status] += 1
    logger.info("Uzum sync user %s finished: %s", user_id, status)
    return status


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
            skip_access_checks=True,
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

        for user in users:
            status = _scheduled_sync_one_user(db, user, stats)
            if status == "failed":
                failed_for_retry.append(user)

        if failed_for_retry:
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
                    skip_access_checks=True,
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
