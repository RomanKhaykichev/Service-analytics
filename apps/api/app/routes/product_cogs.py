"""Product unit COGS: Uzum LK source + Profiboard manual overrides."""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db, qname
from app.deps import require_user
from app.routes.imports import table_exists
from app.schemas.product_cogs import (
    ProductCogsHistoryEntry,
    ProductCogsHistoryResponse,
    ProductCogsItem,
    ProductCogsListResponse,
    ProductCogsUpsertRequest,
)
from app.utils.barcode import barcode_norm_sql
from app.utils.product_image import resolve_product_image_url
from app.utils.metrics import get_status_conditions
from app.utils.shop_filter import normalize_shop, storage_barcode_filter_sql
from app.utils.trial_shop import assert_trial_shop_filter_allowed

logger = logging.getLogger(__name__)
router = APIRouter()

_status = get_status_conditions()
_STATUS_REVENUE_SQL = f"(({_status['completed']}) OR ({_status['processing']}))"


def _str_val(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _parse_num(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(" ", "").replace(",", ".")
    if not s or s in ("-", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_barcode_norm(raw: str) -> str:
    bn = re.sub(r"\s+", "", (raw or "").strip())
    if bn.endswith(".0"):
        bn = bn[:-2]
    return bn


def _extract_product_image_url_from_data(data: dict) -> Optional[str]:
    raw = data.get("Ссылка на товар") or data.get("Mahsulot havolasi") or data.get("Tovar havolasi")
    return resolve_product_image_url(raw)


def _ensure_manual_product_cogs_schema(db: Session) -> None:
    """Таблица ручной себестоимости + колонка effective_from (дата начиная с)."""
    tbl = qname("manual_product_cogs")
    if not table_exists(db, tbl):
        db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL,
                    barcode_norm text NOT NULL,
                    barcode text,
                    sku text,
                    product_name text,
                    shop text,
                    cogs_sum numeric(18,2) NOT NULL,
                    effective_from date,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now(),
                    UNIQUE (user_id, barcode_norm)
                )
                """
            )
        )
        db.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_manual_product_cogs_user ON {tbl} (user_id)")
        )
    else:
        db.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS effective_from date"))


def _ensure_manual_product_cogs_history_schema(db: Session) -> None:
    tbl = qname("manual_product_cogs_history")
    if not table_exists(db, tbl):
        db.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {tbl} (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL,
                    barcode_norm text NOT NULL,
                    cogs_sum numeric(18,2) NOT NULL,
                    effective_from date NOT NULL,
                    calculation_source text NOT NULL DEFAULT 'profiboard',
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
        )
        db.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS ix_manual_product_cogs_history_user_barcode
                ON {tbl} (user_id, barcode_norm, effective_from DESC, created_at DESC)
                """
            )
        )


def _append_cogs_history(
    db: Session,
    user_id: UUID,
    barcode_norm: str,
    cogs_sum: float,
    effective_from: str,
) -> None:
    _ensure_manual_product_cogs_history_schema(db)
    db.execute(
        text(f"""
            INSERT INTO {qname("manual_product_cogs_history")} (
                user_id, barcode_norm, cogs_sum, effective_from, calculation_source
            ) VALUES (
                CAST(:user_id AS uuid), :barcode_norm,
                CAST(:cogs_sum AS numeric(18,2)), CAST(:effective_from AS date), 'profiboard'
            )
        """),
        {
            "user_id": str(user_id),
            "barcode_norm": barcode_norm,
            "cogs_sum": cogs_sum,
            "effective_from": effective_from,
        },
    )


