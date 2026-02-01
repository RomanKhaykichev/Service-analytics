from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import Optional
from datetime import date, datetime, timedelta
from pydantic import BaseModel
import logging
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/extra-expenses/check-schema")
async def check_manual_expenses_schema(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Diagnostic endpoint to check manual_expenses table schema and database connection."""
    try:
        # Get current database and schema info
        db_info_query = text("""
            SELECT 
                current_database() as db_name,
                current_schema() as current_schema,
                (SELECT setting FROM pg_settings WHERE name = 'search_path') as search_path
        """)
        db_info_result = db.execute(db_info_query)
        db_info = db_info_result.fetchone()
        
        db_name = db_info[0]
        current_schema = db_info[1]
        search_path = db_info[2]
        
        # Check where manual_expenses table exists
        table_locations_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'manual_expenses'
            ORDER BY table_schema
        """)
        table_locations_result = db.execute(table_locations_query)
        manual_expenses_locations = [{"schema": row[0], "table": row[1]} for row in table_locations_result.fetchall()]
        
        # Check where fact_sales table exists (to verify same DB as imports)
        fact_locations_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'fact_sales'
            ORDER BY table_schema
        """)
        fact_locations_result = db.execute(fact_locations_query)
        fact_sales_locations = [{"schema": row[0], "table": row[1]} for row in fact_locations_result.fetchall()]
        
        # Get columns from manual_expenses in the expected schema
        columns_query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'manual_expenses'
            ORDER BY column_name
        """)
        columns_result = db.execute(columns_query, {"schema": settings.DB_SCHEMA})
        columns = columns_result.fetchall()
        
        column_list = [{"name": row[0], "type": row[1], "nullable": row[2]} for row in columns]
        has_shop_id = any(col["name"] == "shop_id" for col in column_list)
        
        # Check if fact_sales and manual_expenses are in the same database
        manual_in_expected_schema = any(loc["schema"] == settings.DB_SCHEMA for loc in manual_expenses_locations)
        fact_in_expected_schema = any(loc["schema"] == settings.DB_SCHEMA for loc in fact_sales_locations)
        same_db = len(manual_expenses_locations) > 0 and len(fact_sales_locations) > 0
        
        return {
            "database": {
                "name": db_name,
                "current_schema": current_schema,
                "search_path": search_path,
                "expected_schema": settings.DB_SCHEMA
            },
            "manual_expenses": {
                "locations": manual_expenses_locations,
                "in_expected_schema": manual_in_expected_schema,
                "columns": column_list,
                "has_shop_id": has_shop_id,
                "column_count": len(column_list)
            },
            "fact_sales": {
                "locations": fact_sales_locations,
                "in_expected_schema": fact_in_expected_schema
            },
            "diagnosis": {
                "same_database": same_db,
                "manual_expenses_exists": len(manual_expenses_locations) > 0,
                "fact_sales_exists": len(fact_sales_locations) > 0,
                "both_in_expected_schema": manual_in_expected_schema and fact_in_expected_schema,
                "shop_id_missing": not has_shop_id and manual_in_expected_schema
            }
        }
    except Exception as e:
        logger.error(f"Error checking schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking schema: {str(e)}")


# Schemas
class ExtraExpenseCreate(BaseModel):
    expense_date: date
    amount_sum: float
    shop_id: Optional[str] = None
    category: str = "Прочее"  # Default category if not provided
    comment: Optional[str] = None


class ExtraExpenseUpdate(BaseModel):
    expense_date: Optional[date] = None
    amount_sum: Optional[float] = None
    shop_id: Optional[str] = None
    category: Optional[str] = None
    comment: Optional[str] = None


class ExtraExpenseItem(BaseModel):
    id: int
    expense_date: str
    amount_sum: float
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None
    category: Optional[str] = None
    comment: Optional[str] = None
    created_at: str
    updated_at: str


class ExtraExpensesResponse(BaseModel):
    expenses: list[ExtraExpenseItem]
    total: int


