import logging
import re
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, qname
from app.deps import require_user
from app.services.uzum_time import UZ_TZ, uz_now

logger = logging.getLogger(__name__)

router = APIRouter()

NOTIFICATION_INITIAL_LOOKBACK_DAYS = 14


def _extract_service_number(service: str) -> str | None:
    """Extract invoice/order number from RU or UZ Uzum service names."""
    match = re.search(r"№\s*([0-9]+)", service)
    if match:
        return match.group(1)

    match = re.search(r"^\s*([0-9]+)\s*-?\s*sonli\b", service, flags=re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _classify_service(service: str) -> str:
    service_upper = service.upper()
    service_lower = service.lower()

    if "ОПЛАТА ЗА УСЛУГИ ХРАНЕНИЯ СОБРАННОГО ВОЗВРАТА ПО НАКЛАДНОЙ" in service_upper:
        return "storage_return"
    if "yig" in service_lower and "qaytarishni saqlash" in service_lower:
        return "storage_return"

    if "ОБРАБОТКА НАКЛАДНОЙ УТИЛИЗАЦИИ" in service_upper:
        return "utilization_invoice"

    if "ОБРАБОТКА ВОЗВРАТА СО СКЛАДА ПО НАКЛАДНОЙ" in service_upper:
        return "warehouse_return"
    if "ombordan qaytarishni qayta ishlash" in service_lower:
        return "warehouse_return"

    if "ШТРАФ ЗА РАСХОЖДЕНИЯ ПРИ ПРИЕМКЕ НАКЛАДНОЙ" in service_upper:
        return "fine_discrepancy"
    if "qabuldagi tafovut" in service_lower and "jarima" in service_lower:
        return "fine_discrepancy"

    if "ШТРАФ" in service_upper or "jarima" in service_lower:
        return "fine"

    return "other"


def _user_last_api_sync_at(db: Session, user_id: UUID):
    row = db.execute(
        text(f"""
            SELECT last_api_sync_at
            FROM {qname("users")}
            WHERE id = CAST(:user_id AS uuid)
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _first_successful_api_sync_finished_at(db: Session, user_id: UUID):
    """First successful Uzum API sync for notification fallback."""
    row = db.execute(
        text(f"""
            SELECT finished_at
            FROM {qname("uzum_sync_log")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND status = 'success'
              AND upload_batch_id IS NOT NULL
              AND finished_at IS NOT NULL
            ORDER BY finished_at ASC
            LIMIT 1
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    return row[0] if row else None


def _latest_full_sync_finished_at(db: Session, user_id: UUID):
    """Most recent successful full API sync (manual_full, scheduled_full, etc.)."""
    row = db.execute(
        text(f"""
            SELECT finished_at
            FROM {qname("uzum_sync_log")}
            WHERE user_id = CAST(:user_id AS uuid)
              AND status = 'success'
              AND upload_batch_id IS NOT NULL
              AND finished_at IS NOT NULL
              AND trigger LIKE '%\_full' ESCAPE '\\'
            ORDER BY finished_at DESC
            LIMIT 1
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    return row[0] if row else None


def _notification_expenses_min_date(db: Session, user_id: UUID) -> date:
    """
    Expense notifications window:
    - On full API load (first connect or admin full sync): last 14 days before that sync.
    - On later incremental syncs: same anchor — new rows with newer written_off dates appear.
    """
    baseline_sync = _latest_full_sync_finished_at(db, user_id)
    if baseline_sync is None:
        baseline_sync = _first_successful_api_sync_finished_at(db, user_id)
    if baseline_sync is None:
        return uz_now().date() - timedelta(days=NOTIFICATION_INITIAL_LOOKBACK_DAYS)
    sync_dt = baseline_sync.astimezone(UZ_TZ) if baseline_sync.tzinfo else baseline_sync.replace(tzinfo=UZ_TZ)
    return sync_dt.date() - timedelta(days=NOTIFICATION_INITIAL_LOOKBACK_DAYS)


@router.get("/notifications/expenses")
async def get_expense_notifications(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return bell notifications from expenses-report rows.
    Source columns: Услуга, Дата списания, Сумма (сумы).
    After first API sync: only expenses from the last 14 days before that sync onward.
    """
    min_written_off_date = _notification_expenses_min_date(db, user_id)
    query = text(
        f"""
        SELECT
            COUNT(*) OVER() AS total_count,
            md5(concat_ws(
                '|',
                COALESCE(fe.operation_id, ''),
                COALESCE(fe.service, ''),
                COALESCE(fe.date_written_off::date::text, ''),
                COALESCE(fe.amount_sum::text, '')
            )) AS id,
            fe.service,
            fe.date_written_off::date AS written_off_date,
            COALESCE(fe.amount_sum, 0)::double precision AS amount_sum
        FROM {qname("fact_expenses")} fe
        WHERE fe.user_id = CAST(:user_id AS uuid)
          AND fe.date_written_off IS NOT NULL
          AND fe.date_written_off::date >= CAST(:min_written_off_date AS date)
          AND (
            upper(COALESCE(fe.service, '')) LIKE :storage_return_service
            OR upper(COALESCE(fe.service, '')) LIKE :fine_service
            OR upper(COALESCE(fe.service, '')) LIKE :warehouse_return_service
            OR upper(COALESCE(fe.service, '')) LIKE :utilization_invoice_service
            OR lower(COALESCE(fe.service, '')) LIKE :uz_storage_return_service
            OR lower(COALESCE(fe.service, '')) LIKE :uz_fine_service
            OR lower(COALESCE(fe.service, '')) LIKE :uz_warehouse_return_service
          )
        ORDER BY fe.date_written_off::date DESC, fe.amount_sum DESC, fe.service ASC
        """
    )
    rows = db.execute(
        query,
        {
            "user_id": str(user_id),
            "min_written_off_date": min_written_off_date.isoformat(),
            "storage_return_service": "%ОПЛАТА ЗА УСЛУГИ ХРАНЕНИЯ СОБРАННОГО ВОЗВРАТА ПО НАКЛАДНОЙ%",
            "fine_service": "%ШТРАФ%",
            "warehouse_return_service": "%ОБРАБОТКА ВОЗВРАТА СО СКЛАДА ПО НАКЛАДНОЙ%",
            "utilization_invoice_service": "%ОБРАБОТКА НАКЛАДНОЙ УТИЛИЗАЦИИ%",
            "uz_storage_return_service": "%yig%ilgan qaytarishni saqlash%",
            "uz_fine_service": "%jarima%",
            "uz_warehouse_return_service": "%ombordan qaytarishni qayta ishlash%",
        },
    ).fetchall()

    items = [
        {
            "id": row.id,
            "service": row.service or "",
            "service_key": _classify_service(row.service or ""),
            "service_number": _extract_service_number(row.service or ""),
            "written_off_date": row.written_off_date.isoformat() if row.written_off_date else None,
            "amount_sum": float(row.amount_sum or 0),
        }
        for row in rows
    ]
    total_count = int(rows[0].total_count) if rows else 0
    return {"items": items, "count": total_count}


@router.get("/notifications/ratings")
async def get_rating_notifications(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return bell notifications for products with rating below 4.5.
    Source: left-out-report_old (stg_leftout_old.data -> «Рейтинг»), latest batch per user.
    Excludes archived products: only items with a shop in seller-storage (same as products table).
    On each API sync the catalog is refreshed; new alerts appear when rating changes (id includes rating).
    """
    try:
        rating_updated_at = _user_last_api_sync_at(db, user_id)
        query = text(
        f"""
        WITH latest_batch AS (
            SELECT sl.upload_batch_id
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
            ORDER BY sl.upload_batch_id DESC NULLS LAST
            LIMIT 1
        ),
        storage_by_barcode AS (
            SELECT
                COALESCE(
                    fss.barcode_norm,
                    NULLIF(trim(regexp_replace(COALESCE(fss.barcode, ''), '\\s+', '', 'g')), '')
                ) AS barcode_norm,
                MAX(NULLIF(trim(fss.shop_raw), '')) AS shop
            FROM {qname("fact_storage_snapshot")} fss
            WHERE fss.user_id = CAST(:user_id AS uuid)
              AND (fss.barcode_norm IS NOT NULL OR fss.barcode IS NOT NULL)
            GROUP BY
                fss.user_id,
                COALESCE(
                    fss.barcode_norm,
                    NULLIF(trim(regexp_replace(COALESCE(fss.barcode, ''), '\\s+', '', 'g')), '')
                )
            HAVING COALESCE(MAX(NULLIF(trim(fss.shop_raw), '')), '') <> ''
        ),
        product_rows AS (
            SELECT
                NULLIF(TRIM(COALESCE(sl.data->>'ID товара', sl.data->>'Tovar identifikatori')), '') AS product_id,
                NULLIF(TRIM(COALESCE(sl.data->>'Наименование', sl.data->>'Название товара')), '') AS product_name,
                CASE
                    WHEN TRIM(COALESCE(sl.data->>'Рейтинг', '')) ~ '^[0-9]+([.,][0-9]+)?$'
                        THEN REPLACE(TRIM(sl.data->>'Рейтинг'), ',', '.')::double precision
                    ELSE NULL
                END AS rating,
                CASE
                    WHEN TRIM(COALESCE(sl.data->>'Количество отзывов', '')) ~ '^[0-9]+$'
                        THEN TRIM(sl.data->>'Количество отзывов')::int
                    ELSE NULL
                END AS feedback_quantity,
                NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') AS barcode_norm
            FROM {qname("stg_leftout_old")} sl
            INNER JOIN latest_batch lb ON sl.upload_batch_id = lb.upload_batch_id
            WHERE sl.user_id = CAST(:user_id AS uuid)
        ),
        active_product_rows AS (
            SELECT pr.*
            FROM product_rows pr
            INNER JOIN storage_by_barcode sb ON sb.barcode_norm = pr.barcode_norm
            WHERE pr.product_id IS NOT NULL
              AND pr.barcode_norm IS NOT NULL
        ),
        grouped AS (
            SELECT
                product_id,
                MAX(product_name) AS product_name,
                MAX(rating) AS rating,
                MAX(feedback_quantity) AS feedback_quantity
            FROM active_product_rows
            WHERE rating IS NOT NULL
              AND rating > 0
              AND rating < 4.5
            GROUP BY product_id
        )
        SELECT
            COUNT(*) OVER() AS total_count,
            md5(concat('rating|', product_id, '|', round(rating::numeric, 1)::text)) AS id,
            product_id,
            product_name,
            rating,
            feedback_quantity
        FROM grouped
        ORDER BY rating ASC, product_name ASC NULLS LAST, product_id ASC
        """
        )
        rows = db.execute(query, {"user_id": str(user_id)}).fetchall()
    except Exception as exc:
        logger.warning("get_rating_notifications failed for user %s: %s", user_id, exc)
        return {"items": [], "count": 0}

    updated_at_iso = (
        rating_updated_at.isoformat()
        if rating_updated_at is not None
        else None
    )
    items = [
        {
            "id": row.id,
            "product_id": row.product_id,
            "product_name": row.product_name or "",
            "rating": float(row.rating) if row.rating is not None else None,
            "feedback_quantity": int(row.feedback_quantity) if row.feedback_quantity is not None else None,
            "updated_at": updated_at_iso,
        }
        for row in rows
    ]
    total_count = int(rows[0].total_count) if rows else 0
    return {"items": items, "count": total_count}