def _get_first_sale_date(db: Session, user_id: UUID, barcode_norm: str) -> Optional[str]:
    fs_barcode_norm_expr = (
        "CASE "
        "WHEN RIGHT(COALESCE(fs.barcode_norm, ''), 2) = '.0' "
        "THEN LEFT(COALESCE(fs.barcode_norm, ''), LENGTH(COALESCE(fs.barcode_norm, '')) - 2) "
        "ELSE COALESCE(fs.barcode_norm, '') END"
    )
    row = db.execute(
        text(f"""
            SELECT MIN(fs.date_created::date) AS first_sale_date
            FROM {qname("fact_sales")} fs
            WHERE fs.user_id = CAST(:user_id AS uuid)
              AND fs.barcode_norm IS NOT NULL
              AND {fs_barcode_norm_expr} = :barcode_norm
        """),
        {"user_id": str(user_id), "barcode_norm": barcode_norm},
    ).fetchone()
    if not row or not row[0]:
        return None
    val = row[0]
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def _get_last_sale_date(db: Session, user_id: UUID, barcode_norm: str) -> Optional[str]:
    fs_barcode_norm_expr = (
        "CASE "
        "WHEN RIGHT(COALESCE(fs.barcode_norm, ''), 2) = '.0' "
        "THEN LEFT(COALESCE(fs.barcode_norm, ''), LENGTH(COALESCE(fs.barcode_norm, '')) - 2) "
        "ELSE COALESCE(fs.barcode_norm, '') END"
    )
    row = db.execute(
        text(f"""
            SELECT MAX(fs.date_created::date) AS last_sale_date
            FROM {qname("fact_sales")} fs
            WHERE fs.user_id = CAST(:user_id AS uuid)
              AND fs.barcode_norm IS NOT NULL
              AND {fs_barcode_norm_expr} = :barcode_norm
        """),
        {"user_id": str(user_id), "barcode_norm": barcode_norm},
    ).fetchone()
    if not row or not row[0]:
        return None
    val = row[0]
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


def _iso_day_before(iso_date: str) -> str:
    return (date.fromisoformat(iso_date) - timedelta(days=1)).isoformat()


def _get_lk_cogs_for_barcode(db: Session, user_id: UUID, barcode_norm: str) -> Optional[float]:
    batch_row = db.execute(
        text(f"""
            SELECT upload_batch_id
            FROM {qname("fact_leftout_old_snapshot")}
            WHERE user_id = CAST(:user_id AS uuid)
            ORDER BY loaded_at DESC NULLS LAST
            LIMIT 1
        """),
        {"user_id": str(user_id)},
    ).fetchone()
    if batch_row and batch_row[0]:
        stg_row = db.execute(
            text(f"""
                SELECT sl.data, sl.cost_raw
                FROM {qname("stg_leftout_old")} sl
                WHERE sl.user_id = CAST(:user_id AS uuid)
                  AND sl.upload_batch_id = CAST(:batch_id AS uuid)
                  AND NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') = :barcode_norm
                LIMIT 1
            """),
            {
                "user_id": str(user_id),
                "batch_id": str(batch_row[0]),
                "barcode_norm": barcode_norm,
            },
        ).fetchone()
        if stg_row:
            data = stg_row[0] if isinstance(stg_row[0], dict) else {}
            lk_cogs = _parse_num(data.get("Себест. (сумы)")) or _parse_num(stg_row[1])
            if lk_cogs is not None:
                return lk_cogs

    fs_barcode_norm_expr = (
        "CASE "
        "WHEN RIGHT(COALESCE(fs.barcode_norm, ''), 2) = '.0' "
        "THEN LEFT(COALESCE(fs.barcode_norm, ''), LENGTH(COALESCE(fs.barcode_norm, '')) - 2) "
        "ELSE COALESCE(fs.barcode_norm, '') END"
    )
    sales_row = db.execute(
        text(f"""
            WITH last_dates AS (
                SELECT {fs_barcode_norm_expr} AS barcode_norm, MAX(fs.date_created::date) AS last_date
                FROM {qname("fact_sales")} fs
                WHERE fs.user_id = CAST(:user_id AS uuid) AND fs.barcode_norm IS NOT NULL
                  AND {_STATUS_REVENUE_SQL}
                GROUP BY {fs_barcode_norm_expr}
            )
            SELECT COALESCE(MAX(fs.cogs_sum), 0) AS unit_cogs
            FROM {qname("fact_sales")} fs
            JOIN last_dates ld
              ON ld.barcode_norm = {fs_barcode_norm_expr}
             AND fs.date_created::date = ld.last_date
            WHERE fs.user_id = CAST(:user_id AS uuid)
              AND {fs_barcode_norm_expr} = :barcode_norm
              AND {_STATUS_REVENUE_SQL}
        """),
        {"user_id": str(user_id), "barcode_norm": barcode_norm},
    ).fetchone()
    if sales_row and sales_row[0] and float(sales_row[0]) > 0:
        return float(sales_row[0])
    return None