def parse_period(period: str) -> tuple[Optional[date], date]:
    """Parse period string to date range."""
    today = date.today()
    
    if period == "7d":
        date_from = today - timedelta(days=6)
        return date_from, today
    elif period == "30d":
        date_from = today - timedelta(days=29)
        return date_from, today
    elif period == "90d":
        date_from = today - timedelta(days=89)
        return date_from, today
    elif period == "all":
        return None, today
    else:
        raise ValueError(f"Invalid period: {period}")


def _shop_name_norm(s: Optional[str]) -> str:
    """Normalize shop name for filtering: trim, collapse spaces, upper."""
    if not s:
        return ""
    return " ".join((s or "").strip().split()).upper()


@router.get("/extra-expenses", response_model=ExtraExpensesResponse)
async def get_extra_expenses(
    user_id: UUID = Depends(require_user),
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d, or all"),
    date_from: Optional[str] = Query(default=None, description="Start date YYYY-MM-DD (overrides period when date_to also set)"),
    date_to: Optional[str] = Query(default=None, description="End date YYYY-MM-DD"),
    shop: Optional[str] = Query(default=None, description="Shop name (string) — filter by Магазин, normalized"),
    shop_id: Optional[str] = Query(default=None, description="Shop UUID (legacy)"),
    db: Session = Depends(get_db)
):
    """Get list of extra expenses with optional period/date range and shop filters.
    When date_from and date_to are both set, they override period.
    """
    if date_from and date_to:
        try:
            date_from_dt = datetime.fromisoformat(date_from.strip()).date()
            date_to_dt = datetime.fromisoformat(date_to.strip()).date()
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid date_from or date_to format (use YYYY-MM-DD).")
        if date_from_dt > date_to_dt:
            raise HTTPException(status_code=400, detail="date_from must be less than or equal to date_to.")
        date_from_res = date_from_dt
        date_to_res = date_to_dt
    else:
        try:
            date_from_res, date_to_res = parse_period(period)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    params = {
        "user_id": str(user_id),
        "date_to": date_to_res.isoformat(),
    }

    date_filter = ""
    if date_from_res:
        params["date_from"] = date_from_res.isoformat()
        date_filter = "AND e.expense_date >= CAST(:date_from AS date)"
    
    # Filter by shop name (string, normalized): trim, collapse spaces, upper — no UUID
    shop_filter = ""
    if shop:
        shop_norm = _shop_name_norm(shop)
        params["shop_norm"] = shop_norm
        shop_filter = "AND upper(regexp_replace(trim(COALESCE(ds.shop_name, '')), '\\s+', ' ', 'g')) = :shop_norm"
    elif shop_id:
        params["shop_id"] = shop_id
        shop_filter = "AND e.shop_id = CAST(:shop_id AS uuid)"
    
    query = text(f"""
        SELECT 
            e.id,
            e.expense_date,
            e.amount_sum,
            e.shop_id::text AS shop_id,
            ds.shop_name,
            e.category,
            e.comment,
            e.created_at,
            e.updated_at
        FROM {qname("manual_expenses")} e
        LEFT JOIN {qname("dim_shop")} ds ON ds.shop_id = e.shop_id AND ds.user_id = e.user_id
        WHERE e.user_id = CAST(:user_id AS uuid)
          AND e.is_deleted = false
          AND e.expense_date <= CAST(:date_to AS date)
          {date_filter}
          {shop_filter}
        ORDER BY e.expense_date DESC, e.created_at DESC
    """)
    
    result = db.execute(query, params)
    rows = result.fetchall()
    
    expenses = []
    for row in rows:
        expenses.append(ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=row[4],
            category=row[5],
            comment=row[6],
            created_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7]),
            updated_at=row[8].isoformat() if isinstance(row[8], datetime) else str(row[8])
        ))
    
    return ExtraExpensesResponse(expenses=expenses, total=len(expenses))


