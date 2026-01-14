import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

SHEETS = {
    "sales": "Отчет по продажам",
    "expenses": "Отчет по услугам",
    "leftout": "Остатки (новый)",
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

# ВАЖНО: теперь ключ = штрихкод
REQUIRED = {
    "sales": ["Дата создания", "№ заказа", "Штрихкод"],
    "expenses": ["ID операции", "Дата списания"],
    "leftout": ["Магазин", "Штрихкод"],
    "storage": ["Магазин", "Штрихкод"],
}

def make_engine():
    load_dotenv()
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")
    if not all([db, user, pwd]):
        raise RuntimeError("Заполни .env: PGDATABASE, PGUSER, PGPASSWORD")
    url = f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"
    return create_engine(url, future=True)

def norm(s):
    """Normalize column name: remove newlines, non-breaking spaces, normalize whitespace."""
    return " ".join(str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ").strip().split())


def read_excel_as_str(path: Path, sheet: str, file_type: str = None) -> pd.DataFrame:
    """Read Excel with header=1 and proper converters for barcode/sku."""
    # Converters to preserve leading zeros in barcode/sku
    converters = {}
    if file_type in ("leftout", "storage"):
        converters = {
            "Штрихкод": lambda x: str(x) if pd.notna(x) else "",
            "SKU": lambda x: str(x) if pd.notna(x) else "",
        }
    
    df = pd.read_excel(
        path,
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
    missing = [c for c in REQUIRED[file_type] if c not in df.columns]
    if missing:
        raise ValueError(f"[{file_type}] Не найдены обязательные колонки: {missing}. Найдено: {list(df.columns)}")

def to_staging(df: pd.DataFrame, mapping: dict, user_id: str, batch_id: str, table: str, engine, file_type: str = None):
    """Load data to staging table with proper type handling for leftout/storage."""
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

    out.to_sql(
        name=table,
        schema="app",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000,
    )

def get_or_create_user(engine, email: str) -> str:
    with engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT user_id FROM app.user_account WHERE email=:e"),
            {"e": email},
        ).scalar()

        if user_id:
            return str(user_id)

        now = datetime.utcnow()
        trial_ends = now + timedelta(days=10)
        user_id = conn.execute(
            text("""
                INSERT INTO app.user_account(email, password_hash, created_at, plan, trial_started_at, trial_ends_at)
                VALUES (:e, :ph, now(), 'trial', :ts, :te)
                RETURNING user_id
            """),
            {"e": email, "ph": "local_import_placeholder", "ts": now, "te": trial_ends},
        ).scalar()
        return str(user_id)

def create_batch(engine, user_id: str) -> str:
    with engine.begin() as conn:
        batch_id = conn.execute(
            text("""
                INSERT INTO app.upload_batch(user_id, status, is_current)
                VALUES (:u, 'processing', false)
                RETURNING upload_batch_id
            """),
            {"u": user_id},
        ).scalar()
        return str(batch_id)

def register_file(engine, batch_id: str, file_type: str, path: Path):
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO app.upload_file(upload_batch_id, file_type, original_name, stored_path, status)
                VALUES (:b, :t, :n, :p, 'uploaded')
                ON CONFLICT (upload_batch_id, file_type) DO UPDATE
                SET original_name=EXCLUDED.original_name,
                    stored_path=EXCLUDED.stored_path,
                    uploaded_at=now(),
                    status='uploaded',
                    error_message=NULL
            """),
            {"b": batch_id, "t": file_type, "n": path.name, "p": str(path)},
        )

def mark_file_parsed(engine, batch_id: str, file_type: str):
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE app.upload_file
                SET status='parsed', parsed_at=now(), error_message=NULL
                WHERE upload_batch_id=:b AND file_type=:t
            """),
            {"b": batch_id, "t": file_type},
        )