def _load_profiboard_periods(db: Session, user_id: UUID, barcode_norm: str) -> list[tuple[str, float]]:
    """Периоды Profiboard: (effective_from, cogs), по возрастанию даты."""
    periods: list[tuple[str, float]] = []
    seen_dates: set[str] = set()

    tbl = qname("manual_product_cogs_history")
    if table_exists(db, tbl):
        _ensure_manual_product_cogs_history_schema(db)
        rows = db.execute(
            text(f"""
                SELECT DISTINCT ON (effective_from)
                    effective_from, cogs_sum
                FROM {tbl}
                WHERE user_id = CAST(:user_id AS uuid) AND barcode_norm = :barcode_norm
                ORDER BY effective_from ASC, created_at DESC
            """),
            {"user_id": str(user_id), "barcode_norm": barcode_norm},
        ).fetchall()
        for row in rows:
            eff = row[0]
            if eff is None:
                continue
            date_str = eff.isoformat() if hasattr(eff, "isoformat") else str(eff).strip()
            if date_str:
                periods.append((date_str, float(row[1] or 0)))
                seen_dates.add(date_str)

    manual_tbl = qname("manual_product_cogs")
    if table_exists(db, manual_tbl):
        db.execute(text(f"ALTER TABLE {manual_tbl} ADD COLUMN IF NOT EXISTS effective_from date"))
        row = db.execute(
            text(f"""
                SELECT effective_from, cogs_sum
                FROM {manual_tbl}
                WHERE user_id = CAST(:user_id AS uuid) AND barcode_norm = :barcode_norm
                LIMIT 1
            """),
            {"user_id": str(user_id), "barcode_norm": barcode_norm},
        ).fetchone()
        if row and row[0]:
            date_str = (
                row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]).strip()
            )
            if date_str and date_str not in seen_dates:
                periods.append((date_str, float(row[1] or 0)))

    periods.sort(key=lambda x: x[0])
    return periods


def _sync_manual_product_cogs_from_history(db: Session, user_id: UUID, barcode_norm: str) -> None:
    """После изменения истории — актуальная запись = последний период Profiboard или удаление."""
    periods = _load_profiboard_periods(db, user_id, barcode_norm)
    manual_tbl = qname("manual_product_cogs")
    if not table_exists(db, manual_tbl):
        return
    uid = str(user_id)
    if not periods:
        db.execute(
            text(f"""
                DELETE FROM {manual_tbl}
                WHERE user_id = CAST(:user_id AS uuid) AND barcode_norm = :barcode_norm
            """),
            {"user_id": uid, "barcode_norm": barcode_norm},
        )
        return
    eff_date, cogs = periods[-1]
    db.execute(
        text(f"""
            UPDATE {manual_tbl}
            SET cogs_sum = CAST(:cogs_sum AS numeric(18,2)),
                effective_from = CAST(:effective_from AS date),
                updated_at = now()
            WHERE user_id = CAST(:user_id AS uuid) AND barcode_norm = :barcode_norm
        """),
        {
            "user_id": uid,
            "barcode_norm": barcode_norm,
            "cogs_sum": cogs,
            "effective_from": eff_date,
        },
    )


def _load_latest_profiboard_by_barcode(db: Session, user_id: UUID) -> dict[str, dict]:
    """Последняя запись Profiboard по каждому штрихкоду (max effective_from)."""
    latest: dict[str, dict] = {}

    def _consider(bn: str, eff_raw, cogs_raw) -> None:
        if not bn or eff_raw is None:
            return
        eff_str = eff_raw.isoformat() if hasattr(eff_raw, "isoformat") else str(eff_raw).strip()
        if not eff_str:
            return
        cogs_val = float(cogs_raw or 0)
        prev = latest.get(bn)
        if prev is None or eff_str > prev["effective_from"]:
            latest[bn] = {"cogs": cogs_val, "effective_from": eff_str}

    tbl = qname("manual_product_cogs_history")
    if table_exists(db, tbl):
        _ensure_manual_product_cogs_history_schema(db)
        for row in db.execute(
            text(f"""
                SELECT DISTINCT ON (barcode_norm)
                    barcode_norm, effective_from, cogs_sum
                FROM {tbl}
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY barcode_norm, effective_from DESC, created_at DESC
            """),
            {"user_id": str(user_id)},
        ).fetchall():
            bn = (row[0] or "").strip()
            _consider(bn, row[1], row[2])

    manual_tbl = qname("manual_product_cogs")
    if table_exists(db, manual_tbl):
        db.execute(text(f"ALTER TABLE {manual_tbl} ADD COLUMN IF NOT EXISTS effective_from date"))
        for row in db.execute(
            text(f"""
                SELECT barcode_norm, effective_from, cogs_sum
                FROM {manual_tbl}
                WHERE user_id = CAST(:user_id AS uuid)
            """),
            {"user_id": str(user_id)},
        ).fetchall():
            bn = (row[0] or "").strip()
            _consider(bn, row[1], row[2])

    return latest


