from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import Optional
from pathlib import Path
import pandas as pd
import logging
import io
from app.db import get_db, qname
from app.deps import require_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Маппинги колонок (из import/import_batch.py)
SHEETS = {
    "sales": "Отчет по продажам",
    "expenses": "Отчет по услугам",
    "inventory": "Остатки (новый)",  # leftout -> inventory
    "storage": "Отчет по хранению",
}

SALES_MAP = {
    "Статус": "status_raw",
    "Дата создания": "created_at_raw",
    "Дата получения": "received_at_raw",
    "№ заказа": "order_no_raw",
    "Штрихкод": "barcode_raw",
    "SKU": "sku_raw",
    "Наименование": "name_raw",
    "Категория": "category_raw",
    "Количество": "qty_raw",
    "Возвраты": "returns_raw",
    "Выручка (сумы)": "revenue_raw",
    "Выручка с вычетом комиссии и логистики (сумы)": "revenue_net_raw",
    "Комиссия маркетплейса (сумы)": "commission_raw",
    "Цена (сумы)": "price_raw",
    "Промокод (сумы)": "promo_raw",
    "Себестоимость (сумы)": "cogs_raw",
    "Логистический сбор": "logistics_raw",
}

EXP_MAP = {
    "Источник": "source_raw",
    "Услуга": "service_raw",
    "Статус": "status_raw",
    "ID операции": "operation_id_raw",
    "Дата списания": "written_off_raw",
    "Стоимость (сумы)": "cost_raw",
    "Количество": "qty_raw",
    "Сумма (сумы)": "amount_raw",
    "Тип операции": "operation_type_raw",
}

LEFTOUT_MAP = {
    "Магазин": "shop_raw",
    "Название товара": "product_name_raw",
    "ID товара": "product_id_raw",
    "SKU": "sku_raw",
    "Штрихкод": "barcode_raw",
    "Заканчивается": "ending_raw",
    "Индикатор обеспеченности": "availability_ind_raw",
    "Плановая дата, когда закончатся текущие остатки": "planned_end_raw",
    "Обеспеченность (на сколько дней хватит текущих остатков), дней": "coverage_days_raw",
    "Рекомендованное количество на поставку, шт": "recommended_qty_raw",
    "На вашей стороне (на складе FBS), шт": "on_your_side_fbs_raw",
    "На стороне маркетплейса (всего в продаже, в пути, на складах и фотостудии), шт": "on_marketplace_side_raw",
    "В поставке (создана накладная), шт": "in_supply_raw",
    "В продаже, шт": "in_sale_raw",
    "В пути до клиента (в логистике), шт": "to_customer_raw",
    "В пути от клиента (возвраты и отказы), шт": "from_customer_raw",
    "На складе длительного хранения (СДХ), шт": "sdh_raw",
    "На фотостудии, шт": "photo_raw",
    "Брак на складе, шт": "defect_raw",
    "Потенциальная сумма к получению за 1 шт, сум": "potential_per_unit_raw",
    "Потенциальная сумма к получению за все остатки, сум": "potential_total_raw",
}

STORAGE_MAP = {
    "Магазин": "shop_raw",
    "Название товара": "product_name_raw",
    "ID товара": "product_id_raw",
    "SKU": "sku_raw",
    "Штрихкод": "barcode_raw",
    "Габаритная группа": "size_group_raw",
    "Оборачиваемость, дней": "turnover_days_raw",
    "Хранение": "storage_type_raw",
    "Всего за хранение последние 30 дней, сум": "fee_total_30d_raw",
}

REQUIRED = {
    "sales": ["Дата создания", "№ заказа", "Штрихкод"],
    "expenses": ["ID операции", "Дата списания"],
    "inventory": ["Магазин", "Штрихкод"],
    "leftout": ["Магазин", "Штрихкод"],  # Same as inventory
    "storage": ["Магазин", "Штрихкод"],
}

REPORT_TYPE_TO_FILE_TYPE = {
    "sales": "sales",
    "expenses": "expenses",
    "inventory": "leftout",  # inventory -> leftout для внутренней логики
    "storage": "storage",
}


def norm(s):
    """Normalize column name: remove newlines, non-breaking spaces, normalize whitespace."""
    return " ".join(str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ").strip().split())


def read_excel_as_str(file_content: bytes, sheet: str, file_type: str = None) -> pd.DataFrame:
    """Read Excel with header=1 and proper converters for barcode/sku."""
    converters = {}
    if file_type in ("leftout", "storage"):
        converters = {
            "Штрихкод": lambda x: str(x) if pd.notna(x) else "",
            "SKU": lambda x: str(x) if pd.notna(x) else "",
        }
    
    df = pd.read_excel(
        io.BytesIO(file_content),
        sheet_name=sheet,
        header=1,
        dtype={"Штрихкод": "string", "SKU": "string"} if file_type in ("leftout", "storage") else None,
        converters=converters if converters else None,
        engine="openpyxl"
    )
    df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("Unnamed")]]
    # Normalize column names
    df.columns = [norm(c) for c in df.columns]
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    df = df.dropna(how="all")
    
    # Filter rows with empty barcode for leftout/storage
    if file_type in ("leftout", "storage") and "Штрихкод" in df.columns:
        df = df[df["Штрихкод"].notna() & (df["Штрихкод"].astype(str).str.strip() != "")]
    
    return df


def validate_required(df: pd.DataFrame, file_type: str):
    """Validate that required columns are present."""
    required_cols = REQUIRED.get(file_type, [])
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"[{file_type}] Не найдены обязательные колонки: {missing}. Найдено: {list(df.columns)}")


