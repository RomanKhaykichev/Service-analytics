import re
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, qname
from app.deps import require_user

router = APIRouter()


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


@router.get("/notifications/expenses")
async def get_expense_notifications(
    user_id: UUID = Depends(require_user),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Return bell notifications from expenses-report rows.
    Source columns: Услуга, Дата списания, Сумма (сумы).
    """
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
        LIMIT :limit
        """
    )
    rows = db.execute(
        query,
        {
            "user_id": str(user_id),
            "limit": limit,
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