def _build_cogs_timeline(
    first_sale_date: Optional[str],
    last_sale_date: Optional[str],
    lk_cogs: Optional[float],
    profiboard_periods: list[tuple[str, float]],
) -> list[ProductCogsHistoryEntry]:
    """Хронология себестоимости за период продаж: Uzum с первой продажи, затем Profiboard."""
    segments: list[tuple[str, float, str]] = []
    first_pb_date = profiboard_periods[0][0] if profiboard_periods else None

    if first_sale_date and lk_cogs is not None:
        if not first_pb_date or first_pb_date > first_sale_date:
            segments.append((first_sale_date, lk_cogs, "uzum"))

    for eff_date, cogs in profiboard_periods:
        segments.append((eff_date, cogs, "profiboard"))

    if not segments:
        return []

    end_bound = last_sale_date or first_sale_date or date.today().isoformat()
    items: list[ProductCogsHistoryEntry] = []
    for i, (start, cogs, source) in enumerate(segments):
        if i + 1 < len(segments):
            period_to = _iso_day_before(segments[i + 1][0])
        else:
            period_to = end_bound
        if period_to < start:
            period_to = start
        items.append(
            ProductCogsHistoryEntry(
                period_from=start,
                period_to=period_to,
                cogs=cogs,
                calculation_source=source,
                effective_from=start if source == "profiboard" else None,
                can_delete=source == "profiboard",
            )
        )
    return items