def populate_facts(engine, user_id: str, batch_id: str):
    """Populate fact tables from staging tables for the given batch."""
    params = {"user_id": user_id, "batch_id": batch_id}
    
    with engine.begin() as conn:
        # 1) Upsert shops from stg_leftout
        conn.execute(
            text("""
                WITH shops AS (
                    SELECT DISTINCT
                        sl.user_id,
                        NULLIF(trim(sl.shop_raw), '') AS shop_name
                    FROM app.stg_leftout sl
                    WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
                      AND NULLIF(trim(sl.shop_raw), '') IS NOT NULL
                )
                INSERT INTO app.dim_shop (user_id, shop_name)
                SELECT user_id, shop_name
                FROM shops
                ON CONFLICT (user_id, shop_name) DO NOTHING
            """),
            params
        )
        
        # 2) Update map_shop_sku for this batch (barcode-based)
        conn.execute(
            text("""
                DELETE FROM app.map_shop_sku m
                WHERE m.user_id = CAST(:user_id AS uuid) AND m.upload_batch_id = CAST(:batch_id AS uuid)
            """),
            params
        )
        
        conn.execute(
            text("""
                WITH src AS (
                    SELECT DISTINCT
                        sl.user_id,
                        sl.upload_batch_id,
                        ds.shop_id,
                        NULLIF(trim(sl.barcode_raw), '') AS barcode,
                        NULLIF(trim(sl.sku_raw), '') AS sku,
                        NULLIF(trim(sl.product_id_raw), '') AS product_id
                    FROM app.stg_leftout sl
                    JOIN app.dim_shop ds
                        ON ds.user_id = sl.user_id
                       AND ds.shop_name = NULLIF(trim(sl.shop_raw), '')
                    WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
                      AND NULLIF(trim(sl.barcode_raw), '') IS NOT NULL
                      AND NULLIF(trim(sl.sku_raw), '') IS NOT NULL
                )
                INSERT INTO app.map_shop_sku (user_id, shop_id, sku, barcode, product_id, upload_batch_id)
                SELECT user_id, shop_id, sku, barcode, product_id, upload_batch_id
                FROM src
                ON CONFLICT (user_id, barcode) WHERE barcode IS NOT NULL DO UPDATE
                SET shop_id = EXCLUDED.shop_id,
                    sku = COALESCE(EXCLUDED.sku, app.map_shop_sku.sku),
                    product_id = COALESCE(EXCLUDED.product_id, app.map_shop_sku.product_id),
                    upload_batch_id = EXCLUDED.upload_batch_id,
                    last_seen_at = now()
            """),
            params
        )
        
        # 3) fact_leftout_snapshot
        conn.execute(
            text("""
                DELETE FROM app.fact_leftout_snapshot f
                WHERE f.user_id = CAST(:user_id AS uuid) AND f.upload_batch_id = CAST(:batch_id AS uuid)
            """),
            params
        )
        
        result_leftout = conn.execute(
            text("""
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
                    FROM app.stg_leftout sl
                    JOIN app.dim_shop ds
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
                        NULLIF(trim(product_name_raw), '') AS product_name,
                        NULLIF(trim(product_id_raw), '') AS product_id,
                        NULLIF(trim(sku_raw), '') AS sku,
                        NULLIF(trim(ending_raw), '') AS ending,
                        NULLIF(trim(availability_ind_raw), '') AS availability_indicator,
                        CASE
                            WHEN planned_end_raw IS NULL OR trim(planned_end_raw) IN ('', '—', '-') THEN NULL
                            WHEN planned_end_raw ~ '^\\d{4}-\\d{2}-\\d{2}$' THEN planned_end_raw::date
                            WHEN planned_end_raw ~ '^\\d{2}\\.\\d{2}\\.\\d{4}$' THEN to_date(trim(planned_end_raw), 'DD.MM.YYYY')
                            ELSE NULL
                        END AS planned_end_date,
                        -- Safe cast for coverage_days: only cast if it matches numeric pattern
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
                INSERT INTO app.fact_leftout_snapshot (
                    user_id, upload_batch_id, shop_id,
                    product_name, product_id, sku, barcode,
                    ending, availability_indicator, planned_end_date, coverage_days,
                    recommended_qty, fbs_stock, marketplace_side, in_supply, in_sale,
                    to_customer, from_customer, sdh_stock, photo_stock, defect_stock,
                    potential_per_unit, potential_total
                )
                SELECT
                    user_id, upload_batch_id, shop_id,
                    product_name, product_id, sku, barcode,
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
            """),
            params
        )
        leftout_count = result_leftout.rowcount
        
        # 4) fact_storage_snapshot
        conn.execute(
            text("""
                DELETE FROM app.fact_storage_snapshot f
                WHERE f.user_id = CAST(:user_id AS uuid) AND f.upload_batch_id = CAST(:batch_id AS uuid)
            """),
            params
        )
        
        result_storage = conn.execute(
            text("""
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
                    FROM app.stg_storage ss
                    JOIN app.dim_shop ds
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
                        NULLIF(trim(size_group_raw), '') AS size_group,
                        CAST(replace(NULLIF(regexp_replace(trim(turnover_days_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,4)) AS turnover_days,
                        NULLIF(trim(storage_type_raw), '') AS storage_type,
                        CAST(replace(NULLIF(regexp_replace(trim(fee_total_30d_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS fee_total_30d
                    FROM src
                )
                INSERT INTO app.fact_storage_snapshot (
                    user_id, upload_batch_id, shop_id,
                    product_name, product_id, sku, barcode, size_group,
                    turnover_days, storage_type, fee_total_30d
                )
                SELECT
                    user_id, upload_batch_id, shop_id,
                    product_name, product_id, sku, barcode, size_group,
                    turnover_days, storage_type, fee_total_30d
                FROM casted
                ON CONFLICT (user_id, upload_batch_id, shop_id, sku) DO UPDATE
                SET
                    product_name = EXCLUDED.product_name,
                    product_id = EXCLUDED.product_id,
                    barcode = EXCLUDED.barcode,
                    size_group = EXCLUDED.size_group,
                    turnover_days = EXCLUDED.turnover_days,
                    storage_type = EXCLUDED.storage_type,
                    fee_total_30d = EXCLUDED.fee_total_30d
            """),
            params
        )
        storage_count = result_storage.rowcount
        
        # 5) fact_expenses
        conn.execute(
            text("""
                DELETE FROM app.fact_expenses f
                WHERE f.user_id = CAST(:user_id AS uuid) AND f.upload_batch_id = CAST(:batch_id AS uuid)
            """),
            params
        )
        
        result_expenses = conn.execute(
            text("""
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
                    FROM app.stg_expenses se
                    WHERE se.user_id = CAST(:user_id AS uuid) AND se.upload_batch_id = CAST(:batch_id AS uuid)
                      AND NULLIF(trim(se.operation_id_raw), '') IS NOT NULL
                ),
                casted AS (
                    SELECT
                        user_id, upload_batch_id, source, service, status, operation_id,
                        CASE
                            WHEN written_off_raw ~ '^\\d{4}-\\d{2}-\\d{2}' THEN written_off_raw::timestamptz
                            WHEN written_off_raw ~ '^\\d{2}\\.\\d{2}\\.\\d{4}' THEN to_timestamp(written_off_raw, 'DD.MM.YYYY')::timestamptz
                            ELSE NULL
                        END AS date_written_off,
                        NULLIF(replace(replace(cost_raw, ' ', ''), ',', '.'), '')::numeric AS cost_sum,
                        COALESCE(NULLIF(replace(replace(qty_raw, ' ', ''), ',', '.'), '')::numeric::int, 0) AS qty,
                        NULLIF(replace(replace(amount_raw, ' ', ''), ',', '.'), '')::numeric AS amount_sum,
                        operation_type
                    FROM src
                )
                INSERT INTO app.fact_expenses (
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
            """),
            params
        )
        expenses_count = result_expenses.rowcount
        
        # 6) fact_sales
        conn.execute(
            text("""
                DELETE FROM app.fact_sales f
                WHERE f.user_id = CAST(:user_id AS uuid) AND f.upload_batch_id = CAST(:batch_id AS uuid)
            """),
            params
        )
        
        result_sales = conn.execute(
            text("""
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
                    FROM app.stg_sales ss
                    WHERE ss.user_id = CAST(:user_id AS uuid) AND ss.upload_batch_id = CAST(:batch_id AS uuid)
                      AND NULLIF(trim(ss.order_no_raw), '') IS NOT NULL
                      AND NULLIF(trim(ss.barcode_raw), '') IS NOT NULL
                      AND NULLIF(trim(ss.created_at_raw), '') IS NOT NULL
                ),
                casted AS (
                    SELECT
                        s.user_id,
                        s.upload_batch_id,
                        m.shop_id,
                        s.status,
                        CASE
                            WHEN s.created_at_raw ~ '^\\d{4}-\\d{2}-\\d{2}' THEN s.created_at_raw::timestamptz
                            WHEN s.created_at_raw ~ '^\\d{2}\\.\\d{2}\\.\\d{4}' THEN to_timestamp(s.created_at_raw, 'DD.MM.YYYY')::timestamptz
                            ELSE NULL
                        END AS date_created,
                        CASE
                            WHEN s.received_at_raw ~ '^\\d{4}-\\d{2}-\\d{2}' THEN s.received_at_raw::timestamptz
                            WHEN s.received_at_raw ~ '^\\d{2}\\.\\d{2}\\.\\d{4}' THEN to_timestamp(s.received_at_raw, 'DD.MM.YYYY')::timestamptz
                            ELSE NULL
                        END AS date_received,
                        s.order_no,
                        s.sku,
                        s.barcode,
                        s.product_name,
                        s.category,
                        COALESCE(NULLIF(replace(replace(s.qty_raw, ' ', ''), ',', '.'), '')::numeric::int, 0) AS qty,
                        COALESCE(NULLIF(replace(replace(s.returns_raw, ' ', ''), ',', '.'), '')::numeric::int, 0) AS returns_qty,
                        COALESCE(NULLIF(replace(replace(s.revenue_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS revenue_sum,
                        COALESCE(NULLIF(replace(replace(s.revenue_net_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS revenue_net_sum,
                        COALESCE(NULLIF(replace(replace(s.commission_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS commission_sum,
                        COALESCE(NULLIF(replace(replace(s.logistics_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS logistics_sum,
                        COALESCE(NULLIF(replace(replace(s.price_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS price_sum,
                        COALESCE(NULLIF(replace(replace(s.promo_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS promo_sum,
                        COALESCE(NULLIF(replace(replace(s.cogs_raw, ' ', ''), ',', '.'), '')::numeric, 0) AS cogs_sum
                    FROM src s
                    JOIN app.map_shop_sku m
                        ON m.user_id = s.user_id
                       AND m.barcode = s.barcode
                )
                INSERT INTO app.fact_sales (
                    user_id, upload_batch_id, shop_id,
                    status, date_created, date_received, order_no,
                    sku, barcode, product_name, category,
                    qty, returns_qty,
                    revenue_sum, revenue_net_sum, commission_sum, logistics_sum, price_sum, promo_sum, cogs_sum
                )
                SELECT
                    user_id, upload_batch_id, shop_id,
                    status, date_created, date_received, order_no,
                    sku, barcode, product_name, category,
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
            """),
            params
        )
        sales_count = result_sales.rowcount
        
        return {
            "fact_sales_count": sales_count,
            "fact_expenses_count": expenses_count,
            "fact_leftout_count": leftout_count,
            "fact_storage_count": storage_count,
        }

