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
    Return min/max date from fact_sales.date_created (sells-report "Дата создания") for the current user.
    Used by frontend to restrict calendar picker to available data range.
    No shop filter — bounds are global for all sales.
    If no data: min_date and max_date are null.
    """
    q = text(
        f"""
        SELECT
          MIN(date_created::date) AS min_date,
          MAX(date_created::date) AS max_date
        FROM {qname("fact_sales")}
        WHERE user_id = CAST(:user_id AS uuid)
        """
    )
    row = db.execute(q, {"user_id": str(user_id)}).fetchone()
    if not row or (row[0] is None and row[1] is None):
        return {"min_date": None, "max_date": None}
    min_d = row[0].isoformat() if row[0] else None
    max_d = row[1].isoformat() if row[1] else None
    return {"min_date": min_d, "max_date": max_d}