def _load_manual_cogs_by_barcode(db: Session, user_id: UUID) -> dict[str, dict]:
    manual_by_barcode: dict[str, dict] = {}
    tbl = qname("manual_product_cogs")
    if not table_exists(db, tbl):
        return manual_by_barcode
    db.execute(text(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS effective_from date"))
    manual_query = text(f"""
        SELECT barcode_norm, cogs_sum, effective_from, barcode, sku, product_name, shop
        FROM {tbl}
        WHERE user_id = CAST(:user_id AS uuid)
    """)
    for row in db.execute(manual_query, {"user_id": str(user_id)}).fetchall():
        bn = (row[0] or "").strip()
        if bn:
            eff = row[2]
            effective_from_str = None
            if eff is not None:
                effective_from_str = (
                    eff.isoformat() if hasattr(eff, "isoformat") else str(eff).strip()
                )
            manual_by_barcode[bn] = {
                "cogs": float(row[1] or 0),
                "effective_from": effective_from_str,
                "barcode": row[3],
                "sku": row[4],
                "product_name": row[5],
                "shop": row[6],
            }
    return manual_by_barcode


@router.get("/product-cogs", response_model=ProductCogsListResponse)
async def list_product_cogs(
    user_id: UUID = Depends(require_user),
    shop: Optional[str] = Query(default=None, description="Shop name filter"),
    db: Session = Depends(get_db),
):
    """Себестоимость по штрихкоду: ЛК Uzum + актуальная (Profiboard)."""
    try:
        assert_trial_shop_filter_allowed(db, user_id, shop, None)
        shop_norm = normalize_shop(shop)

        params_batch = {"user_id": str(user_id)}
        shop_filter_sql = ""
        if shop_norm:
            params_batch["shop_norm"] = shop_norm
            shop_filter_sql = "\n              " + storage_barcode_filter_sql(
                "sl", prefix_and=True, outer_barcode_norm_expr=barcode_norm_sql("sl.barcode_raw")
            )

        # Последний батч left-out-report_old (как в shipment / products-table)
        if not shop_norm:
            batch_query = text(f"""
                SELECT upload_batch_id
                FROM {qname("fact_leftout_old_snapshot")}
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY loaded_at DESC NULLS LAST
                LIMIT 1
            """)
        else:
            batch_query = text(f"""
                SELECT sl.upload_batch_id FROM {qname("stg_leftout_old")} sl
                WHERE sl.user_id = CAST(:user_id AS uuid)
                {shop_filter_sql}
                ORDER BY sl.upload_batch_id DESC NULLS LAST
                LIMIT 1
            """)
        batch_row = db.execute(batch_query, params_batch).fetchone()
        if not batch_row or not batch_row[0]:
            return ProductCogsListResponse(items=[])

        batch_id = str(batch_row[0])
        params_stg = {"user_id": str(user_id), "batch_id": batch_id}
        if shop_norm:
            params_stg["shop_norm"] = shop_norm

        stg_query = text(f"""
            SELECT sl.data, sl.barcode_raw, sl.cost_raw, sl.price_raw,
                   NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') AS barcode_norm
            FROM {qname("stg_leftout_old")} sl
            WHERE sl.user_id = CAST(:user_id AS uuid)
              AND sl.upload_batch_id = CAST(:batch_id AS uuid)
            {shop_filter_sql if shop_norm else ""}
        """)
        stg_rows = db.execute(stg_query, params_stg).fetchall()

        fs_barcode_norm_expr = (
            "CASE "
            "WHEN RIGHT(COALESCE(fs.barcode_norm, ''), 2) = '.0' "
            "THEN LEFT(COALESCE(fs.barcode_norm, ''), LENGTH(COALESCE(fs.barcode_norm, '')) - 2) "
            "ELSE COALESCE(fs.barcode_norm, '') END"
        )
        sales_cogs_query = text(f"""
            WITH last_dates AS (
                SELECT {fs_barcode_norm_expr} AS barcode_norm, MAX(fs.date_created::date) AS last_date
                FROM {qname("fact_sales")} fs
                WHERE fs.user_id = CAST(:user_id AS uuid) AND fs.barcode_norm IS NOT NULL
                  AND {_STATUS_REVENUE_SQL}
                GROUP BY {fs_barcode_norm_expr}
            ),
            last_rows AS (
                SELECT {fs_barcode_norm_expr} AS barcode_norm, fs.cogs_sum, fs.revenue_sum, fs.qty, fs.returns_qty
                FROM {qname("fact_sales")} fs
                JOIN last_dates ld ON ld.barcode_norm = {fs_barcode_norm_expr} AND fs.date_created::date = ld.last_date
                WHERE fs.user_id = CAST(:user_id AS uuid) AND {_STATUS_REVENUE_SQL}
            )
            SELECT barcode_norm,
                   COALESCE(MAX(cogs_sum), 0) AS unit_cogs,
                   CASE WHEN COALESCE(SUM(GREATEST(COALESCE(qty,0)-COALESCE(returns_qty,0),0)),0) > 0
                        THEN SUM(COALESCE(revenue_sum,0)) / NULLIF(SUM(GREATEST(COALESCE(qty,0)-COALESCE(returns_qty,0),0)),0)
                        ELSE 0 END AS unit_price
            FROM last_rows
            GROUP BY barcode_norm
        """)
        sales_by_barcode: dict[str, dict] = {}
        for row in db.execute(sales_cogs_query, {"user_id": str(user_id)}).fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if bn:
                sales_by_barcode[bn] = {"cogs": float(row[1] or 0), "price": float(row[2] or 0)}

        first_sale_query = text(f"""
            SELECT {fs_barcode_norm_expr} AS barcode_norm, MIN(fs.date_created::date) AS first_sale_date
            FROM {qname("fact_sales")} fs
            WHERE fs.user_id = CAST(:user_id AS uuid) AND fs.barcode_norm IS NOT NULL
            GROUP BY {fs_barcode_norm_expr}
        """)
        first_sale_by_barcode: dict[str, str] = {}
        for row in db.execute(first_sale_query, {"user_id": str(user_id)}).fetchall():
            bn = (row[0] or "").strip() if row[0] else ""
            if bn and row[1]:
                first_sale_by_barcode[bn] = (
                    row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1])
                )

        latest_profiboard_by_barcode = _load_latest_profiboard_by_barcode(db, user_id)

        items: list[ProductCogsItem] = []
        for row in stg_rows:
            data = row[0]
            if not isinstance(data, dict):
                data = {}
            barcode_raw = _str_val(row[1])
            cost_raw = _str_val(row[2]) if len(row) > 2 else None
            price_raw = _str_val(row[3]) if len(row) > 3 else None
            barcode_norm = (row[4] or "").strip() if len(row) > 4 and row[4] else ""
            if not barcode_norm and barcode_raw:
                barcode_norm = _normalize_barcode_norm(barcode_raw)
            if not barcode_norm:
                continue

            product_name = _str_val(data.get("Наименование") or data.get("Название товара"))
            sku = _str_val(data.get("SKU"))
            barcode = _str_val(data.get("Штрихкод")) or barcode_raw

            price = _parse_num(data.get("Стоимость продажи (сумы)")) or _parse_num(price_raw)
            lk_cogs = _parse_num(data.get("Себест. (сумы)")) or _parse_num(cost_raw)

            sales_row = sales_by_barcode.get(barcode_norm)
            if sales_row:
                if not price or price <= 0:
                    price = sales_row["price"] or price
                if lk_cogs is None or lk_cogs <= 0:
                    lk_cogs = sales_row["cogs"] if sales_row["cogs"] > 0 else lk_cogs

            pb_row = latest_profiboard_by_barcode.get(barcode_norm)
            if pb_row:
                actual_cogs = pb_row["cogs"]
                effective_from_str = pb_row["effective_from"]
                used_cogs = actual_cogs
                calculation_source = "profiboard"
            else:
                actual_cogs = None
                effective_from_str = None
                used_cogs = lk_cogs
                calculation_source = "uzum"

            unit_margin = None
            if price is not None and used_cogs is not None:
                unit_margin = price - used_cogs

            date_str = effective_from_str

            items.append(
                ProductCogsItem(
                    barcode=barcode,
                    barcode_norm=barcode_norm,
                    product_name=product_name,
                    sku=sku,
                    product_image_url=_extract_product_image_url_from_data(data),
                    price=price,
                    lk_cogs=lk_cogs,
                    actual_cogs=actual_cogs,
                    unit_margin=unit_margin,
                    calculation_source=calculation_source,
                    date=date_str,
                    effective_from=effective_from_str,
                    first_sale_date=first_sale_by_barcode.get(barcode_norm),
                )
            )

        items.sort(key=lambda x: (x.product_name or "", x.barcode_norm))
        return ProductCogsListResponse(items=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_product_cogs failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/product-cogs/{barcode_norm}", response_model=ProductCogsItem)
async def upsert_product_cogs(
    barcode_norm: str,
    body: ProductCogsUpsertRequest,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Сохранить актуальную себестоимость (ЛК Profiboard)."""
    bn = _normalize_barcode_norm(barcode_norm)
    if not bn:
        raise HTTPException(status_code=400, detail="barcode_norm is required")
    if not body.effective_from:
        raise HTTPException(status_code=400, detail="effective_from is required")

    _ensure_manual_product_cogs_schema(db)

    upsert_query = text(f"""
        INSERT INTO {qname("manual_product_cogs")} (
            user_id, barcode_norm, barcode, sku, product_name, shop, cogs_sum, effective_from, updated_at
        ) VALUES (
            CAST(:user_id AS uuid), :barcode_norm, :barcode, :sku, :product_name, :shop,
            CAST(:cogs_sum AS numeric(18,2)), CAST(:effective_from AS date), now()
        )
        ON CONFLICT (user_id, barcode_norm) DO UPDATE SET
            barcode = EXCLUDED.barcode,
            sku = EXCLUDED.sku,
            product_name = EXCLUDED.product_name,
            shop = EXCLUDED.shop,
            cogs_sum = EXCLUDED.cogs_sum,
            effective_from = EXCLUDED.effective_from,
            updated_at = now()
        RETURNING barcode_norm, barcode, sku, product_name, cogs_sum, updated_at, effective_from
    """)
    row = db.execute(
        upsert_query,
        {
            "user_id": str(user_id),
            "barcode_norm": bn,
            "barcode": body.barcode,
            "sku": body.sku,
            "product_name": body.product_name,
            "shop": body.shop,
            "cogs_sum": body.actual_cogs,
            "effective_from": body.effective_from,
        },
    ).fetchone()

    _append_cogs_history(db, user_id, bn, body.actual_cogs, body.effective_from)
    db.commit()

    resp = await list_product_cogs(user_id=user_id, shop=body.shop, db=db)
    for item in resp.items:
        if item.barcode_norm == bn:
            return item

    return ProductCogsItem(
        barcode=row[1] if row else body.barcode,
        barcode_norm=bn,
        product_name=body.product_name,
        sku=body.sku,
        price=None,
        lk_cogs=None,
        actual_cogs=body.actual_cogs,
        unit_margin=None,
        calculation_source="profiboard",
        date=(
            row[6].isoformat()
            if row and row[6]
            else body.effective_from
        ),
        effective_from=(
            row[6].isoformat()
            if row and row[6]
            else body.effective_from
        ),
    )


@router.delete("/product-cogs/{barcode_norm}")
async def delete_product_cogs(
    barcode_norm: str,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Удалить актуальную себестоимость — вернуться к ЛК Uzum."""
    bn = _normalize_barcode_norm(barcode_norm)
    if not bn:
        raise HTTPException(status_code=400, detail="barcode_norm is required")

    result = db.execute(
        text(f"""
            DELETE FROM {qname("manual_product_cogs")}
            WHERE user_id = CAST(:user_id AS uuid) AND barcode_norm = :barcode_norm
        """),
        {"user_id": str(user_id), "barcode_norm": bn},
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.get("/product-cogs/{barcode_norm}/history", response_model=ProductCogsHistoryResponse)
async def get_product_cogs_history(
    barcode_norm: str,
    user_id: UUID = Depends(require_user),
    product_name: Optional[str] = Query(default=None),
    sku: Optional[str] = Query(default=None),
    lk_cogs: Optional[float] = Query(default=None, description="Себестоимость ЛК Uzum (fallback)"),
    db: Session = Depends(get_db),
):
    """Себестоимость по периодам продаж: Uzum с первой продажи, Profiboard с даты изменения."""
    bn = _normalize_barcode_norm(barcode_norm)
    if not bn:
        raise HTTPException(status_code=400, detail="barcode_norm is required")

    first_sale_date = _get_first_sale_date(db, user_id, bn)
    last_sale_date = _get_last_sale_date(db, user_id, bn)
    lk_value = lk_cogs if lk_cogs is not None and lk_cogs > 0 else _get_lk_cogs_for_barcode(db, user_id, bn)
    profiboard_periods = _load_profiboard_periods(db, user_id, bn)
    items = _build_cogs_timeline(first_sale_date, last_sale_date, lk_value, profiboard_periods)

    return ProductCogsHistoryResponse(
        product_name=product_name,
        sku=sku,
        first_sale_date=first_sale_date,
        items=items,
    )


@router.delete("/product-cogs/{barcode_norm}/history", response_model=ProductCogsHistoryResponse)
async def delete_product_cogs_history_period(
    barcode_norm: str,
    effective_from: str = Query(..., description="Дата начала периода Profiboard (YYYY-MM-DD)"),
    user_id: UUID = Depends(require_user),
    product_name: Optional[str] = Query(default=None),
    sku: Optional[str] = Query(default=None),
    lk_cogs: Optional[float] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Удалить период Profiboard из истории. Период ЛК Uzum не удаляется — восстанавливается при удалении записей поверх."""
    bn = _normalize_barcode_norm(barcode_norm)
    if not bn:
        raise HTTPException(status_code=400, detail="barcode_norm is required")
    eff = (effective_from or "").strip()
    if len(eff) != 10 or eff[4] != "-" or eff[7] != "-":
        raise HTTPException(status_code=400, detail="effective_from must be YYYY-MM-DD")

    _ensure_manual_product_cogs_history_schema(db)
    tbl = qname("manual_product_cogs_history")
    result = db.execute(
        text(f"""
            DELETE FROM {tbl}
            WHERE user_id = CAST(:user_id AS uuid)
              AND barcode_norm = :barcode_norm
              AND effective_from = CAST(:effective_from AS date)
        """),
        {"user_id": str(user_id), "barcode_norm": bn, "effective_from": eff},
    )
    manual_tbl = qname("manual_product_cogs")
    manual_deleted = 0
    if table_exists(db, manual_tbl):
        manual_deleted = (
            db.execute(
                text(f"""
                    DELETE FROM {manual_tbl}
                    WHERE user_id = CAST(:user_id AS uuid)
                      AND barcode_norm = :barcode_norm
                      AND effective_from = CAST(:effective_from AS date)
                """),
                {"user_id": str(user_id), "barcode_norm": bn, "effective_from": eff},
            ).rowcount
            or 0
        )
    if result.rowcount == 0 and manual_deleted == 0:
        raise HTTPException(status_code=404, detail="History period not found")

    _sync_manual_product_cogs_from_history(db, user_id, bn)
    db.commit()

    return await get_product_cogs_history(
        barcode_norm=bn,
        user_id=user_id,
        product_name=product_name,
        sku=sku,
        lk_cogs=lk_cogs,
        db=db,
    )