@router.post("/extra-expenses", response_model=ExtraExpenseItem)
async def create_extra_expense(
    expense: ExtraExpenseCreate,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Create a new extra expense."""
    if expense.amount_sum < 0:
        raise HTTPException(status_code=400, detail="amount_sum must be >= 0")
    
    params = {
        "user_id": str(user_id),
        "expense_date": expense.expense_date.isoformat(),
        "amount_sum": expense.amount_sum,
        "shop_id": expense.shop_id if expense.shop_id else None,
        "category": expense.category or "Прочее",  # Ensure category is not None
        "comment": expense.comment
    }
    
    try:
        # Diagnostic queries to verify database and schema
        try:
            db_info_query = text("""
                SELECT 
                    current_database() as db_name,
                    current_schema() as current_schema,
                    (SELECT setting FROM pg_settings WHERE name = 'search_path') as search_path
            """)
            db_info_result = db.execute(db_info_query)
            db_info = db_info_result.fetchone()
            logger.info(f"Database connection info: db={db_info[0]}, schema={db_info[1]}, search_path={db_info[2]}")
            
            # Check if manual_expenses table exists and its schema
            table_check_query = text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = 'manual_expenses'
            """)
            table_check_result = db.execute(table_check_query)
            table_info = table_check_result.fetchall()
            logger.info(f"manual_expenses table locations: {table_info}")
            
            # Check if fact_sales exists (to verify we're in the same DB as imports)
            fact_check_query = text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_name = 'fact_sales'
            """)
            fact_check_result = db.execute(fact_check_query)
            fact_info = fact_check_result.fetchall()
            logger.info(f"fact_sales table locations: {fact_info}")
            
            # Check columns in manual_expenses
            columns_query = text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'manual_expenses'
                ORDER BY column_name
            """)
            columns_result = db.execute(columns_query, {"schema": settings.DB_SCHEMA})
            columns = columns_result.fetchall()
            logger.info(f"manual_expenses columns in schema '{settings.DB_SCHEMA}': {[col[0] for col in columns]}")
            
            # Verify shop_id exists
            has_shop_id = any(col[0] == 'shop_id' for col in columns)
            if not has_shop_id:
                logger.error(f"CRITICAL: shop_id column NOT found in {settings.DB_SCHEMA}.manual_expenses!")
                logger.error(f"Available columns: {[col[0] for col in columns]}")
        except Exception as diag_error:
            logger.warning(f"Diagnostic queries failed (non-critical): {diag_error}")
        
        logger.info(f"Creating expense for user_id={user_id}, params={params}")
        
        query = text(f"""
            INSERT INTO {qname("manual_expenses")} (
                user_id, expense_date, amount_sum, shop_id, category, comment
            )
            VALUES (
                CAST(:user_id AS uuid),
                CAST(:expense_date AS date),
                CAST(:amount_sum AS numeric(18,2)),
                CASE WHEN :shop_id IS NULL THEN NULL ELSE CAST(:shop_id AS uuid) END,
                :category,
                :comment
            )
            RETURNING 
                id,
                expense_date,
                amount_sum,
                shop_id::text AS shop_id,
                category,
                comment,
                created_at,
                updated_at
        """)
        
        result = db.execute(query, params)
        db.commit()
        
        row = result.fetchone()
        if not row:
            logger.error(f"Failed to create expense: no row returned for user_id={user_id}")
            raise HTTPException(status_code=500, detail="Failed to create expense")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating expense for user_id={user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create expense: {str(e)}"
        )
    
    # Get shop_name if shop_id exists
    shop_name = None
    if row[3]:
        shop_query = text(f"""
            SELECT shop_name FROM {qname("dim_shop")}
            WHERE shop_id = CAST(:shop_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
        """)
        shop_result = db.execute(shop_query, {
            "shop_id": row[3],
            "user_id": str(user_id)
        })
        shop_row = shop_result.fetchone()
        if shop_row:
            shop_name = shop_row[0]
    
    return ExtraExpenseItem(
        id=row[0],
        expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
        amount_sum=float(row[2]),
        shop_id=row[3],
        shop_name=shop_name,
        category=row[4],
        comment=row[5],
        created_at=row[6].isoformat() if isinstance(row[6], datetime) else str(row[6]),
        updated_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7])
    )


