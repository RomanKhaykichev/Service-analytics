"""Filter-related endpoints (date bounds for calendar, etc.)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from app.db import get_db, qname
from app.deps import require_user

router = APIRouter()


@router.get("/filters/date-bounds")
async def get_date_bounds(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return min/max date for the current user: first from fact_sales.date_created,
    if no sales then from fact_expenses.date_written_off. Used by frontend for calendar.
    If no data at all: min_date and max_date are null.
    """
    uid = str(user_id)
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
        return {"min_date": min_d, "max_date": max_d}
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
        return {"min_date": min_d, "max_date": max_d}
    return {"min_date": None, "max_date": None}
