from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging
import io
import json
from app.db import get_db, qname
from app.deps import require_user
from app.settings import get_settings
from app.utils.barcode import barcode_norm_sql
from app.utils.column_mappings import (
    map_headers_to_canonical,
    DuplicateCanonicalError,
    MissingRequiredColumnsError,
)
from app.utils.value_mappings import apply_value_mappings

logger = logging.getLogger(__name__)
router = APIRouter()


def table_exists(db: Session, full_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        db: Database session
        full_name: Full table name with schema, e.g. 'app.map_shop_barcode'
    
    Returns:
        True if table exists, False otherwise
    """
    try:
        result = db.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": full_name})
        return result.scalar() is True
    except Exception as e:
        logger.warning(f"Error checking table existence for {full_name}: {e}")
        return False


def ensure_dev_user_exists(db: Session, user_id: UUID) -> None:
    """
    In dev mode, if user_id is the default dev user and not in app.users, insert them.
    Fixes FK violation when using DEFAULT_DEV_USER_ID without having signed up.
    Does not commit — caller's transaction is used.
    """
    settings = get_settings()
    if settings.APP_ENV.lower() not in ("dev", "development"):
        return
    if str(user_id) != settings.DEFAULT_DEV_USER_ID:
        return
    try:
        db.execute(
            text(f"""
                INSERT INTO {qname("users")} (id, email, full_name, is_active, created_at, updated_at)
                VALUES (CAST(:uid AS uuid), 'dev@local', 'Dev User', true, now(), now())
                ON CONFLICT (id) DO NOTHING
            """),
            {"uid": str(user_id)},
        )
    except Exception as e:
        logger.warning("ensure_dev_user_exists: %s", e)


# Магазины, исключаемые из лимита (как в shops.py)
UNDEFINED_SHOP_NAMES = {
    "не определено", "неопределено", "undefined", "null",
    "(не определено)", "не определен",
}


def get_user_max_shops(db: Session, user_id: UUID) -> Optional[int]:
    """
    Возвращает лимит магазинов по тарифу: Trial 10 -> 1, Month 5 -> 5, Month 10 -> 10.
    Определение только по users.plan (без спец-аккаунтов по email).
    Для тарифа Gold и админов лимит НЕ применяется (безлимит по магазинам).
    """
    try:
        row = db.execute(
            text(
                f"SELECT email, COALESCE(plan, '') FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"
            ),
            {"uid": str(user_id)},
        ).fetchone()
        if not row:
            return None
        email = (row[0] or "").strip().lower()
        plan = (row[1] or "").strip().lower()

        # Админы (ADMIN_USER_IDS по email или UUID) — безлимит по магазинам
        settings = get_settings()
        raw_admin_ids = (settings.ADMIN_USER_IDS or "").strip()
        admin_ids = {s.strip().lower() for s in raw_admin_ids.split(",") if s.strip()}
        if admin_ids:
            if str(user_id).lower() in admin_ids or (email and email in admin_ids):
                return None

        # Gold — безлимитное количество магазинов (лимит не применяется)
        if plan in ("gold", "gold_plan"):
            return None

        # Month 5 — до 5 магазинов
        if plan in ("month_5", "month 5", "month5"):
            return 5

        # Month 10 — до 10 магазинов
        if plan in ("month_10", "month 10", "month10"):
            return 10

        # Trial 10 и любые другие / пустые значения — 1 магазин по умолчанию
        if plan in ("trial", "", None) or not plan:
            return 1

        # Неподдержанные значения плана — тоже 1 магазин (fail-safe)
        return 1
    except Exception as e:
        logger.warning("get_user_max_shops: %s", e)
        return None


def get_saved_shop_names(db: Session, user_id: UUID) -> list:
    """
    Список названий магазинов, сохранённых у пользователя (из dim_shop), без «не определено».
    Отсортирован по shop_name для стабильного порядка (первые N = допуск по тарифу).
    """
    try:
        excluded_sql = ", ".join(repr(s) for s in UNDEFINED_SHOP_NAMES)
        result = db.execute(
            text(f"""
                SELECT shop_name FROM {qname('dim_shop')}
                WHERE user_id = CAST(:user_id AS uuid)
                  AND shop_name IS NOT NULL
                  AND TRIM(shop_name) <> ''
                  AND lower(TRIM(shop_name)) NOT IN ({excluded_sql})
                ORDER BY shop_name
            """),
            {"user_id": str(user_id)},
        )
        return [row[0].strip() for row in result.fetchall() if row and row[0]]
    except Exception as e:
        logger.warning("get_saved_shop_names: %s", e)
        return []


def _file_shop_names_ordered(df: pd.DataFrame, shop_column: str = "Магазин") -> list:
    """Уникальные названия магазинов из файла в порядке первого появления."""
    if shop_column not in df.columns:
        return []
    series = df[shop_column].fillna("").astype(str).str.strip()
    seen: set = set()
    result = []
    for v in series:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def compute_allowed_shops(
    saved_shops: list,
    file_shop_names: list,
    max_shops: Optional[int],
) -> tuple[list, bool]:
    """
    Допуск по тарифу: все ранее сохранённые магазины + новые из файла до лимита.
    Пример: было 2 сохранённых, тариф 5, в файле 7 магазинов → допуск = 2 + 3 новых = 5.
    Возвращает (allowed_shops, store_limit_exceeded).
    """
    if max_shops is None:
        allowed = list(dict.fromkeys(saved_shops + file_shop_names))
        return allowed, False
    allowed_set = set(saved_shops)
    allowed_shops = list(saved_shops)
    for shop in file_shop_names:
        if shop not in allowed_set and len(allowed_shops) < max_shops:
            allowed_shops.append(shop)
            allowed_set.add(shop)
    store_limit_exceeded = len(file_shop_names) > max_shops
    return allowed_shops, store_limit_exceeded


def filter_df_by_allowed_shops(
    df: pd.DataFrame,
    allowed_shop_names: list,
    shop_column: str = "Магазин",
) -> pd.DataFrame:
    """Оставляет в df только строки, у которых магазин входит в allowed_shop_names."""
    if not allowed_shop_names or shop_column not in df.columns:
        return df
    allowed_set = {str(s).strip() for s in allowed_shop_names}
    series = df[shop_column].fillna("").astype(str).str.strip()
    return df[series.isin(allowed_set)].copy()


# Маппинги колонок (из import/import_batch.py)
SHEETS = {
    "sales": "Отчет по продажам",
    "expenses": "Отчет по услугам",
    "inventory": "Остатки (новый)",  # leftout -> inventory
    "storage": "Отчет по хранению",
    "leftout_old": "Остатки (старый)",
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

# Старый формат остатков (left-out-report_old): без магазина, привязка только по barcode_norm к fact_storage_snapshot
# Колонки stg_leftout_old: barcode_raw, sku_raw, product_id_raw, product_name_raw, in_sale_raw, cost_raw, price_raw
LEFTOUT_OLD_MAP = {
    "Штрихкод": "barcode_raw",
    "SKU": "sku_raw",
    "ID товара": "product_id_raw",
    "Наименование": "product_name_raw",
    "В продаже": "in_sale_raw",
    "Себест. (сумы)": "cost_raw",
    "Стоимость продажи (сумы)": "price_raw",
}

REQUIRED = {
    "sales": ["Дата создания", "№ заказа", "Штрихкод"],
    "expenses": ["ID операции", "Дата списания"],
    "inventory": ["Магазин", "Штрихкод"],
    "leftout": ["Магазин", "Штрихкод"],  # Same as inventory
    "leftout_old": ["Штрихкод", "В продаже", "Себест. (сумы)", "Стоимость продажи (сумы)"],
    "storage": ["Магазин", "Штрихкод"],
}

REPORT_TYPE_TO_FILE_TYPE = {
    "sales": "sales",
    "expenses": "expenses",
    "inventory": "leftout",  # inventory -> leftout для внутренней логики
    "inventory_old": "leftout_old",
    "storage": "storage",
}


def norm(s):
    """Normalize column name: remove newlines, non-breaking spaces, normalize whitespace."""
    return " ".join(str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ").strip().split())


def _norm_col_leftout_old(s) -> str:
    """Normalize column name for left-out-report_old validation: trim, collapse spaces, lower, normalize apostrophes."""
    s = str(s).replace("\n", " ").replace("\r", " ").replace("\u00a0", " ").replace("\u02bb", "'").replace("\u2019", "'")
    return " ".join(s.strip().lower().split())


# Required column names for left-out-report_old (after _norm_col_leftout_old): Штрихкод, В продаже, Себест., Стоимость продажи
LEFTOUT_OLD_REQUIRED_NORMALIZED = {"штрихкод", "в продаже", "себест. (сумы)", "стоимость продажи (сумы)"}


def validate_leftout_old_xlsx(file_bytes: bytes) -> None:
    """
    Strict validation: accept only files that look like left-out-report_old.
    Accepts both RU and UZ headers (UZ mapped to canonical via column_mappings).
    Raises HTTPException(400) if the file is not valid.
    Call this BEFORE any DB operations (before delete_old_data/create_batch).
    """
    from app.utils.column_mappings import UZ_TO_RU_LEFTOUT_OLD

    buf = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(buf, engine="openpyxl")
    sheet_names = xl.sheet_names
    required_lower = LEFTOUT_OLD_REQUIRED_NORMALIZED  # {"штрихкод", "в продаже", ...}

    for sheet_name in sheet_names:
        for header_row in range(30):
            try:
                df = pd.read_excel(
                    xl,
                    sheet_name=sheet_name,
                    header=header_row,
                    nrows=0,
                    engine="openpyxl",
                )
            except Exception:
                continue
            cols = [c for c in df.columns if c is not None and not str(c).startswith("Unnamed")]
            if not cols:
                continue
            normalized = [_norm_col_leftout_old(c) for c in cols]
            norm_set = set(normalized)
            # RU: required headers present as-is
            if required_lower <= norm_set:
                return  # valid
            # UZ: map normalized headers to canonical (RU) and check coverage
            mapped_canonical_lower = set()
            for h in norm_set:
                if h in required_lower:
                    mapped_canonical_lower.add(h)
                elif h in UZ_TO_RU_LEFTOUT_OLD:
                    mapped_canonical_lower.add(UZ_TO_RU_LEFTOUT_OLD[h].lower())
            if required_lower <= mapped_canonical_lower:
                return  # valid (UZ file)
            # Quick check: need at least штрихкод and в продаже (RU or UZ)
            if "штрихкод" not in norm_set and "shtrixkod" not in norm_set and not any(
                UZ_TO_RU_LEFTOUT_OLD.get(h, "").lower() == "штрихкод" for h in norm_set
            ):
                continue
            if "в продаже" not in norm_set and "sotuvda" not in norm_set and not any(
                UZ_TO_RU_LEFTOUT_OLD.get(h, "").lower() == "в продаже" for h in norm_set
            ):
                continue
            missing = required_lower - mapped_canonical_lower
            if missing:
                logger.warning(
                    "left-out-report_old validation: missing %s, found %s, mapped %s",
                    sorted(missing), sorted(norm_set), sorted(mapped_canonical_lower),
                )
                raise HTTPException(status_code=400, detail="Неверный формат left-out-report_old")
            return  # valid

    raise HTTPException(status_code=400, detail="Неверный формат left-out-report_old")


def read_excel_as_str(file_content: bytes, sheet: str, file_type: str = None) -> pd.DataFrame:
    """Read Excel with header=1 and proper converters for barcode/sku.
    For leftout_old: sheet_name=0 (first sheet), header=1, all columns as string; column names trim + normalize spaces.
    Otherwise if sheet not found raise ValueError.
    """
    buf = io.BytesIO(file_content)
    xl = pd.ExcelFile(buf, engine="openpyxl")
    if file_type == "leftout_old" and xl.sheet_names:
        sheet_used = xl.sheet_names[0]  # sheet_name=0
    else:
        sheet_used = sheet
        if sheet not in xl.sheet_names:
            # UZ (or other) files may have different sheet names; use first sheet as fallback
            if xl.sheet_names:
                sheet_used = xl.sheet_names[0]
                logger.info("Sheet '%s' not found, using first sheet: %s", sheet, sheet_used)
            else:
                raise ValueError(
                    f"Лист '{sheet}' не найден в файле. Доступные листы: {xl.sheet_names}"
                )
    converters = {}
    if file_type in ("leftout", "storage", "leftout_old"):
        converters = {
            "Штрихкод": lambda x: str(x) if pd.notna(x) else "",
            "SKU": lambda x: str(x) if pd.notna(x) else "",
        }
    # leftout_old: header=1, all columns as string
    dtype_arg = str if file_type == "leftout_old" else ({"Штрихкод": "string", "SKU": "string"} if file_type in ("leftout", "storage") else None)
    df = pd.read_excel(
        xl,
        sheet_name=sheet_used,
        header=1,
        dtype=dtype_arg,
        converters=converters if converters else None,
        engine="openpyxl"
    )
    df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("Unnamed")]]
    # Normalize column names (trim + collapse spaces)
    df.columns = [norm(c) for c in df.columns]
    # Map UZ (or other) headers to canonical RU so existing pipeline is unchanged
    required_canonical = REQUIRED.get(file_type, [])
    if required_canonical:
        try:
            rename_dict, _ = map_headers_to_canonical(file_type, list(df.columns), required_canonical)
            df = df.rename(columns=rename_dict)
        except (DuplicateCanonicalError, MissingRequiredColumnsError) as e:
            raise ValueError(str(e))
    # Canonicalize known variants for storage/leftout: "магазин" / " Магазин " -> "Магазин" (not for leftout_old)
    if file_type in ("leftout", "storage"):
        cols = list(df.columns)
        for i, c in enumerate(cols):
            if c and str(c).strip().lower() == "магазин":
                cols[i] = "Магазин"
                break
        df.columns = cols
    # Ensure barcode/SKU string after possible UZ rename
    if file_type in ("leftout", "storage", "leftout_old"):
        for col in ("Штрихкод", "SKU"):
            if col in df.columns:
                df[col] = df[col].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)
    df = df.dropna(how="all")
    
    # Filter rows with empty barcode for leftout/storage/leftout_old
    if file_type in ("leftout", "storage", "leftout_old") and "Штрихкод" in df.columns:
        df = df[df["Штрихкод"].notna() & (df["Штрихкод"].astype(str).str.strip() != "")]
    
    # Нормализация значений UZ -> RU для метрик (статусы, источник, услуга, тип операции)
    df = apply_value_mappings(df, file_type)
    
    # Универсальная нормализация дат (разное отображение Excel): серийный номер 1900/1904, DD.MM.YYYY, DD.MM.YYYY HH:MM,
    # YYYY-MM-DD, запятая в числе. Результат — YYYY-MM-DD; иначе строки отбрасываются в populate_facts (date_created IS NULL).
    def normalize_date_cell(x):
        if pd.isna(x) or x == "" or (isinstance(x, str) and not x.strip()):
            return ""
        s = str(x).strip()
        if isinstance(x, pd.Timestamp):
            try:
                return x.strftime("%Y-%m-%d")
            except Exception:
                return s
        # Число (int/float или строка типа "45321" / "45321.5" / "45321,5" — не "15.01.2026")
        try:
            if isinstance(x, (int, float)):
                n = int(x)
            else:
                s_num = s.replace(",", ".").replace(" ", "")
                if s_num.count(".") > 1:
                    raise ValueError("looks like DD.MM.YYYY")
                if not (s_num.replace(".", "").replace("-", "").isdigit() and len(s_num.replace(".", "").replace("-", "")) >= 4):
                    raise ValueError("not a serial number")
                n = int(float(s_num))
            if n <= 0:
                return ""
            d = datetime(1899, 12, 30) + timedelta(days=n)
            if d.year < 2024:
                d = datetime(1904, 1, 1) + timedelta(days=n)
            return d.strftime("%Y-%m-%d")
        except (ValueError, OverflowError, TypeError):
            pass
        # Строка-дата: DD.MM.YYYY, DD.MM.YYYY HH:MM, YYYY-MM-DD, с другим отображением Excel — в YYYY-MM-DD
        try:
            parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
            if pd.notna(parsed):
                return parsed.strftime("%Y-%m-%d")
        except Exception:
            pass
        return s
    if file_type == "sales":
        for col in ("Дата создания", "Дата получения"):
            if col in df.columns:
                df = df.copy()
                df[col] = df[col].apply(normalize_date_cell)
    elif file_type == "expenses":
        if "Дата списания" in df.columns:
            df = df.copy()
            df["Дата списания"] = df["Дата списания"].apply(normalize_date_cell)
    
    return df


def validate_required(df: pd.DataFrame, file_type: str):
    """Validate that required columns are present."""
    required_cols = REQUIRED.get(file_type, [])
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"[{file_type}] Не найдены обязательные колонки: {missing}. Найдено: {list(df.columns)}")


def _row_to_json_serializable(obj):
    """Convert a value to JSON-serializable form (for stg_leftout_old.data)."""
    if pd.isna(obj):
        return None
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat() if hasattr(obj, "isoformat") else str(obj)
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return int(obj) if obj == int(obj) else float(obj)
    return obj


def to_staging(df: pd.DataFrame, mapping: dict, user_id: str, batch_id: str, table: str, db: Session, file_type: str = None):
    """Load data to staging table with proper type handling."""
    # Safe: skip write to leftout_old staging if table does not exist (migration not applied)
    if table == "stg_leftout_old":
        if not table_exists(db, qname("stg_leftout_old")):
            logger.warning(
                "to_staging(leftout_old): table %s does not exist (to_regclass returned null), skipping insert",
                qname("stg_leftout_old"),
            )
            return
        # stg_leftout_old: data jsonb (full row as dict) + barcode_raw, in_sale_raw, cost_raw, price_raw
        required_cols = ["Штрихкод", "В продаже", "Себест. (сумы)", "Стоимость продажи (сумы)"]
        for c in required_cols:
            if c not in df.columns:
                raise ValueError(f"[leftout_old] Обязательная колонка отсутствует: {c}. Найдено: {list(df.columns)}")
        rows_data = []
        for _, row in df.iterrows():
            row_dict = {k: _row_to_json_serializable(row[k]) for k in df.columns}
            data_json = json.dumps(row_dict, ensure_ascii=False)
            barcode_raw = str(row["Штрихкод"]).strip() if pd.notna(row["Штрихкод"]) else None
            in_sale_raw = str(row["В продаже"]).strip() if pd.notna(row["В продаже"]) else None
            cost_raw = str(row["Себест. (сумы)"]).strip() if pd.notna(row["Себест. (сумы)"]) else None
            price_raw = str(row["Стоимость продажи (сумы)"]).strip() if pd.notna(row["Стоимость продажи (сумы)"]) else None
            rows_data.append((user_id, batch_id, data_json, barcode_raw, in_sale_raw, cost_raw, price_raw))
        if rows_data:
            stg_table = qname("stg_leftout_old")
            insert_sql = text(f"""
                INSERT INTO {stg_table}
                (user_id, upload_batch_id, row_num, data, barcode_raw, in_sale_raw, cost_raw, price_raw)
                VALUES
                (CAST(:user_id AS uuid), CAST(:upload_batch_id AS uuid), :row_num,
                 CAST(:data AS jsonb), :barcode_raw, :in_sale_raw, :cost_raw, :price_raw)
            """)
            for i, r in enumerate(rows_data):
                # header=1: таблица со 2-й строки, первая строка данных = row_num 2
                row_num = i + 2
                params = {
                    "user_id": r[0],
                    "upload_batch_id": r[1],
                    "row_num": row_num,
                    "data": r[2],
                    "barcode_raw": r[3],
                    "in_sale_raw": r[4],
                    "cost_raw": r[5],
                    "price_raw": r[6],
                }
                if i < 3:
                    logger.info(
                        "stg_leftout_old insert row %s: row_num=%s, barcode_raw=%s, in_sale_raw=%s",
                        i + 1, params["row_num"], params["barcode_raw"], params["in_sale_raw"],
                    )
                db.execute(insert_sql, params)
        return

    out = pd.DataFrame()
    # stg_leftout_old (user schema) has no row_num
    if table != "stg_leftout_old":
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
        
        # Диагностика после маппинга: проверяем shop_raw vs sku_raw
        if "shop_raw" in out.columns and "sku_raw" in out.columns:
            shop_raw_non_null = out["shop_raw"].dropna()
            sku_raw_non_null = out["sku_raw"].dropna()
            shop_unique = shop_raw_non_null.nunique() if len(shop_raw_non_null) > 0 else 0
            sku_unique = sku_raw_non_null.nunique() if len(sku_raw_non_null) > 0 else 0
            logger.info(f"[STORAGE TO_STAGING] After mapping: shop_raw unique={shop_unique}, sku_raw unique={sku_unique}")
            # Проверка: если shop_raw содержит значения из SKU (например, много уникальных значений как в SKU) - это баг
            if shop_unique > 0 and sku_unique > 0:
                shop_sample = shop_raw_non_null.head(5).tolist()
                sku_sample = sku_raw_non_null.head(5).tolist()
                logger.info(f"[STORAGE TO_STAGING] shop_raw sample: {shop_sample}")
                logger.info(f"[STORAGE TO_STAGING] sku_raw sample: {sku_sample}")
                # Если shop_raw содержит слишком много уникальных значений (как SKU) - предупреждение
                if shop_unique > 100 and shop_unique > sku_unique * 0.8:
                    logger.warning(f"[STORAGE TO_STAGING] WARNING: shop_raw has {shop_unique} unique values (similar to sku_raw={sku_unique}). Possible mapping error!")
        
        # Numeric fields
        for col in ["turnover_days_raw", "fee_total_30d_raw"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
    elif file_type == "leftout_old":
        # String fields: strip; no shop — binding only via fact_storage_snapshot by barcode_norm
        for col in ["barcode_raw", "sku_raw", "product_id_raw", "product_name_raw", "in_sale_raw", "cost_raw", "price_raw"]:
            if col in out.columns:
                out[col] = out[col].apply(lambda x: str(x).strip() if pd.notna(x) else None)
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
    # IMPORTANT: manual_expenses (extra expenses) are NOT deleted - they persist across uploads
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
    
    # NOTE: manual_expenses (extra expenses) are NOT deleted here - they persist across uploads
    
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
    elif report_type == "inventory_old":
        # Safe delete: only if tables exist (migration may not be applied yet)
        fact_table = qname("fact_leftout_old_snapshot")
        stg_table = qname("stg_leftout_old")
        if table_exists(db, fact_table):
            db.execute(text(f"DELETE FROM {fact_table} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        else:
            logger.warning(
                "delete_old_data(inventory_old): table %s does not exist (to_regclass returned null), skipping delete",
                fact_table,
            )
        if table_exists(db, stg_table):
            db.execute(text(f"DELETE FROM {stg_table} WHERE user_id = CAST(:user_id AS uuid)"), {"user_id": user_id_str})
        else:
            logger.warning(
                "delete_old_data(inventory_old): table %s does not exist (to_regclass returned null), skipping delete",
                stg_table,
            )
    
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

    # Определяем тариф пользователя (для Trial 10 ограничиваем данные последними 60 днями
    # относительно последней даты в выгрузке по соответствующему типу отчёта).
    try:
        plan_row = db.execute(
            text(f"SELECT COALESCE(plan, 'trial') FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"),
            {"uid": user_id_str},
        ).fetchone()
        plan_val = (plan_row[0] or "trial").strip().lower() if plan_row else "trial"
    except Exception as e:
        logger.warning("populate_facts: failed to read user plan for user_id=%s: %s", user_id_str, e)
        plan_val = "trial"

    is_trial_plan = plan_val in ("trial", "", None) or not plan_val
    params["is_trial_plan"] = is_trial_plan

    # Для Trial 10 считаем "последние 60 дней" от последней даты в выгрузке (а не от now()).
    trial_cutoff_date = None
    if is_trial_plan:
        try:
            if report_type == "sales":
                # Максимальная дата продаж с тем же выражением, что и в CTE casted.date_created
                trial_cutoff_date = db.execute(
                    text(
                        f"""
                        SELECT MAX(
                          CASE
                            WHEN created_at_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'
                              THEN created_at_raw::timestamptz
                            WHEN created_at_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}'
                              THEN to_timestamp(
                                substring(trim(created_at_raw) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'),
                                'DD.MM.YYYY'
                              )::timestamptz
                            WHEN (created_at_raw ~ '^\\d+(\\.\\d*)?$' OR created_at_raw ~ '^\\d+,\\d*$')
                                 AND replace(created_at_raw, ',', '.')::numeric > 0
                              THEN (
                                CASE
                                  WHEN (timestamp '1899-12-30'
                                        + (replace(created_at_raw, ',', '.')::numeric * interval '1 day'))::date < '2024-01-01'::date
                                    THEN (timestamp '1904-01-01'
                                          + (replace(created_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                    ELSE (timestamp '1899-12-30'
                                          + (replace(created_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                END
                              )
                            ELSE NULL
                          END
                        )
                        FROM {qname('stg_sales')}
                        WHERE user_id = CAST(:user_id AS uuid)
                          AND upload_batch_id = CAST(:batch_id AS uuid)
                        """
                    ),
                    params,
                ).scalar()
            elif report_type == "expenses":
                # Максимальная дата списания с тем же выражением, что и в CTE casted.date_written_off
                trial_cutoff_date = db.execute(
                    text(
                        f"""
                        SELECT MAX(
                          CASE
                            WHEN written_off_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}'
                              THEN written_off_raw::timestamptz
                            WHEN written_off_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}'
                              THEN to_timestamp(
                                substring(trim(written_off_raw) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'),
                                'DD.MM.YYYY'
                              )::timestamptz
                            WHEN (written_off_raw ~ '^\\d+(\\.\\d*)?$' OR written_off_raw ~ '^\\d+,\\d*$')
                                 AND replace(written_off_raw, ',', '.')::numeric > 0
                              THEN (
                                CASE
                                  WHEN (timestamp '1899-12-30'
                                        + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::date < '2024-01-01'::date
                                    THEN (timestamp '1904-01-01'
                                          + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                    ELSE (timestamp '1899-12-30'
                                          + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                END
                              )
                            ELSE NULL
                          END
                        )
                        FROM {qname('stg_expenses')}
                        WHERE user_id = CAST(:user_id AS uuid)
                          AND upload_batch_id = CAST(:batch_id AS uuid)
                        """
                    ),
                    params,
                ).scalar()
        except Exception as e:
            logger.warning(
                "populate_facts: failed to compute trial cutoff date for user_id=%s, report_type=%s: %s",
                user_id_str,
                report_type,
                e,
            )

    params["trial_cutoff_date"] = trial_cutoff_date
    
    if report_type == "sales":
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
                        WHEN s.created_at_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(substring(trim(s.created_at_raw) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'), 'DD.MM.YYYY')::timestamptz
                        WHEN (s.created_at_raw ~ '^\\d+(\\.\\d*)?$' OR s.created_at_raw ~ '^\\d+,\\d*$') AND replace(s.created_at_raw, ',', '.')::numeric > 0 THEN (
                            CASE WHEN (timestamp '1899-12-30' + (replace(s.created_at_raw, ',', '.')::numeric * interval '1 day'))::date < '2024-01-01'::date
                                THEN (timestamp '1904-01-01' + (replace(s.created_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                ELSE (timestamp '1899-12-30' + (replace(s.created_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                            END)
                        ELSE NULL
                    END AS date_created,
                    CASE
                        WHEN s.received_at_raw ~ '^\\d{{4}}-\\d{{2}}-\\d{{2}}' THEN s.received_at_raw::timestamptz
                        WHEN s.received_at_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(substring(trim(s.received_at_raw) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'), 'DD.MM.YYYY')::timestamptz
                        WHEN (s.received_at_raw ~ '^\\d+(\\.\\d*)?$' OR s.received_at_raw ~ '^\\d+,\\d*$') AND replace(s.received_at_raw, ',', '.')::numeric > 0 THEN (
                            CASE WHEN (timestamp '1899-12-30' + (replace(s.received_at_raw, ',', '.')::numeric * interval '1 day'))::date < '2024-01-01'::date
                                THEN (timestamp '1904-01-01' + (replace(s.received_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                ELSE (timestamp '1899-12-30' + (replace(s.received_at_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                            END)
                        ELSE NULL
                    END AS date_received,
                    s.order_no,
                    s.sku,
                    s.barcode,
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
                    COALESCE(NULLIF(replace(regexp_replace(trim(s.cogs_raw), '[^0-9,.-]', '', 'g'), ',', '.'), '')::numeric, 0) AS cogs_sum,
                    {barcode_norm_sql('s.barcode')} AS barcode_norm
                FROM src s
                LEFT JOIN {qname('map_shop_sku')} m
                    ON m.user_id = s.user_id
                   AND {barcode_norm_sql('m.barcode')} = {barcode_norm_sql('s.barcode')}
            )
            INSERT INTO {qname('fact_sales')} (
                user_id, upload_batch_id, shop_id,
                status, date_created, date_received, order_no,
                sku, barcode, product_name, category, barcode_norm,
                qty, returns_qty,
                revenue_sum, revenue_net_sum, commission_sum, logistics_sum, price_sum, promo_sum, cogs_sum
            )
            SELECT
                user_id, upload_batch_id, shop_id,
                status, date_created, date_received, order_no,
                sku, barcode, product_name, category, barcode_norm,
                qty, returns_qty,
                revenue_sum, revenue_net_sum, commission_sum, logistics_sum, price_sum, promo_sum, cogs_sum
            FROM casted
            WHERE date_created IS NOT NULL
              AND barcode IS NOT NULL
              AND (
                :is_trial_plan = false
                OR :trial_cutoff_date IS NULL
                OR date_created >= (:trial_cutoff_date - interval '60 days')
              )
            ON CONFLICT (user_id, order_no, barcode, date_created) DO UPDATE
            SET
                upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = EXCLUDED.shop_id,
                status = EXCLUDED.status,
                date_received = EXCLUDED.date_received,
                sku = EXCLUDED.sku,
                product_name = EXCLUDED.product_name,
                category = EXCLUDED.category,
                barcode_norm = EXCLUDED.barcode_norm,
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
        # Use most frequent sku/product_id for each normalized barcode
        db.execute(text(f"""
            INSERT INTO {qname('map_shop_barcode')} (user_id, upload_batch_id, shop_id, barcode_norm, sku, product_id)
            WITH ranked AS (
                SELECT DISTINCT
                    fs.user_id,
                    fs.upload_batch_id,
                    fs.shop_id,
                    {barcode_norm_sql('fs.barcode')} AS barcode_norm,
                    fs.sku,
                    fs.product_name AS product_id,  -- Using product_name as product_id fallback
                    ROW_NUMBER() OVER (
                        PARTITION BY fs.user_id, COALESCE(fs.shop_id, '00000000-0000-0000-0000-000000000000'::uuid), {barcode_norm_sql('fs.barcode')}
                        ORDER BY COUNT(*) DESC, fs.date_created DESC
                    ) AS rn
                FROM {qname('fact_sales')} fs
                WHERE fs.user_id = CAST(:user_id AS uuid) 
                  AND fs.upload_batch_id = CAST(:batch_id AS uuid)
                  AND fs.barcode IS NOT NULL
                  AND {barcode_norm_sql('fs.barcode')} IS NOT NULL
                GROUP BY fs.user_id, fs.upload_batch_id, fs.shop_id, {barcode_norm_sql('fs.barcode')}, fs.sku, fs.product_name, fs.date_created
            )
            SELECT user_id, upload_batch_id, shop_id, barcode_norm, sku, product_id
            FROM ranked
            WHERE rn = 1
            ON CONFLICT (user_id, COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid), barcode_norm) DO UPDATE
            SET upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = COALESCE(EXCLUDED.shop_id, map_shop_barcode.shop_id),
                sku = COALESCE(EXCLUDED.sku, map_shop_barcode.sku),
                product_id = COALESCE(EXCLUDED.product_id, map_shop_barcode.product_id),
                last_seen_at = now(),
                updated_at = now()
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
                   AND {barcode_norm_sql('m.barcode')} = {barcode_norm_sql('s.barcode')}
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
                        WHEN written_off_raw ~ '^\\d{{2}}\\.\\d{{2}}\\.\\d{{4}}' THEN to_timestamp(substring(trim(written_off_raw) from '^[0-9]{{2}}\\.[0-9]{{2}}\\.[0-9]{{4}}'), 'DD.MM.YYYY')::timestamptz
                        WHEN (written_off_raw ~ '^\\d+(\\.\\d*)?$' OR written_off_raw ~ '^\\d+,\\d*$') AND replace(written_off_raw, ',', '.')::numeric > 0 THEN (
                            CASE WHEN (timestamp '1899-12-30' + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::date < '2024-01-01'::date
                                THEN (timestamp '1904-01-01' + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                                ELSE (timestamp '1899-12-30' + (replace(written_off_raw, ',', '.')::numeric * interval '1 day'))::timestamptz
                            END)
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
              AND (
                :is_trial_plan = false
                OR :trial_cutoff_date IS NULL
                OR date_written_off >= (:trial_cutoff_date - interval '60 days')
              )
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
                {barcode_norm_sql('sl.barcode_raw')} AS barcode_norm,
                NULLIF(trim(sl.sku_raw), '') AS sku,
                NULLIF(trim(sl.product_id_raw), '') AS product_id
            FROM {qname('stg_leftout')} sl
            JOIN {qname('dim_shop')} ds ON ds.user_id = sl.user_id AND ds.shop_name = NULLIF(trim(sl.shop_raw), '')
            WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND {barcode_norm_sql('sl.barcode_raw')} IS NOT NULL
            ON CONFLICT (user_id, COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid), barcode_norm) DO UPDATE
            SET upload_batch_id = EXCLUDED.upload_batch_id,
                shop_id = COALESCE(EXCLUDED.shop_id, map_shop_barcode.shop_id),
                sku = COALESCE(EXCLUDED.sku, map_shop_barcode.sku),
                product_id = COALESCE(EXCLUDED.product_id, map_shop_barcode.product_id),
                last_seen_at = now(),
                updated_at = now()
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
                    CAST(replace(NULLIF(regexp_replace(trim(potential_total_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS potential_total,
                    {barcode_norm_sql('barcode_raw')} AS barcode_norm
                FROM src
            ),
            casted_with_norm AS (
                SELECT
                    user_id, upload_batch_id, shop_id,
                    product_name, product_id, sku, barcode, barcode_norm,
                    ending, availability_indicator, planned_end_date, coverage_days,
                    recommended_qty, fbs_stock, marketplace_side, in_supply, in_sale,
                    to_customer, from_customer, sdh_stock, photo_stock, defect_stock,
                    potential_per_unit, potential_total
                FROM casted
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
            FROM casted_with_norm
            WHERE barcode IS NOT NULL
            ON CONFLICT (user_id, upload_batch_id, shop_id, sku) DO UPDATE
            SET
                product_name = EXCLUDED.product_name,
                product_id = EXCLUDED.product_id,
                barcode = EXCLUDED.barcode,
                barcode_norm = EXCLUDED.barcode_norm,
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
                    NULLIF(trim(ss.shop_raw), '') AS shop_raw,
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
                    user_id, upload_batch_id, shop_id, shop_raw,
                    NULLIF(trim(product_name_raw), '') AS product_name,
                    NULLIF(trim(product_id_raw), '') AS product_id,
                    NULLIF(trim(sku_raw), '') AS sku,
                    NULLIF(trim(barcode_raw), '') AS barcode,
                    NULLIF(trim(size_group_raw), '') AS size_group,
                    CAST(replace(NULLIF(regexp_replace(trim(turnover_days_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,4)) AS turnover_days,
                    NULLIF(trim(storage_type_raw), '') AS storage_type,
                    CAST(replace(NULLIF(regexp_replace(trim(fee_total_30d_raw), '[^0-9,.-]', '', 'g'), ''), ',', '.') AS numeric(18,2)) AS fee_total_30d
                FROM src
            ),
            casted_with_norm AS (
                SELECT
                    user_id, upload_batch_id, shop_id, shop_raw,
                    product_name, product_id, sku, barcode,
                    {barcode_norm_sql('barcode')} AS barcode_norm,
                    size_group, turnover_days, storage_type, fee_total_30d
                FROM casted
            )
            INSERT INTO {qname('fact_storage_snapshot')} (
                user_id, upload_batch_id, shop_id, shop_raw,
                product_name, product_id, sku, barcode, barcode_norm, size_group,
                turnover_days, storage_type, fee_total_30d
            )
            SELECT
                user_id, upload_batch_id, shop_id, shop_raw,
                product_name, product_id, sku, barcode, barcode_norm, size_group,
                turnover_days, storage_type, fee_total_30d
            FROM casted_with_norm
            WHERE barcode IS NOT NULL
            ON CONFLICT (user_id, upload_batch_id, shop_id, sku) DO UPDATE
            SET
                shop_raw = EXCLUDED.shop_raw,
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
    
    elif report_type == "inventory_old":
        # Safe: only touch leftout_old tables if they exist (migration may not be applied)
        fact_table = qname("fact_leftout_old_snapshot")
        if not table_exists(db, fact_table):
            logger.warning(
                "populate_facts(inventory_old): table %s does not exist, skipping; run migration to create stg_leftout_old and fact_leftout_old_snapshot",
                fact_table,
            )
            return 0
        # Перед вставкой: DELETE по user_id (как у других файлов)
        db.execute(text(f"DELETE FROM {fact_table} WHERE user_id = CAST(:user_id AS uuid)"), params)
        # Парсинг: barcode_norm = TRIM(regexp_replace(barcode_raw, '\s+', '', 'g')); in_sale_qty int (пусто=0, <0=0); cost_sum/price_sum numeric
        # cost_sum/price_sum: numeric(18,2), пусто→NULL (колонки nullable)
        result = db.execute(text(f"""
            INSERT INTO {fact_table} (
                user_id, upload_batch_id, barcode, barcode_norm, in_sale_qty, cost_sum, price_sum, loaded_at
            )
            SELECT
                sl.user_id,
                sl.upload_batch_id,
                NULLIF(trim(sl.barcode_raw), '') AS barcode,
                NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') AS barcode_norm,
                GREATEST(0, COALESCE(CAST(NULLIF(replace(replace(regexp_replace(trim(COALESCE(sl.in_sale_raw, '')), '\\s+', '', 'g'), ',', ''), '\u2014', ''), '') AS int), 0)) AS in_sale_qty,
                CAST(NULLIF(replace(regexp_replace(trim(COALESCE(sl.cost_raw, '')), '\\s+', '', 'g'), ',', '.'), '') AS numeric(18,2)) AS cost_sum,
                CAST(NULLIF(replace(regexp_replace(trim(COALESCE(sl.price_raw, '')), '\\s+', '', 'g'), ',', '.'), '') AS numeric(18,2)) AS price_sum,
                now() AS loaded_at
            FROM {qname('stg_leftout_old')} sl
            WHERE sl.user_id = CAST(:user_id AS uuid) AND sl.upload_batch_id = CAST(:batch_id AS uuid)
              AND NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') IS NOT NULL
              AND NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') != ''
        """), params)
        count = result.rowcount
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
    - reportType: sales|inventory|expenses|storage|inventory_old
    - fileName: optional file name
    
    Returns:
    - ok: true
    - reportType: report type
    - upload_batch_id: UUID of the batch
    - saved_as: path where file was saved
    - rowsImported: number of rows imported to fact tables
    """
    
    # Validate reportType - accept common variants
    valid_report_types = ["sales", "inventory", "expenses", "storage", "leftout", "inventory_old"]
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
    
    # Strict validation for inventory_old: accept only left-out-report_old format, BEFORE any DB ops
    file_content_early = None
    if reportType == "inventory_old":
        file_content_early = await file.read()
        validate_leftout_old_xlsx(file_content_early)
    
    # Start transaction - all operations in one transaction
    try:
        store_limit_exceeded = False
        ensure_dev_user_exists(db, user_id)
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
        
        if file_content_early is not None:
            file_content = file_content_early
        else:
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
            "inventory_old": LEFTOUT_OLD_MAP,
        }.get(reportType, {})
        
        if not mapping:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"No mapping found for reportType: {reportType}"
            )
        
        # Диагностика для seller-storage: проверяем наличие колонки "Магазин"
        if file_type == "storage":
            logger.info(
                f"[STORAGE IMPORT] reportType={reportType}, file_type={file_type}, sheet_name={sheet_name}, "
                f"columns={list(df.columns)}, rows={len(df)}"
            )
            logger.info(f"[STORAGE IMPORT] df.head(3)=\n{df.head(3).to_string()}")
            if "Магазин" not in df.columns:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=f"Колонка 'Магазин' не найдена в файле seller-storage. Найдены колонки: {list(df.columns)}"
                )
            shop_col = df["Магазин"]
            shop_sample = shop_col.dropna().head(5).tolist()
            shop_unique_count = shop_col.dropna().nunique()
            logger.info(f"[STORAGE IMPORT] Column 'Магазин' found. Sample: {shop_sample}, distinct shops: {shop_unique_count}")
            # Проверяем, что "Магазин" НЕ маппится в sku_raw
            if mapping.get("Магазин") != "shop_raw":
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"ОШИБКА МАППИНГА: Колонка 'Магазин' должна маппиться в 'shop_raw', но маппится в '{mapping.get('Магазин')}'"
                )
            # Проверяем, что "SKU" маппится в sku_raw, а не в shop_raw
            if mapping.get("SKU") == "shop_raw":
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=f"ОШИБКА МАППИНГА: Колонка 'SKU' НЕ должна маппиться в 'shop_raw', должна маппиться в 'sku_raw'"
                )
        
        # Ограничение по тарифу: сохранённые магазины + новые из файла до лимита (например 2 было + 3 из файла = 5)
        store_limit_exceeded = False
        store_limit_max: Optional[int] = None  # для ответа при store_limit_exceeded
        if reportType in ("inventory", "storage") and "Магазин" in df.columns:
            saved_shops = get_saved_shop_names(db, user_id)
            max_shops = get_user_max_shops(db, user_id)
            file_shop_names = _file_shop_names_ordered(df, "Магазин")
            if max_shops is not None:
                allowed_shops, store_limit_exceeded = compute_allowed_shops(
                    saved_shops, file_shop_names, max_shops
                )
                if store_limit_exceeded:
                    store_limit_max = max_shops
                df = filter_df_by_allowed_shops(df, allowed_shops, "Магазин")
                if df.empty and store_limit_exceeded:
                    logger.warning(
                        "Import: no rows left after shop limit (tariff max_shops=%s); file had shops outside allowed list",
                        max_shops,
                    )

        # Step 5: Load to staging
        staging_table = {
            "sales": "stg_sales",
            "expenses": "stg_expenses",
            "inventory": "stg_leftout",
            "storage": "stg_storage",
            "inventory_old": "stg_leftout_old",
        }.get(reportType)
        
        # 0) Диагностика: Остатки (старый формат) — reportType, file_type, лист, stg-таблица
        if reportType == "inventory_old":
            logger.info(
                "[Остатки (старый формат)] reportType=%s, file_type=%s, sheet_name=%s, staging_table=%s",
                reportType, file_type, sheet_name, staging_table,
            )
        
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
        
        # Step 6: Transform to fact tables (для inventory_old — populate stg_leftout_old → fact_leftout_old_snapshot)
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
        # Отметить батч как успешный для метрик админки (успех = загрузка Excel прошла без ошибки)
        try:
            db.execute(
                text(f"UPDATE {qname('upload_batch')} SET status = 'success' WHERE upload_batch_id = CAST(:bid AS uuid)"),
                {"bid": batch_id},
            )
            db.commit()
        except Exception as e:
            logger.debug("upload_batch status update skipped: %s", e)
            db.rollback()

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
        
        # Safe: only COUNT if tables exist (migration may not be applied)
        stg_leftout_old_count = 0
        leftout_old_count = 0
        if table_exists(db, qname("stg_leftout_old")):
            stg_leftout_old_count = db.execute(
                text(f"SELECT COUNT(*) FROM {qname('stg_leftout_old')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
                params_log
            ).scalar() or 0
        if table_exists(db, qname("fact_leftout_old_snapshot")):
            leftout_old_count = db.execute(
                text(f"SELECT COUNT(*) FROM {qname('fact_leftout_old_snapshot')} WHERE user_id = CAST(:user_id AS uuid) AND upload_batch_id = CAST(:batch_id AS uuid)"),
                params_log
            ).scalar() or 0
        else:
            logger.warning(
                "import_xlsx: table %s does not exist (to_regclass returned null), returning count=0 for logging",
                qname("fact_leftout_old_snapshot"),
            )
        # Временный лог после импорта: counts по stg_old и fact_old для batch_id
        if reportType == "inventory_old":
            logger.info(
                "left-out-report_old import: batch_id=%s, stg_leftout_old=%s, fact_leftout_old_snapshot=%s",
                batch_id, stg_leftout_old_count, leftout_old_count,
            )
        logger.info(
            f"Import successful (overwrite mode): user_id={user_id}, upload_batch_id={batch_id}, "
            f"reportType={reportType}, rowsImported={rows_imported}, "
            f"fact_sales={sales_count}, fact_expenses={expenses_count}, "
            f"fact_leftout_snapshot={inventory_count}, fact_storage_snapshot={storage_count}, "
            f"stg_leftout_old={stg_leftout_old_count}, fact_leftout_old_snapshot={leftout_old_count}, saved_as={saved_as}"
        )
        
        store_limit_current: Optional[int] = None
        if store_limit_exceeded and store_limit_max is not None:
            store_limit_current = len(get_saved_shop_names(db, user_id))
        
        out = {
            "ok": True,
            "reportType": reportType,
            "upload_batch_id": batch_id,
            "saved_as": saved_as,
            "rowsImported": rows_imported,
            "store_limit_exceeded": store_limit_exceeded,
        }
        if store_limit_exceeded:
            out["store_limit_max"] = store_limit_max
            out["store_limit_current"] = store_limit_current
        return out
    
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
        ensure_dev_user_exists(db, user_id)
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
        batch_store_limit_exceeded = False
        saved_shops = get_saved_shop_names(db, user_id)
        max_shops = get_user_max_shops(db, user_id)
        
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
                
                # Ограничение по тарифу: сохранённые + новые из файла до лимита
                if report_type in ("inventory", "storage") and "Магазин" in df.columns and max_shops is not None:
                    file_shop_names = _file_shop_names_ordered(df, "Магазин")
                    allowed_shops, exceeded = compute_allowed_shops(
                        saved_shops, file_shop_names, max_shops
                    )
                    df = filter_df_by_allowed_shops(df, allowed_shops, "Магазин")
                    batch_store_limit_exceeded = batch_store_limit_exceeded or exceeded
                
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
                
                # После inventory/storage обновляем список сохранённых магазинов для следующего файла (лимит тарифа)
                if report_type in ("inventory", "storage"):
                    saved_shops = get_saved_shop_names(db, user_id)
                
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
        # Отметить батч как успешный для метрик админки
        try:
            db.execute(
                text(f"UPDATE {qname('upload_batch')} SET status = 'success' WHERE upload_batch_id = CAST(:bid AS uuid)"),
                {"bid": batch_id},
            )
            db.commit()
        except Exception as e:
            logger.debug("upload_batch status update skipped: %s", e)
            db.rollback()

        # Step 6: Log success with row counts per table
        logger.info(
            f"Batch import successful: user_id={user_id}, upload_batch_id={batch_id}, "
            f"imported={imported_counts}, saved_as={saved_paths}"
        )
        
        out_batch = {
            "ok": True,
            "upload_batch_id": batch_id,
            "imported": imported_counts,
            "saved_as": saved_paths,
            "store_limit_exceeded": batch_store_limit_exceeded,
        }
        if batch_store_limit_exceeded and max_shops is not None:
            out_batch["store_limit_max"] = max_shops
            out_batch["store_limit_current"] = len(get_saved_shop_names(db, user_id))
        return out_batch
    
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
