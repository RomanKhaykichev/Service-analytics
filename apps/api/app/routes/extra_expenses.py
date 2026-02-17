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
from app.utils.barcode import barcode_norm_sql
from app.utils.shop_filter import storage_barcode_filter_sql, normalize_shop

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/extra-expenses/ensure-name-column")
async def ensure_name_column(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Ensure name column exists in manual_expenses table. Creates it if missing."""
    try:
        # Check if column exists
        check_query = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses'
              AND column_name = 'name'
        """)
        result = db.execute(check_query, {"schema": settings.DB_SCHEMA})
        if result.fetchone():
            return {"status": "exists", "message": "Column 'name' already exists", "has_name": True}
        
        # Add column if it doesn't exist
        add_column_query = text(f"""
            ALTER TABLE {qname("manual_expenses")}
            ADD COLUMN IF NOT EXISTS name text NULL
        """)
        db.execute(add_column_query)
        db.commit()
        
        logger.info(f"Added 'name' column to {qname('manual_expenses')}")
        return {"status": "created", "message": "Column 'name' has been added successfully", "has_name": True}
    except Exception as e:
        db.rollback()
        logger.error(f"Error ensuring name column: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ensure name column: {str(e)}")


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
        has_name = any(col["name"] == "name" for col in column_list)
        
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
                "has_name": has_name,
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
                "shop_id_missing": not has_shop_id and manual_in_expected_schema,
                "name_missing": not has_name and manual_in_expected_schema
            }
        }
    except Exception as e:
        logger.error(f"Error checking schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking schema: {str(e)}")


# Schemas
class ExtraExpenseCreate(BaseModel):
    expense_date: date
    amount_sum: float
    shop_id: Optional[str] = None  # UUID (legacy)
    shop: Optional[str] = None  # Shop name from seller-storage (column "Магазин"); resolved to shop_id via dim_shop
    category: str = "Прочее"  # Default category if not provided
    name: Optional[str] = None  # Product name from left-out-report_old (column "Наименование")
    comment: Optional[str] = None


class ExtraExpenseUpdate(BaseModel):
    expense_date: Optional[date] = None
    amount_sum: Optional[float] = None
    shop_id: Optional[str] = None
    category: Optional[str] = None
    name: Optional[str] = None
    comment: Optional[str] = None


class ExtraExpenseItem(BaseModel):
    id: int
    expense_date: str
    amount_sum: float
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None
    category: Optional[str] = None
    name: Optional[str] = None  # Product name from left-out-report_old
    comment: Optional[str] = None
    created_at: str
    updated_at: str


class ExtraExpensesResponse(BaseModel):
    expenses: list[ExtraExpenseItem]
    total: int