def mark_batch(engine, user_id: str, batch_id: str, ok: bool, err: str | None = None):
    with engine.begin() as conn:
        if ok:
            conn.execute(text("UPDATE app.upload_batch SET is_current=false WHERE user_id=:u"), {"u": user_id})
            conn.execute(
                text("""
                    UPDATE app.upload_batch
                    SET status='success', is_current=true, error_message=NULL
                    WHERE upload_batch_id=:b
                """),
                {"b": batch_id},
            )
        else:
            conn.execute(
                text("""
                    UPDATE app.upload_batch
                    SET status='failed', error_message=:e
                    WHERE upload_batch_id=:b
                """),
                {"b": batch_id, "e": (err or "failed")[:2000]},
            )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--sales", required=True)
    ap.add_argument("--expenses", required=True)
    ap.add_argument("--leftout", required=True)
    ap.add_argument("--storage", required=True)
    args = ap.parse_args()

    engine = make_engine()

    sales_path = Path(args.sales).expanduser().resolve()
    exp_path = Path(args.expenses).expanduser().resolve()
    left_path = Path(args.leftout).expanduser().resolve()
    stor_path = Path(args.storage).expanduser().resolve()

    for p in [sales_path, exp_path, left_path, stor_path]:
        if not p.exists():
            raise FileNotFoundError(f"Файл не найден: {p}")

    user_id = get_or_create_user(engine, args.email)
    batch_id = create_batch(engine, user_id)

    try:
        register_file(engine, batch_id, "leftout", left_path)
        register_file(engine, batch_id, "storage", stor_path)
        register_file(engine, batch_id, "sales", sales_path)
        register_file(engine, batch_id, "expenses", exp_path)

        df_left = read_excel_as_str(left_path, SHEETS["leftout"], file_type="leftout")
        print("LEFTOUT columns:", df_left.columns.tolist())
        print("LEFTOUT sample rows:", df_left.head(2).to_dict("records"))
        validate_required(df_left, "leftout")
        to_staging(df_left, LEFTOUT_MAP, user_id, batch_id, "stg_leftout", engine, file_type="leftout")
        mark_file_parsed(engine, batch_id, "leftout")

        df_stor = read_excel_as_str(stor_path, SHEETS["storage"], file_type="storage")
        print("STORAGE columns:", df_stor.columns.tolist())
        print("STORAGE sample rows:", df_stor.head(2).to_dict("records"))
        validate_required(df_stor, "storage")
        to_staging(df_stor, STORAGE_MAP, user_id, batch_id, "stg_storage", engine, file_type="storage")
        mark_file_parsed(engine, batch_id, "storage")

        df_sales = read_excel_as_str(sales_path, SHEETS["sales"])
        validate_required(df_sales, "sales")
        to_staging(df_sales, SALES_MAP, user_id, batch_id, "stg_sales", engine)
        mark_file_parsed(engine, batch_id, "sales")

        df_exp = read_excel_as_str(exp_path, SHEETS["expenses"])
        validate_required(df_exp, "expenses")
        to_staging(df_exp, EXP_MAP, user_id, batch_id, "stg_expenses", engine)
        mark_file_parsed(engine, batch_id, "expenses")

        # Populate fact tables from staging
        print("Populating fact tables...")
        fact_counts = populate_facts(engine, user_id, batch_id)
        
        sales_count = fact_counts["fact_sales_count"]
        expenses_count = fact_counts["fact_expenses_count"]
        leftout_count = fact_counts["fact_leftout_count"]
        storage_count = fact_counts["fact_storage_count"]
        
        print(f"Fact tables populated: sales={sales_count}, expenses={expenses_count}, leftout={leftout_count}, storage={storage_count}")
        
        # Check if any fact table is empty
        if sales_count == 0 and expenses_count == 0 and leftout_count == 0 and storage_count == 0:
            error_msg = f"facts not populated: sales={sales_count}, expenses={expenses_count}, leftout={leftout_count}, storage={storage_count}"
            mark_batch(engine, user_id, batch_id, ok=False, err=error_msg)
            raise RuntimeError(error_msg)
        
        # Update error_message with counts (if no error)
        counts_msg = f"facts: sales={sales_count}, expenses={expenses_count}, leftout={leftout_count}, storage={storage_count}"
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE app.upload_batch
                    SET error_message=:msg
                    WHERE upload_batch_id=:b
                """),
                {"b": batch_id, "msg": counts_msg[:2000]},
            )
        
        mark_batch(engine, user_id, batch_id, ok=True)
        print(f"OK ✅ user_id={user_id} upload_batch_id={batch_id}")

    except Exception as e:
        mark_batch(engine, user_id, batch_id, ok=False, err=str(e))
        print(f"FAILED ❌ upload_batch_id={batch_id}\n{e}")
        raise

if __name__ == "__main__":
    main()