@router.put("/extra-expenses/{expense_id}", response_model=ExtraExpenseItem)
async def update_extra_expense(
    expense_id: int,
    expense: ExtraExpenseUpdate,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Update an existing extra expense."""
    # Check if expense exists and belongs to user
    check_query = text(f"""
        SELECT id FROM {qname("manual_expenses")}
        WHERE id = :expense_id
          AND user_id = CAST(:user_id AS uuid)
          AND is_deleted = false
    """)
    check_result = db.execute(check_query, {
        "expense_id": expense_id,
        "user_id": str(user_id)
    })
    if not check_result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Build update query dynamically
    updates = []
    params = {
        "expense_id": expense_id,
        "user_id": str(user_id)
    }
    
    if expense.expense_date is not None:
        updates.append("expense_date = CAST(:expense_date AS date)")
        params["expense_date"] = expense.expense_date.isoformat()
    
    if expense.amount_sum is not None:
        if expense.amount_sum < 0:
            raise HTTPException(status_code=400, detail="amount_sum must be >= 0")
        updates.append("amount_sum = CAST(:amount_sum AS numeric(18,2))")
        params["amount_sum"] = expense.amount_sum
    
    if expense.shop_id is not None:
        # Allow setting shop_id to NULL explicitly
        if expense.shop_id == "" or expense.shop_id.lower() == "null":
            updates.append("shop_id = NULL")
        else:
            updates.append("shop_id = CAST(:shop_id AS uuid)")
            params["shop_id"] = expense.shop_id
    # If shop_id is None, don't update it (keep current value)
    
    if expense.category is not None:
        updates.append("category = :category")
        params["category"] = expense.category or "Прочее"  # Ensure category is not None
    
    if expense.comment is not None:
        updates.append("comment = :comment")
        params["comment"] = expense.comment
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # updated_at will be set by trigger
    update_query = text(f"""
        UPDATE {qname("manual_expenses")}
        SET {', '.join(updates)}
        WHERE id = :expense_id
          AND user_id = CAST(:user_id AS uuid)
          AND is_deleted = false
        RETURNING 
            id,
            expense_date,
            amount_sum,
            shop_id::text AS shop_id,
            category,
            comment,
            created_at,
            updated_at
    """)
    
    result = db.execute(update_query, params)
    db.commit()
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Get shop_name if shop_id exists
    shop_name = None
    if row[3]:
        shop_query = text(f"""
            SELECT shop_name FROM {qname("dim_shop")}
            WHERE shop_id = CAST(:shop_id AS uuid)
              AND user_id = CAST(:user_id AS uuid)
        """)
        shop_result = db.execute(shop_query, {
            "shop_id": row[3],
            "user_id": str(user_id)
        })
        shop_row = shop_result.fetchone()
        if shop_row:
            shop_name = shop_row[0]
    
    return ExtraExpenseItem(
        id=row[0],
        expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
        amount_sum=float(row[2]),
        shop_id=row[3],
        shop_name=shop_name,
        category=row[4],
        comment=row[5],
        created_at=row[6].isoformat() if isinstance(row[6], datetime) else str(row[6]),
        updated_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7])
    )


@router.delete("/extra-expenses/{expense_id}")
async def delete_extra_expense(
    expense_id: int,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Delete an extra expense (soft delete by setting is_deleted=true)."""
    query = text(f"""
        UPDATE {qname("manual_expenses")}
        SET is_deleted = true, updated_at = now()
        WHERE id = :expense_id
          AND user_id = CAST(:user_id AS uuid)
          AND is_deleted = false
        RETURNING id
    """)
    
    result = db.execute(query, {
        "expense_id": expense_id,
        "user_id": str(user_id)
    })
    db.commit()
    
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return {"message": "Expense deleted successfully"}