def to_staging(df: pd.DataFrame, mapping: dict, user_id: str, batch_id: str, table: str, db: Session, file_type: str = None):
    """Load data to staging table with proper type handling."""
    out = pd.DataFrame()
    out["row_num"] = (df.reset_index().index + 3).astype(int)

    for src_col, dst_col in mapping.items():
        if src_col in df.columns:
            out[dst_col] = df[src_col]
        else:
            out[dst_col] = None

    # Type conversions for leftout/storage
    if file_type == "leftout":
        # String fields: strip
        for col in ["shop_raw", "product_name_raw", "product_id_raw", "sku_raw", "barcode_raw", 
                    "ending_raw", "availability_ind_raw"]:
            if col in out.columns:
                out[col] = out[col].apply(lambda x: str(x).strip() if pd.notna(x) else None)
        
        # Date field
        if "planned_end_raw" in out.columns:
            out["planned_end_raw"] = pd.to_datetime(out["planned_end_raw"], errors="coerce").dt.date
        
        # Numeric fields
        for col in ["coverage_days_raw", "potential_per_unit_raw", "potential_total_raw"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
        
        # Integer fields (stock quantities)
        for col in ["recommended_qty_raw", "on_your_side_fbs_raw", "on_marketplace_side_raw",
                    "in_supply_raw", "in_sale_raw", "to_customer_raw", "from_customer_raw",
                    "sdh_raw", "photo_raw", "defect_raw"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
    
    elif file_type == "storage":
        # String fields: strip
        for col in ["shop_raw", "product_name_raw", "product_id_raw", "sku_raw", "barcode_raw",
                    "size_group_raw", "storage_type_raw"]:
            if col in out.columns:
                out[col] = out[col].apply(lambda x: str(x).strip() if pd.notna(x) else None)
        
        # Numeric fields
        for col in ["turnover_days_raw", "fee_total_30d_raw"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
    else:
        # Trim string fields for other file types
        for col in out.columns:
            if out[col].dtype == "object":
                out[col] = out[col].apply(lambda x: str(x).strip() if pd.notna(x) and isinstance(x, str) else x)

    out["user_id"] = user_id
    out["upload_batch_id"] = batch_id

    cols = ["user_id", "upload_batch_id", "row_num"] + [
        c for c in out.columns if c not in ("user_id", "upload_batch_id", "row_num")
    ]
    out = out[cols]

    # Use current session connection for pandas to_sql (same transaction)
    conn = db.connection()
    
    out.to_sql(
        name=table,
        schema="app",
        con=conn,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )
    # Note: No commit here - caller will commit the transaction


def delete_all_user_data(db: Session, user_id: UUID):
    """
    Delete ALL old data for user from staging and fact tables (overwrite mode).
    This is called before importing new batch to ensure clean state.
    """
    user_id_str = str(user_id)
    params = {"user_id": user_id_str}
    
    # Delete from fact tables first (FK constraints)
    # Order matters: delete fact tables before staging tables
    db.execute(text(f"DELETE FROM {qname('fact_sales')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('fact_expenses')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('fact_storage_snapshot')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('fact_leftout_snapshot')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    
    # Delete from staging tables
    db.execute(text(f"DELETE FROM {qname('stg_sales')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('stg_expenses')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('stg_storage')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    db.execute(text(f"DELETE FROM {qname('stg_leftout')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    
    # Also clean up map_shop_sku for this user
    db.execute(text(f"DELETE FROM {qname('map_shop_sku')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    
    # Note: dim_shop is NOT deleted - shops are shared across batches
    # db.execute(text(f"DELETE FROM {qname('dim_shop')} WHERE user_id = CAST(:user_id AS uuid)"), params)
    
    logger.info(f"Deleted all user data: user_id={user_id}")


def delete_old_data(db: Session, user_id: UUID, report_type: str):
    """Delete old data for user from staging and fact tables (legacy - per report type). Does NOT commit."""
    user_id_str = str(user_id)
    
    if report_type == "sales":
        # Delete from fact_sales first (FK constraints)
        db.execute(text(f"DELETE FROM {qname('fact_sales')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        db.execute(text(f"DELETE FROM {qname('stg_sales')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
    elif report_type == "expenses":
        db.execute(text(f"DELETE FROM {qname('fact_expenses')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        db.execute(text(f"DELETE FROM {qname('stg_expenses')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
    elif report_type == "inventory":
        db.execute(text(f"DELETE FROM {qname('fact_leftout_snapshot')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        db.execute(text(f"DELETE FROM {qname('stg_leftout')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
    elif report_type == "storage":
        db.execute(text(f"DELETE FROM {qname('fact_storage_snapshot')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        db.execute(text(f"DELETE FROM {qname('stg_storage')} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
    
    # Note: No commit here - caller will commit the transaction


def create_batch(db: Session, user_id: UUID) -> str:
    """Create new upload batch. Does NOT commit - caller must commit."""
    batch_id = db.execute(
        text(f"""
            INSERT INTO {qname('upload_batch')}(user_id, status, is_current)
            VALUES (CAST(:u AS uuid), 'processing', false)
            RETURNING upload_batch_id
        """),
        {"u": str(user_id)},
    ).scalar()
    # Note: No commit here - caller will commit the transaction
    return str(batch_id)


def populate_facts(db: Session, user_id: UUID, batch_id: str, report_type: str) -> int:
    """Populate fact tables from staging tables. Returns number of rows inserted."""
    user_id_str = str(user_id)
    params = {"user_id": user_id_str, "batch_id": batch_id}
    
    if report_type == "sales":
        # Update barcode_norm in staging table (normalize barcode_raw)
        db.execute(text(f"""
            UPDATE {qname('stg_sales')}
            SET barcode_norm = NULLIF(TRIM(regexp_replace(barcode_raw, '\s+', '', 'g')), '')
            WHERE user_id = CAST(:user_id AS uuid) 
              AND upload_batch_id = CAST(:batch_id AS uuid)
              AND barcode_raw IS NOT NULL
        """), params)
        
        # Delete old batch data first
        db.execute(text(f"DELETE FROM {qname('fact_sales')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        # Ensure fallback shop exists for rows without mapping
        db.execute(text(f"""
            INSERT INTO {qname('dim_shop')} (user_id, shop_name)
            VALUES (CAST(:user_id AS uuid), '(Не определено)')
            ON CONFLICT (user_id, shop_name) DO NOTHING
        """), params)
        
        # Get fallback shop_id
        fallback_shop_id = db.execute(text(f"""
            SELECT shop_id FROM {qname('dim_shop')}
            WHERE user_id = CAST(:user_id AS uuid) AND shop_name = '(Не определено)'
        """), params).scalar()
        
        # Add fallback_shop_id to params for use in query
        params["fallback_shop_id"] = str(fallback_shop_id)
        
        result = db.execute(text(f"""
            WITH src AS (
                SELECT
                    ss.user_id,
                    ss.upload_batch_id,
                    NULLIF(trim(ss.status_raw), '') AS status,
                    NULLIF(trim(ss.created_at_raw), '') AS created_at_raw,
                    NULLIF(trim(ss.received_at_raw), '') AS received_at_raw,
                    NULLIF(trim(ss.order_no_raw), '') AS order_no,
                    NULLIF(trim(ss.barcode_raw), '') AS barcode,
                    NULLIF(trim(ss.sku_raw), '') AS sku,
                    NULLIF(trim(ss.name_raw), '') AS product_name,
                    NULLIF(trim(ss.category_raw), '') AS category,
                    NULLIF(trim(ss.qty_raw), '') AS qty_raw,
                    NULLIF(trim(ss.returns_raw), '') AS returns_raw,
                    NULLIF(trim(ss.revenue_raw), '') AS revenue_raw,
                    NULLIF(trim(ss.revenue_net_raw), '') AS revenue_net_raw,
                    NULLIF(trim(ss.commission_raw), '') AS commission_raw,
                    NULLIF(trim(ss.logistics_raw), '') AS logistics_raw,
                    NULLIF(trim(ss.price_raw), '') AS price_raw,
                    NULLIF(trim(ss.promo_raw), '') AS promo_raw,
                    NULLIF(trim(ss.cogs_raw), '') AS cogs_raw
                FROM {qname('stg_sales')} ss
                WHERE ss.user_id = CAST(:user_id AS uuid) AND ss.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(ss.order_no_raw), '') IS NOT NULL
                  AND NULLIF(trim(ss.barcode_raw), '') IS NOT NULL
                  AND NULLIF(trim(ss.created_at_raw), '') IS NOT NULL
            ),
            casted AS (
                SELECT
                    s.user_id,
                    s.upload_batch_id,
                    COALESCE(m.shop_id, CAST(:fallback_shop_id AS uuid)) AS shop_id,
                    lower(trim(s.status)) AS status,
                    CASE
                        WHEN s.created_at_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN s.created_at_raw::timestamptz
                        WHEN s.created_at_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(s.created_at_raw, 'DD.MM.YYYY')::timestamptz
                        ELSE NULL
                    END AS date_created,
                    CASE
                        WHEN s.received_at_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN s.received_at_raw::timestamptz
                        WHEN s.received_at_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(s.received_at_raw, 'DD.MM.YYYY')::timestamptz
                        ELSE NULL
                    END AS date_received,
                    s.order_no,
                    s.sku,
                    s.barcode,
                    -- Normalize barcode: remove all whitespace, trim, preserve leading zeros
                    NULLIF(TRIM(regexp_replace(s.barcode, '\s+', '', 'g')), '') AS barcode_norm,
                    s.product_name,
                    s.category,
                    -- Integer fields: remove all non-digit characters except minus sign
                    COALESCE(NULLIF(regexp_replace(trim(s.qty_raw), '[^0-9-]', '', 'g'), '')::numeric::int, 0) AS qty,
                    COALESCE(NULLIF(regexp_replace(trim(s.returns_raw), '[^0-9-]', '', 'g'), '')::numeric::int, 0) AS returns_qty,
                    -- Numeric fields: remove all non-digit characters except digits, comma, dot, minus
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.revenue_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS revenue_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.revenue_net_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS revenue_net_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.commission_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS commission_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.logistics_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS logistics_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.price_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS price_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.promo_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS promo_sum,
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.cogs_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS cogs_sum
                FROM src s
                LEFT JOIN {qname('map_shop_sku')} m
                    ON m.user_id = s.user_id
                   AND m.barcode = s.barcode
            )
            INSERT INTO {qname('fact_sales')} (
                user_id, upload_batch_id, shop_id,
                status, date_created, date_received, order_no,
                sku, barcode, barcode_norm, product_name, category,
                qty, returns_qty,
                revenue_sum, revenue_net_sum, commission_sum, logistics_sum, price_sum, promo_sum, cogs_sum
            )
            SELECT
                user_id, upload_batch_id, shop_id,
                status, date_created, date_received, order_no,
                sku, barcode, barcode_norm, product_name, category,
                qty, returns_qty,
                revenue_sum, revenue_net_sum, commission_sum, logistics_sum, price_sum, promo_sum, cogs_sum
            FROM casted
            WHERE date_created IS NOT NULL
            ON CONFLICT (user_id, order_no, barcode, date_created) DO UPDATE
            SET
                upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = EXCLUDED.shop_id,
                status = EXCLUDED.status,
                date_received = EXCLUDED.date_received,
                sku = EXCLUDED.sku,
                barcode_norm = EXCLUDED.barcode_norm,
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                qty = EXCLUDED.qty,
                returns_qty = EXCLUDED.returns_qty,
                revenue_sum = EXCLUDED.revenue_sum,
                revenue_net_sum = EXCLUDED.revenue_net_sum,
                commission_sum = EXCLUDED.commission_sum,
                logistics_sum = EXCLUDED.logistics_sum,
                price_sum = EXCLUDED.price_sum,
                promo_sum = EXCLUDED.promo_sum,
                cogs_sum = EXCLUDED.cogs_sum
        """), params)
        count = result.rowcount
        
        # Populate map_shop_barcode from fact_sales (after insert)
        # Use most frequent sku/product_id for each barcode_norm
        db.execute(text(f"""
            INSERT INTO {qname('map_shop_barcode')} (user_id, upload_batch_id, shop_id, barcode_norm, sku, product_id)
            WITH ranked AS (
                SELECT DISTINCT
                    fs.user_id,
                    fs.upload_batch_id,
                    fs.shop_id,
                    fs.barcode_norm,
                    fs.sku,
                    fs.product_name AS product_id,  -- Using product_name as product_id fallback
                    ROW_NUMBER() OVER (
                        PARTITION BY fs.user_id, COALESCE(fs.shop_id, '00000000-0000-0000-0000-000000000000'::uuid), fs.barcode_norm
                        ORDER BY COUNT(*) DESC, fs.date_created DESC
                    ) AS rn
                FROM {qname('fact_sales')} fs
                WHERE fs.user_id = CAST(:user_id AS uuid) 
                  AND fs.upload_batch_id = CAST(:batch_id AS uuid)
                  AND fs.barcode_norm IS NOT NULL
                GROUP BY fs.user_id, fs.upload_batch_id, fs.shop_id, fs.barcode_norm, fs.sku, fs.product_name, fs.date_created
            )
            SELECT user_id, upload_batch_id, shop_id, barcode_norm, sku, product_id
            FROM ranked
            WHERE rn = 1
            ON CONFLICT (user_id, COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid), barcode_norm) DO UPDATE
            SET upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = COALESCE(EXCLUDED.shop_id, map_shop_barcode.shop_id),
                sku = COALESCE(EXCLUDED.sku, map_shop_barcode.sku),
                product_id = COALESCE(EXCLUDED.product_id, map_shop_barcode.product_id),
                last_seen_at = now()
        """), params)
        
        # Verification: Compare row counts and aggregates between stg_sales and fact_sales
        # This helps ensure no rows are lost during transformation
        verification = db.execute(text(f"""
            WITH stg_valid AS (
                -- Valid rows from stg_sales (with required fields)
                SELECT 
                    NULLIF(trim(barcode_raw), '') AS barcode
                FROM {qname('stg_sales')}
                WHERE user_id = CAST(:user_id AS uuid) 
                  AND upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(order_no_raw), '') IS NOT NULL
                  AND NULLIF(trim(barcode_raw), '') IS NOT NULL
                  AND NULLIF(trim(created_at_raw), '') IS NOT NULL
            ),
            stg_with_mapping AS (
                -- Rows from stg_sales that have mapping in map_shop_sku
                SELECT DISTINCT s.barcode
                FROM stg_valid s
                INNER JOIN {qname('map_shop_sku')} m
                    ON m.user_id = CAST(:user_id AS uuid)
                   AND m.barcode = s.barcode
            ),
            stg_counts AS (
                SELECT 
                    COUNT(*) AS stg_row_count,
                    COUNT(*) - COUNT(DISTINCT s.barcode) AS stg_duplicates,
                    COUNT(DISTINCT s.barcode) AS stg_unique_barcodes
                FROM stg_valid s
            ),
            stg_mapping_stats AS (
                SELECT 
                    COUNT(DISTINCT s.barcode) AS stg_with_mapping_count,
                    (SELECT COUNT(DISTINCT barcode) FROM stg_valid) - COUNT(DISTINCT s.barcode) AS stg_missing_mapping_count
                FROM stg_with_mapping s
            ),
            stg_agg AS (
                SELECT 
                    COALESCE(SUM(COALESCE(NULLIF(replace(replace(trim(qty_raw), ' ', ''), ',', '.'), '')::numeric::int, 0)), 0) AS stg_qty,
                    COALESCE(SUM(COALESCE(NULLIF(replace(replace(trim(revenue_raw), ' ', ''), ',', '.'), '')::numeric, 0)), 0) AS stg_revenue,
                    COALESCE(SUM(COALESCE(NULLIF(replace(replace(trim(returns_raw), ' ', ''), ',', '.'), '')::numeric::int, 0)), 0) AS stg_returns
                FROM {qname('stg_sales')}
                WHERE user_id = CAST(:user_id AS uuid) 
                  AND upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(order_no_raw), '') IS NOT NULL
                  AND NULLIF(trim(barcode_raw), '') IS NOT NULL
                  AND NULLIF(trim(created_at_raw), '') IS NOT NULL
            ),
            fact_counts AS (
                SELECT 
                    COUNT(*) AS fact_row_count,
                    COUNT(DISTINCT CASE WHEN shop_id = CAST(:fallback_shop_id AS uuid) THEN barcode END) AS fact_fallback_barcodes
                FROM {qname('fact_sales')}
                WHERE user_id = CAST(:user_id AS uuid) 
                  AND upload_batch_id = CAST(:batch_id AS uuid)
            ),
            fact_agg AS (
                SELECT 
                    COALESCE(SUM(qty), 0) AS fact_qty,
                    COALESCE(SUM(revenue_sum), 0) AS fact_revenue,
                    COALESCE(SUM(returns_qty), 0) AS fact_returns
                FROM {qname('fact_sales')}
                WHERE user_id = CAST(:user_id AS uuid) 
                  AND upload_batch_id = CAST(:batch_id AS uuid)
            )
            SELECT 
                stg_counts.stg_row_count,
                fact_counts.fact_row_count,
                stg_counts.stg_unique_barcodes,
                stg_mapping_stats.stg_with_mapping_count,
                stg_mapping_stats.stg_missing_mapping_count,
                fact_counts.fact_fallback_barcodes,
                stg_agg.stg_qty,
                fact_agg.fact_qty,
                stg_agg.stg_revenue,
                fact_agg.fact_revenue,
                stg_agg.stg_returns,
                fact_agg.fact_returns,
                CASE WHEN stg_counts.stg_row_count = fact_counts.fact_row_count THEN 'OK' ELSE 'MISMATCH' END AS row_count_match,
                CASE WHEN stg_agg.stg_qty = fact_agg.fact_qty THEN 'OK' ELSE 'MISMATCH' END AS qty_match,
                CASE WHEN ABS(stg_agg.stg_revenue - fact_agg.fact_revenue) < 0.01 THEN 'OK' ELSE 'MISMATCH' END AS revenue_match,
                CASE WHEN stg_agg.stg_returns = fact_agg.fact_returns THEN 'OK' ELSE 'MISMATCH' END AS returns_match
            FROM stg_counts, stg_mapping_stats, stg_agg, fact_counts, fact_agg
        """), params).fetchone()
        
        if verification:
            logger.info(
                f"Sales import verification (batch_id={batch_id}): "
                f"rows: stg={verification[0]} fact={verification[1]} ({verification[12]}), "
                f"unique_barcodes: stg={verification[2]}, "
                f"mapping: with={verification[3]} missing={verification[4]}, "
                f"fallback_barcodes: fact={verification[5]}, "
                f"qty: stg={verification[6]} fact={verification[7]} ({verification[13]}), "
                f"revenue: stg={verification[8]} fact={verification[9]} ({verification[14]}), "
                f"returns: stg={verification[10]} fact={verification[11]} ({verification[15]})"
            )
        
        # Debug: Check rows where returns_qty > 0 but price_sum = 0 (potential parsing issues)
        debug_rows = db.execute(text(f"""
            SELECT 
                order_no,
                barcode,
                status,
                returns_qty,
                price_sum,
                COALESCE(returns_qty, 0) * COALESCE(price_sum, 0) AS returns_value_calc
            FROM {qname('fact_sales')}
            WHERE user_id = CAST(:user_id AS uuid) 
              AND upload_batch_id = CAST(:batch_id AS uuid)
              AND COALESCE(returns_qty, 0) > 0
              AND COALESCE(price_sum, 0) = 0
            ORDER BY returns_qty DESC
            LIMIT 20
        """), params).fetchall()
        
        if debug_rows:
            logger.warning(
                f"Sales import debug (batch_id={batch_id}): Found {len(debug_rows)} rows with returns_qty>0 but price_sum=0. "
                f"Top 5: {[(r[0], r[1], r[2], r[3], r[4]) for r in debug_rows[:5]]}"
            )
        else:
            logger.info(
                f"Sales import debug (batch_id={batch_id}): No rows with returns_qty>0 and price_sum=0 found (parsing OK)"
            )
        
        # Note: No commit here - caller will commit the transaction
        return count
    
    elif report_type == "expenses":
        db.execute(text(f"DELETE FROM {qname('fact_expenses')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        result = db.execute(text(f"""
            WITH src AS (
                SELECT
                    se.user_id,
                    se.upload_batch_id,
                    NULLIF(trim(se.source_raw), '') AS source,
                    NULLIF(trim(se.service_raw), '') AS service,
                    NULLIF(trim(se.status_raw), '') AS status,
                    NULLIF(trim(se.operation_id_raw), '') AS operation_id,
                    NULLIF(trim(se.written_off_raw), '') AS written_off_raw,
                    NULLIF(trim(se.cost_raw), '') AS cost_raw,
                    NULLIF(trim(se.qty_raw), '') AS qty_raw,
                    NULLIF(trim(se.amount_raw), '') AS amount_raw,
                    NULLIF(trim(se.operation_type_raw), '') AS operation_type
                FROM {qname('stg_expenses')} se
                WHERE se.user_id = CAST(:user_id AS uuid) AND se.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(se.operation_id_raw), '') IS NOT NULL
            ),
            casted AS (
                SELECT
                    user_id, upload_batch_id, source, service, status, operation_id,
                    CASE
                        WHEN written_off_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN written_off_raw::timestamptz
                        WHEN written_off_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(written_off_raw, 'DD.MM.YYYY')::timestamptz
                        ELSE NULL
                    END AS date_written_off,
                    NULLIF(replace(replace(cost_raw, ' ', ''), ',', '.'), '')::numeric AS cost_sum,
                    COALESCE(NULLIF(replace(replace(qty_raw, ' ', ''), ',', '.'), '')::numeric::int, 0) AS qty,
                    NULLIF(replace(replace(amount_raw, ' ', ''), ',', '.'), '')::numeric AS amount_sum,
                    operation_type
                FROM src
            )
            INSERT INTO {qname('fact_expenses')} (
                user_id, upload_batch_id,
                source, service, status, operation_id, date_written_off,
                cost_sum, qty, amount_sum, operation_type
            )
            SELECT
                user_id, upload_batch_id,
                source, service, status, operation_id, date_written_off,
                COALESCE(cost_sum, 0), qty, COALESCE(amount_sum, 0), operation_type
            FROM casted
            WHERE date_written_off IS NOT NULL
            ON CONFLICT (user_id, operation_id) DO UPDATE
            SET
                upload_batch_id = EXCLUDED.upload_batch_id,
                source = EXCLUDED.source,
                service = EXCLUDED.service,
                status = EXCLUDED.status,
                date_written_off = EXCLUDED.date_written_off,
                cost_sum = EXCLUDED.cost_sum,
                qty = EXCLUDED.qty,
                amount_sum = EXCLUDED.amount_sum,
                operation_type = EXCLUDED.operation_type
        """), params)
        count = result.rowcount
        # Note: No commit here - caller will commit the transaction
        return count
    
    elif report_type == "inventory":
        # Update barcode_norm in staging table (normalize barcode_raw)
        db.execute(text(f"""
            UPDATE {qname('stg_leftout')}
            SET barcode_norm = NULLIF(TRIM(regexp_replace(barcode_raw, '\s+', '', 'g')), '')
            WHERE user_id = CAST(:user_id AS uuid) 
              AND upload_batch_id = CAST(:batch_id AS uuid)
              AND barcode_raw IS NOT NULL
        """), params)
        
        # First upsert shops
        db.execute(text(f"""
            WITH shops AS (
                SELECT DISTINCT
                    sl.user_id,
                    NULLIF(trim(sl.shop_raw), '') AS shop_name
                FROM {qname('stg_leftout')} sl
                WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(sl.shop_raw), '') IS NOT NULL
            )
            INSERT INTO {qname('dim_shop')} (user_id, shop_name)
            SELECT user_id, shop_name
            FROM shops
            ON CONFLICT (user_id, shop_name) DO NOTHING
        """), params)
        
        # Update map_shop_sku
        db.execute(text(f"DELETE FROM {qname('map_shop_sku')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        db.execute(text(f"""
            INSERT INTO {qname('map_shop_sku')} (user_id, upload_batch_id, shop_id, barcode, sku)
            SELECT DISTINCT
                sl.user_id,
                sl.upload_batch_id,
                ds.shop_id,
                NULLIF(trim(sl.barcode_raw), '') AS barcode,
                NULLIF(trim(sl.sku_raw), '') AS sku
            FROM {qname('stg_leftout')} sl
            JOIN {qname('dim_shop')} ds ON ds.user_id = sl.user_id AND ds.shop_name = NULLIF(trim(sl.shop_raw), '')
            WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND NULLIF(trim(sl.barcode_raw), '') IS NOT NULL
            ON CONFLICT (user_id, barcode) DO UPDATE
            SET upload_batch_id = EXCLUDED.upload_batch_id, shop_id = EXCLUDED.shop_id, sku = EXCLUDED.sku
        """), params)
        
        # Update map_shop_barcode (normalized barcode mapping)
        db.execute(text(f"DELETE FROM {qname('map_shop_barcode')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        db.execute(text(f"""
            INSERT INTO {qname('map_shop_barcode')} (user_id, upload_batch_id, shop_id, barcode_norm, sku, product_id)
            SELECT DISTINCT
                sl.user_id,
                sl.upload_batch_id,
                ds.shop_id,
                NULLIF(TRIM(regexp_replace(trim(sl.barcode_raw), '\s+', '', 'g')), '') AS barcode_norm,
                NULLIF(trim(sl.sku_raw), '') AS sku,
                NULLIF(trim(sl.product_id_raw), '') AS product_id
            FROM {qname('stg_leftout')} sl
            JOIN {qname('dim_shop')} ds ON ds.user_id = sl.user_id AND ds.shop_name = NULLIF(trim(sl.shop_raw), '')
            WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND NULLIF(TRIM(regexp_replace(trim(sl.barcode_raw), '\s+', '', 'g')), '') IS NOT NULL
            ON CONFLICT (user_id, COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid), barcode_norm) DO UPDATE
            SET upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = COALESCE(EXCLUDED.shop_id, map_shop_barcode.shop_id),
                sku = COALESCE(EXCLUDED.sku, map_shop_barcode.sku),
                product_id = COALESCE(EXCLUDED.product_id, map_shop_barcode.product_id),
                last_seen_at = now()
        """), params)
        
        # Delete old batch data
        db.execute(text(f"DELETE FROM {qname('fact_leftout_snapshot')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        result = db.execute(text(f"""
            WITH src AS (
                SELECT
                    sl.user_id,
                    sl.upload_batch_id,
                    ds.shop_id,
                    NULLIF(trim(sl.barcode_raw), '') AS barcode_raw,
                    NULLIF(trim(sl.product_name_raw), '') AS product_name_raw,
                    NULLIF(trim(sl.product_id_raw), '') AS product_id_raw,
                    NULLIF(trim(sl.sku_raw), '') AS sku_raw,
                    NULLIF(trim(sl.ending_raw), '') AS ending_raw,
                    NULLIF(trim(sl.availability_ind_raw), '') AS availability_ind_raw,
                    NULLIF(trim(sl.planned_end_raw), '') AS planned_end_raw,
                    NULLIF(trim(sl.coverage_days_raw), '') AS coverage_days_raw,
                    NULLIF(trim(sl.recommended_qty_raw), '') AS recommended_qty_raw,
                    NULLIF(trim(sl.on_your_side_fbs_raw), '') AS on_your_side_fbs_raw,
                    NULLIF(trim(sl.on_marketplace_side_raw), '') AS on_marketplace_side_raw,
                    NULLIF(trim(sl.in_supply_raw), '') AS in_supply_raw,
                    NULLIF(trim(sl.in_sale_raw), '') AS in_sale_raw,
                    NULLIF(trim(sl.to_customer_raw), '') AS to_customer_raw,
                    NULLIF(trim(sl.from_customer_raw), '') AS from_customer_raw,
                    NULLIF(trim(sl.sdh_raw), '') AS sdh_raw,
                    NULLIF(trim(sl.photo_raw), '') AS photo_raw,
                    NULLIF(trim(sl.defect_raw), '') AS defect_raw,
                    NULLIF(trim(sl.potential_per_unit_raw), '') AS potential_per_unit_raw,
                    NULLIF(trim(sl.potential_total_raw), '') AS potential_total_raw
                FROM {qname('stg_leftout')} sl
                JOIN {qname('dim_shop')} ds
                    ON ds.user_id = sl.user_id
                   AND ds.shop_name = NULLIF(trim(sl.shop_raw), '')
                WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(sl.barcode_raw), '') IS NOT NULL
            ),
            casted AS (
                SELECT
                    user_id,
                    upload_batch_id,
                    shop_id,
                    NULLIF(trim(barcode_raw), '') AS barcode,
                    -- Normalize barcode: remove all whitespace, trim, preserve leading zeros
                    NULLIF(TRIM(regexp_replace(trim(barcode_raw), '\s+', '', 'g')), '') AS barcode_norm,
                    NULLIF(trim(product_name_raw), '') AS product_name,
                    NULLIF(trim(product_id_raw), '') AS product_id,
                    NULLIF(trim(sku_raw), '') AS sku,
                    NULLIF(trim(ending_raw), '') AS ending,
                    NULLIF(trim(availability_ind_raw), '') AS availability_indicator,
                    CASE
                        WHEN planned_end_raw IS NULL OR trim(planned_end_raw) IN ('', '—', '-') THEN NULL
                        WHEN planned_end_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}$' THEN planned_end_raw::date
                        WHEN planned_end_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}$' THEN to_date(trim(planned_end_raw), 'DD.MM.YYYY')
                        ELSE NULL
                    END AS planned_end_date,
                    CASE 
                        WHEN coverage_days_raw IS NULL OR trim(coverage_days_raw) = '' THEN NULL
                        WHEN trim(coverage_days_raw) ~ '^\\s*\\d+(\\.\\d+)?\\s*$' THEN CAST(replace(regexp_replace(trim(coverage_days_raw), '[^0-9,.-]', '', 'g'), ',', '.') AS numeric(10,2))
                        ELSE NULL
                    END AS coverage_days,
                    CAST(NULLIF(regexp_replace(trim(recommended_qty_raw), '[^0-9]', '', 'g'), '') AS int) AS recommended_qty,
                    CAST(NULLIF(regexp_replace(trim(on_your_side_fbs_raw), '[^0-9]', '', 'g'), '') AS int) AS fbs_stock,
                    CAST(NULLIF(regexp_replace(trim(on_marketplace_side_raw), '[^0-9]', '', 'g'), '') AS int) AS marketplace_side,
                    CAST(NULLIF(regexp_replace(trim(in_supply_raw), '[^0-9]', '', 'g'), '') AS int) AS in_supply,
                    CAST(NULLIF(regexp_replace(trim(in_sale_raw), '[^0-9]', '', 'g'), '') AS int) AS in_sale,
                    CAST(NULLIF(regexp_replace(trim(to_customer_raw), '[^0-9]', '', 'g'), '') AS int) AS to_customer,
                    CAST(NULLIF(regexp_replace(trim(from_customer_raw), '[^0-9]', '', 'g'), '') AS int) AS from_customer,
                    CAST(NULLIF(regexp_replace(trim(sdh_raw), '[^0-9]', '', 'g'), '') AS int) AS sdh_stock,
                    CAST(NULLIF(regexp_replace(trim(photo_raw), '[^0-9]', '', 'g'), '') AS int) AS photo_stock,
                    CAST(NULLIF(regexp_replace(trim(defect_raw), '[^0-9]', '', 'g'), '') AS int) AS defect_stock,
                    CAST(replace(NULLIF(regexp_replace(trim(potential_per_unit_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS potential_per_unit,
                    CAST(replace(NULLIF(regexp_replace(trim(potential_total_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS potential_total
                FROM src
            )
            INSERT INTO {qname('fact_leftout_snapshot')} (
                user_id, upload_batch_id, shop_id,
                product_name, product_id, sku, barcode, barcode_norm,
                ending, availability_indicator, planned_end_date, coverage_days,
                recommended_qty, fbs_stock, marketplace_side, in_supply, in_sale,
                to_customer, from_customer, sdh_stock, photo_stock, defect_stock,
                potential_per_unit, potential_total
            )
            SELECT
                user_id, upload_batch_id, shop_id,
                product_name, product_id, sku, barcode, barcode_norm,
                ending, availability_indicator, planned_end_date, coverage_days,
                recommended_qty, fbs_stock, marketplace_side, in_supply, in_sale,
                to_customer, from_customer, sdh_stock, photo_stock, defect_stock,
                potential_per_unit, potential_total
            FROM casted
            ON CONFLICT (user_id, upload_batch_id, shop_id, sku) DO UPDATE
            SET
                product_name = EXCLUDED.product_name,
                product_id = EXCLUDED.product_id,
                barcode = EXCLUDED.barcode,
                ending = EXCLUDED.ending,
                availability_indicator = EXCLUDED.availability_indicator,
                planned_end_date = EXCLUDED.planned_end_date,
                coverage_days = EXCLUDED.coverage_days,
                recommended_qty = EXCLUDED.recommended_qty,
                fbs_stock = EXCLUDED.fbs_stock,
                marketplace_side = EXCLUDED.marketplace_side,
                in_supply = EXCLUDED.in_supply,
                in_sale = EXCLUDED.in_sale,
                to_customer = EXCLUDED.to_customer,
                from_customer = EXCLUDED.from_customer,
                sdh_stock = EXCLUDED.sdh_stock,
                photo_stock = EXCLUDED.photo_stock,
                defect_stock = EXCLUDED.defect_stock,
                potential_per_unit = EXCLUDED.potential_per_unit,
                potential_total = EXCLUDED.potential_total
        """), params)
        count = result.rowcount
        # Note: No commit here - caller will commit the transaction
        return count
    
    elif report_type == "storage":
        # Update barcode_norm in staging table (normalize barcode_raw)
        db.execute(text(f"""
            UPDATE {qname('stg_storage')}
            SET barcode_norm = NULLIF(TRIM(regexp_replace(barcode_raw, '\s+', '', 'g')), '')
            WHERE user_id = CAST(:user_id AS uuid) 
              AND upload_batch_id = CAST(:batch_id AS uuid)
              AND barcode_raw IS NOT NULL
        """), params)
        # Upsert shops
        db.execute(text(f"""
            WITH shops AS (
                SELECT DISTINCT
                    ss.user_id,
                    NULLIF(trim(ss.shop_raw), '') AS shop_name
                FROM {qname('stg_storage')} ss
                WHERE ss.user_id = CAST(:user_id AS uuid) AND ss.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(ss.shop_raw), '') IS NOT NULL
            )
            INSERT INTO {qname('dim_shop')} (user_id, shop_name)
            SELECT user_id, shop_name
            FROM shops
            ON CONFLICT (user_id, shop_name) DO NOTHING
        """), params)
        
        # Delete old batch data
        db.execute(text(f"DELETE FROM {qname('fact_storage_snapshot')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"), params)
        
        result = db.execute(text(f"""
            WITH src AS (
                SELECT
                    ss.user_id,
                    ss.upload_batch_id,
                    ds.shop_id,
                    NULLIF(trim(ss.product_name_raw), '') AS product_name_raw,
                    NULLIF(trim(ss.product_id_raw), '') AS product_id_raw,
                    NULLIF(trim(ss.sku_raw), '') AS sku_raw,
                    NULLIF(trim(ss.barcode_raw), '') AS barcode_raw,
                    NULLIF(trim(ss.size_group_raw), '') AS size_group_raw,
                    NULLIF(trim(ss.turnover_days_raw), '') AS turnover_days_raw,
                    NULLIF(trim(ss.storage_type_raw), '') AS storage_type_raw,
                    NULLIF(trim(ss.fee_total_30d_raw), '') AS fee_total_30d_raw
                FROM {qname('stg_storage')} ss
                JOIN {qname('dim_shop')} ds
                    ON ds.user_id = ss.user_id
                   AND ds.shop_name = NULLIF(trim(ss.shop_raw), '')
                WHERE ss.user_id = CAST(:user_id AS uuid) AND ss.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(ss.barcode_raw), '') IS NOT NULL
            ),
            casted AS (
                SELECT
                    user_id, upload_batch_id, shop_id,
                    NULLIF(trim(product_name_raw), '') AS product_name,
                    NULLIF(trim(product_id_raw), '') AS product_id,
                    NULLIF(trim(sku_raw), '') AS sku,
                    NULLIF(trim(barcode_raw), '') AS barcode,
                    -- Normalize barcode: remove all whitespace, trim, preserve leading zeros
                    NULLIF(TRIM(regexp_replace(trim(barcode_raw), '\s+', '', 'g')), '') AS barcode_norm,
                    NULLIF(trim(size_group_raw), '') AS size_group,
                    CAST(replace(NULLIF(regexp_replace(trim(turnover_days_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,4)) AS turnover_days,
                    NULLIF(trim(storage_type_raw), '') AS storage_type,
                    CAST(replace(NULLIF(regexp_replace(trim(fee_total_30d_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS fee_total_30d
                FROM src
            )
            INSERT INTO {qname('fact_storage_snapshot')} (
                user_id, upload_batch_id, shop_id,
                product_name, product_id, sku, barcode, barcode_norm, size_group,
                turnover_days, storage_type, fee_total_30d
            )
            SELECT
                user_id, upload_batch_id, shop_id,
                product_name, product_id, sku, barcode, barcode_norm, size_group,
                turnover_days, storage_type, fee_total_30d
            FROM casted
            ON CONFLICT (user_id, upload_batch_id, shop_id, sku) DO UPDATE
            SET
                product_name = EXCLUDED.product_name,
                product_id = EXCLUDED.product_id,
                barcode = EXCLUDED.barcode,
                barcode_norm = EXCLUDED.barcode_norm,
                size_group = EXCLUDED.size_group,
                turnover_days = EXCLUDED.turnover_days,
                storage_type = EXCLUDED.storage_type,
                fee_total_30d = EXCLUDED.fee_total_30d
        """), params)
        count = result.rowcount
        # Note: No commit here - caller will commit the transaction
        return count
    
    return 0


@router.post("/import-xlsx")
async def import_xlsx(
    file: UploadFile = File(...),
    reportType: str = Form(...),
    fileName: Optional[str] = Form(None),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Import XLSX report file with overwrite mode.
    
    Accepts:
    - file: XLSX file (multipart/form-data)
    - reportType: sales|inventory|expenses|storage|leftout
    - fileName: optional file name
    
    Returns:
    - ok: true
    - reportType: report type
    - upload_batch_id: UUID of the batch
    - saved_as: path where file was saved
    - rowsImported: number of rows imported to fact tables
    """
    
    # Validate reportType - accept common variants
    valid_report_types = ["sales", "inventory", "expenses", "storage", "leftout"]
    if reportType not in valid_report_types:
        logger.warning(f"Unknown reportType: {reportType}, accepting anyway")
        # Don't fail, just log warning
    
    # Validate file extension
    original_filename = fileName or file.filename or "upload.xlsx"
    if not original_filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only .xlsx and .xls files are supported"
        )
    
    # Start transaction - all operations in one transaction
    try:
        # Step 1: Delete old data ONLY for this report type (overwrite per reportType)
        # This keeps other report types (e.g. inventory vs sales) intact.
        try:
            delete_old_data(db, user_id, reportType)
        except Exception as e:
            logger.error(f"Error deleting old data for reportType={reportType}: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting old data for reportType={reportType}: {str(e)}"
            )
        
        # Step 2: Create new batch
        try:
            batch_id = create_batch(db, user_id)
            # Note: create_batch does NOT commit - we'll commit at the end
        except Exception as e:
            logger.error(f"Error creating batch: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating batch: {str(e)}"
            )
        
        # Step 3: Save file to disk
        project_root = Path(__file__).parent.parent.parent.parent
        uploads_base = project_root / "apps" / "api" / "uploads"
        user_dir = uploads_base / str(user_id)
        batch_dir = user_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        file_ext = Path(original_filename).suffix or ".xlsx"
        saved_filename = f"{reportType}{file_ext}"
        saved_path = batch_dir / saved_filename
        
        file_content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(file_content)
        
        saved_as = str(saved_path)
        
        # Step 4: Parse and import data
        # Map reportType to internal file_type
        file_type = REPORT_TYPE_TO_FILE_TYPE.get(reportType, reportType)
        sheet_name = SHEETS.get(file_type, SHEETS.get(reportType, "Sheet1"))
        
        # Read Excel file
        try:
            df = read_excel_as_str(file_content, sheet_name, file_type)
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Error reading Excel file: {str(e)}"
            )
        
        if df.empty:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail="Excel file is empty or has no valid data"
            )
        
        # Validate required columns
        try:
            validate_required(df, file_type)
        except ValueError as e:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=str(e)
            )
        
        # Get mapping
        mapping = {
            "sales": SALES_MAP,
            "expenses": EXP_MAP,
            "inventory": LEFTOUT_MAP,
            "storage": STORAGE_MAP,
        }.get(reportType, {})
        
        if not mapping:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"No mapping found for reportType: {reportType}"
            )
        
        # Step 5: Load to staging
        staging_table = {
            "sales": "stg_sales",
            "expenses": "stg_expenses",
            "inventory": "stg_leftout",
            "storage": "stg_storage",
        }.get(reportType)
        
        if not staging_table:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"No staging table found for reportType: {reportType}"
            )
        
        try:
            to_staging(df, mapping, str(user_id), batch_id, staging_table, db, file_type)
        except Exception as e:
            logger.error(f"Error loading to staging: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error loading to staging: {str(e)}"
            )
        
        # Step 6: Transform to fact tables
        try:
            rows_imported = populate_facts(db, user_id, batch_id, reportType)
        except Exception as e:
            logger.error(f"Error populating fact tables: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error populating fact tables: {str(e)}"
            )
        
        # Step 7: Commit transaction (all operations succeeded)
        db.commit()
        
        # Step 8: Log success with row counts per table
        # Get row counts per fact table for detailed logging
        user_id_str = str(user_id)
        params_log = {"user_id": user_id_str, "batch_id": batch_id}
        
        sales_count = db.execute(
            text(f"SELECT COUNT(*) FROM {qname('fact_sales')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
            params_log
        ).scalar() or 0
        
        expenses_count = db.execute(
            text(f"SELECT COUNT(*) FROM {qname('fact_expenses')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
            params_log
        ).scalar() or 0
        
        inventory_count = db.execute(
            text(f"SELECT COUNT(*) FROM {qname('fact_leftout_snapshot')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
            params_log
        ).scalar() or 0
        
        storage_count = db.execute(
            text(f"SELECT COUNT(*) FROM {qname('fact_storage_snapshot')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
            params_log
        ).scalar() or 0
        
        logger.info(
            f"Import successful (overwrite mode): user_id={user_id}, upload_batch_id={batch_id}, "
            f"reportType={reportType}, rowsImported={rows_imported}, "
            f"fact_sales={sales_count}, fact_expenses={expenses_count}, "
            f"fact_leftout_snapshot={inventory_count}, fact_storage_snapshot={storage_count}, "
            f"saved_as={saved_as}"
        )
        
        return {
            "ok": True,
            "reportType": reportType,
            "upload_batch_id": batch_id,
            "saved_as": saved_as,
            "rowsImported": rows_imported
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in import_xlsx: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/import-xlsx-batch")
async def import_xlsx_batch(
    salesFile: Optional[UploadFile] = File(None),
    inventoryFile: Optional[UploadFile] = File(None),
    expensesFile: Optional[UploadFile] = File(None),
    storageFile: Optional[UploadFile] = File(None),
    fileNameSales: Optional[str] = Form(None),
    fileNameInventory: Optional[str] = Form(None),
    fileNameExpenses: Optional[str] = Form(None),
    fileNameStorage: Optional[str] = Form(None),
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Batch import of 4 XLSX report files in one transaction.
    
    Accepts:
    - salesFile: XLSX file for sales report
    - inventoryFile: XLSX file for inventory report (leftout)
    - expensesFile: XLSX file for expenses report
    - storageFile: XLSX file for storage report
    - fileNameSales, fileNameInventory, fileNameExpenses, fileNameStorage: optional file names
    
    Returns:
    - ok: true
    - upload_batch_id: UUID of the batch
    - imported: dict with row counts per report type
    - saved_as: dict with file paths per report type
    
    Import order: inventory → sales → expenses → storage
    (inventory first to populate dim_shop and map_shop_sku)
    """
    
    # Validate that all files are provided
    files = {
        "sales": salesFile,
        "inventory": inventoryFile,
        "expenses": expensesFile,
        "storage": storageFile,
    }
    
    missing_files = [report_type for report_type, file in files.items() if file is None]
    if missing_files:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required files: {', '.join(missing_files)}"
        )
    
    # Validate file extensions
    file_names = {
        "sales": fileNameSales or salesFile.filename or "sales.xlsx",
        "inventory": fileNameInventory or inventoryFile.filename or "inventory.xlsx",
        "expenses": fileNameExpenses or expensesFile.filename or "expenses.xlsx",
        "storage": fileNameStorage or storageFile.filename or "storage.xlsx",
    }
    
    for report_type, filename in file_names.items():
        if not filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for {report_type}: {filename}. Only .xlsx and .xls files are supported"
            )
    
    # Start transaction - all operations in one transaction
    try:
        # Step 1: Delete ALL old data for this user (overwrite mode) - ONCE
        try:
            delete_all_user_data(db, user_id)
            # Note: delete_all_user_data doesn't commit, we'll commit at the end
        except Exception as e:
            logger.error(f"Error deleting old data: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting old data: {str(e)}"
            )
        
        # Step 2: Create new batch - ONE batch for all files
        try:
            batch_id = create_batch(db, user_id)
            # Note: create_batch does NOT commit - we'll commit at the end
        except Exception as e:
            logger.error(f"Error creating batch: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Error creating batch: {str(e)}"
            )
        
        # Step 3: Prepare upload directory
        project_root = Path(__file__).parent.parent.parent.parent
        uploads_base = project_root / "apps" / "api" / "uploads"
        user_dir = uploads_base / str(user_id)
        batch_dir = user_dir / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 4: Import files in correct order: inventory → sales → expenses → storage
        # Order matters: inventory first to populate dim_shop and map_shop_sku
        import_order = [
            ("inventory", inventoryFile, fileNameInventory, "leftout", "Остатки (новый)", LEFTOUT_MAP, "stg_leftout"),
            ("sales", salesFile, fileNameSales, "sales", "Отчет по продажам", SALES_MAP, "stg_sales"),
            ("expenses", expensesFile, fileNameExpenses, "expenses", "Отчет по услугам", EXP_MAP, "stg_expenses"),
            ("storage", storageFile, fileNameStorage, "storage", "Отчет по хранению", STORAGE_MAP, "stg_storage"),
        ]
        
        imported_counts = {}
        saved_paths = {}
        
        for report_type, file_obj, file_name, file_type, sheet_name, mapping, staging_table in import_order:
            try:
                # Read file content (only once - file.read() consumes the stream)
                file_content = await file_obj.read()
                
                # Save file to disk
                file_ext = Path(file_name or file_obj.filename or f"{report_type}.xlsx").suffix or ".xlsx"
                saved_filename = f"{report_type}{file_ext}"
                saved_path = batch_dir / saved_filename
                
                with open(saved_path, "wb") as f:
                    f.write(file_content)
                
                saved_paths[report_type] = str(saved_path)
                
                # Read Excel file (reuse file_content)
                try:
                    df = read_excel_as_str(file_content, sheet_name, file_type)
                except Exception as e:
                    logger.error(f"Error reading Excel file for {report_type}: {e}", exc_info=True)
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Error reading {report_type} Excel file: {str(e)}"
                    )
                
                if df.empty:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"{report_type} Excel file is empty or has no valid data"
                    )
                
                # Validate required columns
                try:
                    validate_required(df, file_type)
                except ValueError as e:
                    db.rollback()
                    raise HTTPException(
                        status_code=400,
                        detail=f"{report_type}: {str(e)}"
                    )
                
                # Load to staging
                try:
                    to_staging(df, mapping, str(user_id), batch_id, staging_table, db, file_type)
                except Exception as e:
                    logger.error(f"Error loading {report_type} to staging: {e}", exc_info=True)
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error loading {report_type} to staging: {str(e)}"
                    )
                
                # Transform to fact tables
                try:
                    rows_imported = populate_facts(db, user_id, batch_id, report_type)
                    imported_counts[report_type] = rows_imported
                except Exception as e:
                    logger.error(f"Error populating {report_type} fact tables: {e}", exc_info=True)
                    db.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error populating {report_type} fact tables: {str(e)}"
                    )
                
                logger.info(f"Imported {report_type}: {rows_imported} rows, batch_id={batch_id}")
                
            except HTTPException:
                # Re-raise HTTPException to preserve status code and detail
                raise
            except Exception as e:
                logger.error(f"Unexpected error importing {report_type}: {e}", exc_info=True)
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected error importing {report_type}: {str(e)}"
                )
        
        # Step 5: Commit transaction (all operations succeeded)
        db.commit()
        
        # Step 6: Log success with row counts per table
        logger.info(
            f"Batch import successful: user_id={user_id}, upload_batch_id={batch_id}, "
            f"imported={imported_counts}, saved_as={saved_paths}"
        )
        
        return {
            "ok": True,
            "upload_batch_id": batch_id,
            "imported": imported_counts,
            "saved_as": saved_paths
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in import_xlsx_batch: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