class ProductNamesResponse(BaseModel):
    names: list[str]


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
    
    Note: If 'name' column doesn't exist in manual_expenses, it will return NULL for name field.
    When date_from and date_to are both set, they override period.
    """
    # Check if 'name' column exists, create if missing
    has_name_column = False
    try:
        check_column_query = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses'
              AND column_name = 'name'
        """)
        result = db.execute(check_column_query, {"schema": settings.DB_SCHEMA})
        has_name_column = result.fetchone() is not None
        
        # Auto-create column if it doesn't exist
        if not has_name_column:
            logger.warning(f"GET /extra-expenses: name column NOT found! Auto-creating...")
            try:
                add_column_query = text(f"""
                    ALTER TABLE {qname("manual_expenses")}
                    ADD COLUMN IF NOT EXISTS name text NULL
                """)
                db.execute(add_column_query)
                db.commit()
                has_name_column = True
                logger.info(f"GET /extra-expenses: Successfully created 'name' column")
            except Exception as create_error:
                logger.error(f"GET /extra-expenses: Failed to auto-create name column: {create_error}")
                db.rollback()
        
        logger.info(f"GET /extra-expenses: Checking name column existence: {has_name_column}")
    except Exception as e:
        logger.warning(f"GET /extra-expenses: Error checking name column: {e}")
        pass  # Assume column doesn't exist if check fails
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
    
    # Build SELECT query with conditional name column
    name_select = "e.name" if has_name_column else "NULL::text AS name"
    query = text(f"""
        SELECT 
            e.id,
            e.expense_date,
            e.amount_sum,
            e.shop_id::text AS shop_id,
            ds.shop_name,
            e.category,
            {name_select},
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
    
    logger.info(f"GET /extra-expenses: has_name_column={has_name_column}, found {len(rows)} rows")
    if rows:
        logger.info(f"  First row name value: {repr(rows[0][6] if len(rows[0]) > 6 else 'N/A')}")
    
    expenses = []
    for idx, row in enumerate(rows):
        name_value = row[6] if len(row) > 6 else None
        if idx < 3:  # Log first 3 rows for debugging
            logger.info(f"  Row {idx}: id={row[0]}, name={repr(name_value)}")
        expenses.append(ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=row[4],
            category=row[5],
            name=name_value,
            comment=row[7],
            created_at=row[8].isoformat() if isinstance(row[8], datetime) else str(row[8]),
            updated_at=row[9].isoformat() if isinstance(row[9], datetime) else str(row[9])
        ))
    
    return ExtraExpensesResponse(expenses=expenses, total=len(expenses))


@router.post("/extra-expenses", response_model=ExtraExpenseItem)
async def create_extra_expense(
    expense: ExtraExpenseCreate,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Create a new extra expense."""
    logger.info(f"Received expense creation request: expense_date={expense.expense_date}, amount_sum={expense.amount_sum}, category={expense.category}, name={expense.name}, shop={expense.shop}, shop_id={expense.shop_id}")
    
    if expense.amount_sum < 0:
        raise HTTPException(status_code=400, detail="amount_sum must be >= 0")

    # Resolve shop (name from seller-storage) to shop_id (UUID) via dim_shop; prefer shop over shop_id
    resolved_shop_id: Optional[str] = None
    if expense.shop and expense.shop.strip():
        shop_norm = _shop_name_norm(expense.shop)
        if shop_norm:
            try:
                resolve_query = text(f"""
                    SELECT shop_id::text FROM {qname("dim_shop")}
                    WHERE user_id = CAST(:user_id AS uuid)
                      AND upper(regexp_replace(trim(COALESCE(shop_name, '')), '\\s+', ' ', 'g')) = :shop_norm
                    LIMIT 1
                """)
                resolve_result = db.execute(resolve_query, {"user_id": str(user_id), "shop_norm": shop_norm})
                resolve_row = resolve_result.fetchone()
                if resolve_row:
                    resolved_shop_id = resolve_row[0]
            except Exception as e:
                logger.warning(f"Could not resolve shop name to UUID: {e}")
    if resolved_shop_id is None and expense.shop_id and expense.shop_id.strip():
        # Legacy: use shop_id if it looks like UUID
        try:
            UUID(expense.shop_id)
            resolved_shop_id = expense.shop_id
        except (ValueError, TypeError):
            pass

    params = {
        "user_id": str(user_id),
        "expense_date": expense.expense_date.isoformat(),
        "amount_sum": expense.amount_sum,
        "shop_id": resolved_shop_id,
        "category": expense.category or "Прочее",  # Ensure category is not None
        "name": expense.name if expense.name and expense.name.strip() else None,  # Convert empty string to None
        "comment": expense.comment if expense.comment and expense.comment.strip() else None  # Convert empty string to None
    }
    
    logger.info(f"POST /extra-expenses: Received expense.name={repr(expense.name)}, params['name']={repr(params.get('name'))}")

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
            
            # Check if name column exists, create if missing
            has_name_column = any(col[0] == 'name' for col in columns)
            if not has_name_column:
                logger.warning(f"WARNING: name column NOT found in {settings.DB_SCHEMA}.manual_expenses! Auto-creating...")
                logger.warning(f"Available columns: {[col[0] for col in columns]}")
                try:
                    add_column_query = text(f"""
                        ALTER TABLE {qname("manual_expenses")}
                        ADD COLUMN IF NOT EXISTS name text NULL
                    """)
                    db.execute(add_column_query)
                    db.commit()
                    has_name_column = True
                    logger.info(f"POST /extra-expenses: Successfully created 'name' column")
                except Exception as create_error:
                    logger.error(f"POST /extra-expenses: Failed to auto-create name column: {create_error}")
                    db.rollback()
        except Exception as diag_error:
            logger.warning(f"Diagnostic queries failed (non-critical): {diag_error}")
            has_name_column = False
        
        logger.info(f"Creating expense for user_id={user_id}, has_name_column={has_name_column}")
        logger.info(f"  expense.name (raw) = {repr(expense.name)}")
        logger.info(f"  params['name'] = {repr(params.get('name'))}")
        
        # Build INSERT query conditionally based on whether name column exists
        if has_name_column:
            insert_columns = "user_id, expense_date, amount_sum, shop_id, category, name, comment"
            insert_values = """CAST(:user_id AS uuid),
                CAST(:expense_date AS date),
                CAST(:amount_sum AS numeric(18,2)),
                CASE WHEN :shop_id IS NULL THEN NULL ELSE CAST(:shop_id AS uuid) END,
                :category,
                :name,
                :comment"""
            returning_name = "name,"
            logger.info(f"  Using INSERT with name column")
        else:
            insert_columns = "user_id, expense_date, amount_sum, shop_id, category, comment"
            insert_values = """CAST(:user_id AS uuid),
                CAST(:expense_date AS date),
                CAST(:amount_sum AS numeric(18,2)),
                CASE WHEN :shop_id IS NULL THEN NULL ELSE CAST(:shop_id AS uuid) END,
                :category,
                :comment"""
            returning_name = "NULL::text AS name,"
            logger.warning(f"  WARNING: name column does not exist! INSERT without name column. Please run migration.")
        
        query = text(f"""
            INSERT INTO {qname("manual_expenses")} (
                {insert_columns}
            )
            VALUES (
                {insert_values}
            )
            RETURNING 
                id,
                expense_date,
                amount_sum,
                shop_id::text AS shop_id,
                category,
                {returning_name}
                comment,
                created_at,
                updated_at
        """)
        
        logger.info(f"  Executing INSERT query with params: {params}")
        logger.info(f"  INSERT query columns: {insert_columns}")
        logger.info(f"  INSERT query returning_name: {returning_name}")
        result = db.execute(query, params)
        db.commit()
        logger.info(f"  INSERT successful, row returned")
        
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
    
    # Handle different row structures based on whether name column exists
    logger.info(f"  Row length: {len(row)}, has_name_column: {has_name_column}")
    logger.info(f"  Row data: {row}")
    
    if has_name_column and len(row) >= 9:  # With name column
        # RETURNING order: id, expense_date, amount_sum, shop_id, category, name, comment, created_at, updated_at
        saved_name = row[5]  # name is at index 5
        logger.info(f"  Saved name from database: {repr(saved_name)}")
        logger.info(f"  Returning expense with name={repr(saved_name)}")
        return ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=shop_name,
            category=row[4],
            name=saved_name,
            comment=row[6],
            created_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7]),
            updated_at=row[8].isoformat() if isinstance(row[8], datetime) else str(row[8])
        )
    else:  # Without name column
        logger.warning(f"  Returning without name (column doesn't exist or wrong row length)")
        return ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=shop_name,
            category=row[4],
            name=None,
            comment=row[5] if len(row) > 5 else None,
            created_at=row[6].isoformat() if isinstance(row[6], datetime) else str(row[6]) if len(row) > 6 else str(datetime.now()),
            updated_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7]) if len(row) > 7 else str(datetime.now())
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
    
    # Check if name column exists before trying to update it, create if missing
    has_name_column = False
    try:
        check_name_query = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses'
              AND column_name = 'name'
        """)
        name_result = db.execute(check_name_query, {"schema": settings.DB_SCHEMA})
        has_name_column = name_result.fetchone() is not None
        
        # Auto-create column if it doesn't exist
        if not has_name_column:
            logger.warning(f"PUT /extra-expenses: name column NOT found! Auto-creating...")
            try:
                add_column_query = text(f"""
                    ALTER TABLE {qname("manual_expenses")}
                    ADD COLUMN IF NOT EXISTS name text NULL
                """)
                db.execute(add_column_query)
                db.commit()
                has_name_column = True
                logger.info(f"PUT /extra-expenses: Successfully created 'name' column")
            except Exception as create_error:
                logger.error(f"PUT /extra-expenses: Failed to auto-create name column: {create_error}")
                db.rollback()
    except Exception as e:
        logger.warning(f"PUT /extra-expenses: Error checking name column: {e}")
        pass
    
    if expense.name is not None and has_name_column:
        updates.append("name = :name")
        # Convert empty string to None
        params["name"] = expense.name if expense.name and expense.name.strip() else None
    
    if expense.comment is not None:
        updates.append("comment = :comment")
        # Convert empty string to None
        params["comment"] = expense.comment if expense.comment and expense.comment.strip() else None
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # updated_at will be set by trigger
    name_return = "name," if has_name_column else "NULL::text AS name,"
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
            {name_return}
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
    
    # Handle different row structures based on whether name column exists
    if has_name_column and len(row) >= 9:
        return ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=shop_name,
            category=row[4],
            name=row[5],
            comment=row[6],
            created_at=row[7].isoformat() if isinstance(row[7], datetime) else str(row[7]),
            updated_at=row[8].isoformat() if isinstance(row[8], datetime) else str(row[8])
        )
    else:
        return ExtraExpenseItem(
            id=row[0],
            expense_date=row[1].isoformat() if isinstance(row[1], date) else str(row[1]),
            amount_sum=float(row[2]),
            shop_id=row[3],
            shop_name=shop_name,
            category=row[4],
            name=None,
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


@router.get("/extra-expenses/product-names", response_model=ProductNamesResponse)
async def get_product_names(
    user_id: UUID = Depends(require_user),
    shop_id: Optional[str] = Query(default=None, description="Shop identifier (normalized shop name or UUID) — filter products by shop via barcode_norm"),
    db: Session = Depends(get_db)
):
    """Get unique product names from left-out-report_old (stg_leftout_old, column 'Наименование').
    
    If shop_id is provided, only return product names that are linked to that shop via barcode_norm
    (through fact_storage_snapshot). shop_id can be either:
    - Normalized shop name (string from seller-storage, e.g., "AOELEMENT UNDERWEAR")
    - UUID from dim_shop
    """
    try:
        params = {"user_id": str(user_id)}
        shop_filter_sql = ""
        shop_norm = None
        
        # If shop_id is provided, filter by products linked to that shop via barcode_norm
        if shop_id and shop_id.strip():
            shop_id_clean = shop_id.strip()
            
            # Try to determine if it's a UUID or a shop name string
            is_uuid = False
            try:
                UUID(shop_id_clean)
                is_uuid = True
            except ValueError:
                pass
            
            if is_uuid:
                # For UUID, resolve shop_id to shop_name from dim_shop, then normalize
                shop_name_query = text(f"""
                    SELECT shop_name FROM {qname("dim_shop")}
                    WHERE shop_id = CAST(:shop_id AS uuid) AND user_id = CAST(:user_id AS uuid)
                """)
                shop_name_result = db.execute(shop_name_query, {"shop_id": shop_id_clean, "user_id": str(user_id)})
                shop_name_row = shop_name_result.fetchone()
                if shop_name_row and shop_name_row[0]:
                    shop_norm = normalize_shop(shop_name_row[0])
            else:
                # Filter by shop_raw (normalized shop name from seller-storage)
                shop_norm = normalize_shop(shop_id_clean)
            
            if shop_norm:
                params["shop_norm"] = shop_norm
                # Use the same filter as in charts.py: storage_barcode_filter_sql with barcode_raw
                # This checks if barcode from stg_leftout_old exists in fact_storage_snapshot for the selected shop
                shop_filter_sql = "\n              " + storage_barcode_filter_sql(
                    "sl", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("COALESCE(sl.barcode_raw, sl.data->>'Штрихкод')")
                )
        
        # Get latest batch_id from stg_leftout_old (with optional shop filter)
        # Same approach as in charts.py
        batch_query = text(f"""
            SELECT sl.upload_batch_id 
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
            {shop_filter_sql}
            ORDER BY sl.upload_batch_id DESC NULLS LAST
            LIMIT 1
        """)
        batch_result = db.execute(batch_query, params)
        batch_row = batch_result.fetchone()
        
        if not batch_row or not batch_row[0]:
            logger.warning(f"GET /extra-expenses/product-names: No batches found for user_id={user_id}")
            return ProductNamesResponse(names=[])
        
        batch_id = str(batch_row[0])
        params["batch_id"] = batch_id
        
        # Build query with latest batch_id and shop filter (same as charts.py)
        query = text(f"""
            SELECT DISTINCT 
                NULLIF(trim(sl.data->>'Наименование'), '') AS name
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
              AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND sl.data IS NOT NULL
              AND NULLIF(trim(sl.data->>'Наименование'), '') IS NOT NULL
              {shop_filter_sql}
            ORDER BY name
        """)
        
        logger.info(f"GET /extra-expenses/product-names: shop_id={shop_id}, batch_id={batch_id}, shop_filter={'applied' if shop_filter_sql else 'none'}")
        logger.info(f"  Query params: {params}")
        logger.info(f"  Shop filter SQL: {shop_filter_sql[:500] if shop_filter_sql else 'none'}")
        
        # Debug: Check how many products exist without filter
        debug_query_no_filter = text(f"""
            SELECT COUNT(DISTINCT NULLIF(trim(sl.data->>'Наименование'), ''))
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
              AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND sl.data IS NOT NULL
              AND NULLIF(trim(sl.data->>'Наименование'), '') IS NOT NULL
        """)
        debug_result = db.execute(debug_query_no_filter, {"user_id": str(user_id), "batch_id": batch_id})
        total_count = debug_result.scalar() or 0
        logger.info(f"  Total products without filter: {total_count}")
        
        # Debug: Check how many barcodes exist in fact_storage_snapshot for this shop
        if shop_filter_sql and "shop_norm" in params:
            debug_storage_query = text(f"""
                SELECT COUNT(DISTINCT COALESCE(fss.barcode_norm, {barcode_norm_sql("fss.barcode")}))
                FROM {qname("fact_storage_snapshot")} fss
                INNER JOIN (
                    SELECT user_id, upload_batch_id
                    FROM (
                        SELECT user_id, upload_batch_id,
                               ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY loaded_at DESC NULLS LAST) AS rn
                        FROM {qname("fact_storage_snapshot")}
                        WHERE user_id = CAST(:user_id AS uuid)
                    ) t WHERE rn = 1
                ) last_batch ON fss.user_id = last_batch.user_id AND fss.upload_batch_id = last_batch.upload_batch_id
                WHERE fss.user_id = CAST(:user_id AS uuid)
                  AND upper(regexp_replace(trim(COALESCE(fss.shop_raw, '')), '\\s+', ' ', 'g')) = :shop_norm
            """)
            debug_storage_result = db.execute(debug_storage_query, {"user_id": str(user_id), "shop_norm": params["shop_norm"]})
            storage_barcodes_count = debug_storage_result.scalar() or 0
            logger.info(f"  Barcodes in fact_storage_snapshot for shop_norm={params['shop_norm']}: {storage_barcodes_count}")
        
        result = db.execute(query, params)
        rows = result.fetchall()
        
        names = [row[0] for row in rows if row[0]]
        
        logger.info(f"GET /extra-expenses/product-names: shop_id={shop_id}, found {len(names)} names")
        if names:
            logger.info(f"  First 3 names: {names[:3]}")
        elif shop_filter_sql:
            logger.warning(f"  No names found with shop filter! Check barcode matching between stg_leftout_old and fact_storage_snapshot")
        return ProductNamesResponse(names=names)
    except Exception as e:
        logger.error(f"Error fetching product names: {e}", exc_info=True)
        # Return empty list on error instead of failing
        return ProductNamesResponse(names=[])
