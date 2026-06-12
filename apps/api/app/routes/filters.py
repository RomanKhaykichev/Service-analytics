"""Filter-related endpoints (date bounds for calendar, etc.)."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings

router = APIRouter()


def _last_data_update_at(db: Session, user_id: str) -> Optional[str]:
    """Последнее успешное обновление данных (last_api_sync_at или upload_batch)."""
    schema = get_settings().DB_SCHEMA
    try:
        has_last_sync = db.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'users' AND column_name = 'last_api_sync_at'
            """),
            {"schema": schema},
        ).fetchone()
        if has_last_sync:
            row = db.execute(
                text(f"""
                    SELECT last_api_sync_at FROM {qname("users")}
                    WHERE id = CAST(:user_id AS uuid)
                """),
                {"user_id": user_id},
            ).fetchone()
            if row and row[0] is not None:
                return row[0].isoformat()

        has_created_at = db.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'upload_batch' AND column_name = 'created_at'
            """),
            {"schema": schema},
        ).fetchone()
        if not has_created_at:
            return None

        has_updated_at = db.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'upload_batch' AND column_name = 'updated_at'
            """),
            {"schema": schema},
        ).fetchone()
        ts_expr = "COALESCE(updated_at, created_at)" if has_updated_at else "created_at"
        row = db.execute(
            text(f"""
                SELECT MAX({ts_expr})
                FROM {qname("upload_batch")}
                WHERE user_id = CAST(:user_id AS uuid)
                  AND status = 'success'
            """),
            {"user_id": user_id},
        ).fetchone()
        if row and row[0] is not None:
            return row[0].isoformat()
    except Exception:
        return None
    return None


@router.get("/filters/date-bounds")
async def get_date_bounds(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return min/max date for the current user: first from fact_sales.date_created,
    if no sales then from fact_expenses.date_written_off. Used by frontend for calendar.
    If no data at all: min_date and max_date are null.
    Also returns last_updated_at — timestamp of the last successful data import.
    """
    uid = str(user_id)
    last_updated_at = _last_data_update_at(db, uid)
    # 1) Try fact_sales (sells-report "Дата создания")
    q_sales = text(
        f"""
        SELECT MIN(date_created::date), MAX(date_created::date)
        FROM {qname("fact_sales")}
        WHERE user_id = CAST(:user_id AS uuid)
        """
    )
    row = db.execute(q_sales, {"user_id": uid}).fetchone()
    if row and (row[0] is not None or row[1] is not None):
        min_d = row[0].isoformat() if row[0] else None
        max_d = row[1].isoformat() if row[1] else None
        return {"min_date": min_d, "max_date": max_d, "last_updated_at": last_updated_at}
    # 2) Fallback: fact_expenses (expenses-report "Дата списания")
    q_exp = text(
        f"""
        SELECT MIN(date_written_off::date), MAX(date_written_off::date)
        FROM {qname("fact_expenses")}
        WHERE user_id = CAST(:user_id AS uuid)
        """
    )
    row = db.execute(q_exp, {"user_id": uid}).fetchone()
    if row and (row[0] is not None or row[1] is not None):
        min_d = row[0].isoformat() if row[0] else None
        max_d = row[1].isoformat() if row[1] else None
        return {"min_date": min_d, "max_date": max_d, "last_updated_at": last_updated_at}
    return {"min_date": None, "max_date": None, "last_updated_at": last_updated_at}
