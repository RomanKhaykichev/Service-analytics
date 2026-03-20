from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
import logging
from typing import Optional
from app.db import get_db, qname
from app.deps import require_user
from app.schemas import ShopsResponse, Shop

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/shops", response_model=ShopsResponse)
async def get_shops(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get list of shops from v_sales_daily."""
    shops = []
    
    logger.info(f"get_shops: user_id={user_id}, schema={qname('v_sales_daily')}")
    
    try:
        # ТЗ: Магазины для фильтра склада должны браться из left-out-report (fact_leftout_snapshot)
        # dim_shop заполняется из left-out-report при импорте, поэтому используем его как основной источник
        # Также включаем магазины из продаж для совместимости
        try:
            # Объединяем магазины из dim_shop (left-out-report) и fact_sales (sells-report)
            # Фильтруем пустые/NULL магазины ("не определено")
            query = text(f"""
                SELECT DISTINCT shop_id::text, shop_name
                FROM {qname("dim_shop")}
                WHERE user_id = CAST(:user_id AS uuid)
                  AND shop_name IS NOT NULL
                  AND TRIM(shop_name) <> ''
                  AND lower(TRIM(shop_name)) NOT IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
                UNION
                SELECT DISTINCT shop_id::text, NULL::text AS shop_name
                FROM {qname("fact_sales")}
                WHERE user_id = CAST(:user_id AS uuid)
                  AND shop_id IS NOT NULL
                  AND shop_id NOT IN (
                      SELECT shop_id FROM {qname("dim_shop")} 
                      WHERE user_id = CAST(:user_id AS uuid)
                        AND shop_name IS NOT NULL
                        AND TRIM(shop_name) <> ''
                        AND lower(TRIM(shop_name)) NOT IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
                  )
                ORDER BY shop_id
            """)
            result = db.execute(query, {"user_id": str(user_id)})
            rows = result.fetchall()
            
            if rows:
                logger.info(f"get_shops: found {len(rows)} shops (dim_shop + fact_sales)")
                shops = [
                    Shop(
                        shop_id=row[0], 
                        shop_name=row[1] or f"Shop {row[0]}"
                    )
                    for row in rows
                ]
                return ShopsResponse(shops=shops)
        except Exception as e:
            logger.debug(f"dim_shop/fact_sales not available: {e}. Using v_sales_daily.")
        
        # Fallback to v_sales_daily - just shop_id
        query = text(f"""
            SELECT DISTINCT shop_id
            FROM {qname("v_sales_daily")}
            WHERE user_id = CAST(:user_id AS uuid)
            ORDER BY shop_id
        """)
        result = db.execute(query, {"user_id": str(user_id)})
        rows = result.fetchall()
        logger.info(f"get_shops: found {len(rows)} shops from v_sales_daily")
        
        shops = [
            Shop(shop_id=str(row[0]), shop_name=f"Shop {row[0]}")
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to query shops: {e}")
        shops = []
    
    return ShopsResponse(shops=shops)


@router.get("/storage/shops", response_model=ShopsResponse)
async def get_storage_shops(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get list of shops from seller-storage ONLY (source of truth for shop filter).
    
    Uses app.fact_storage_snapshot.shop_raw first (persistent); fallback to stg_storage.shop_raw.
    Returns DISTINCT shop names — column "Магазин" from seller-storage file.
    
    Returns:
    - shop_id: normalized value (UPPER, single spaces) — used as shop= query param for KPI
    - shop_name: original label — for display in UI
    """
    shops: list[Shop] = []

    # Tariff-based limit for what we show in the shop filter UI.
    # Trial: 1 shop, Month 5: 5 shops, Month 10: 10 shops, Gold: unlimited.
    max_shops: Optional[int] = None
    try:
        plan_row = db.execute(
            text(f"SELECT COALESCE(plan, 'trial') FROM {qname('users')} WHERE id = CAST(:uid AS uuid)"),
            {"uid": str(user_id)},
        ).fetchone()
        plan_val = (plan_row[0] or "trial").strip().lower() if plan_row else "trial"
        if plan_val in ("trial", "", None) or not plan_val:
            max_shops = 1
        elif plan_val in ("month_5", "month 5", "month5"):
            max_shops = 5
        elif plan_val in ("month_10", "month 10", "month10"):
            max_shops = 10
        elif plan_val in ("gold", "gold_plan"):
            max_shops = None
        else:
            # fail-safe: show 1 shop for unknown plan
            max_shops = 1
    except Exception:
        max_shops = 1
    
    logger.info(f"get_storage_shops: user_id={user_id}")
    
    try:
        # 1) Prefer fact_storage_snapshot.shop_raw (persistent, survives staging clear)
        query_fss = text(f"""
            WITH src AS (
                SELECT NULLIF(trim(fss.shop_raw), '') AS shop_raw
                FROM {qname("fact_storage_snapshot")} fss
                WHERE fss.user_id = CAST(:user_id AS uuid)
                    AND NULLIF(trim(fss.shop_raw), '') IS NOT NULL
                    AND lower(trim(fss.shop_raw)) NOT IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
            ),
            norm AS (
                SELECT
                    shop_raw,
                    upper(regexp_replace(trim(shop_raw), '\\s+', ' ', 'g')) AS shop_norm
                FROM src
                WHERE shop_raw IS NOT NULL
            )
            SELECT DISTINCT
                shop_norm AS value,
                MIN(shop_raw) AS label
            FROM norm
            GROUP BY shop_norm
            ORDER BY value
        """)
        result = db.execute(query_fss, {"user_id": str(user_id)})
        rows = result.fetchall()
        
        if rows:
            logger.info(f"get_storage_shops: found {len(rows)} shops from fact_storage_snapshot.shop_raw")
            shops = [
                Shop(
                    shop_id=row[0] or "",
                    shop_name=row[1] or row[0] or ""
                )
                for row in rows
            ]
            if max_shops is not None:
                shops = shops[:max_shops]
            return ShopsResponse(shops=shops)
        
        # 2) Fallback: stg_storage.shop_raw (when fact_storage_snapshot is empty)
        logger.info(f"get_storage_shops: no shops in fact_storage_snapshot, trying stg_storage")
        query_stg = text(f"""
            WITH src AS (
                SELECT NULLIF(trim(ss.shop_raw), '') AS shop_raw
                FROM {qname("stg_storage")} ss
                WHERE ss.user_id = CAST(:user_id AS uuid)
                    AND NULLIF(trim(ss.shop_raw), '') IS NOT NULL
                    AND lower(trim(ss.shop_raw)) NOT IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
            ),
            norm AS (
                SELECT
                    shop_raw,
                    upper(regexp_replace(trim(shop_raw), '\\s+', ' ', 'g')) AS shop_norm
                FROM src
                WHERE shop_raw IS NOT NULL
            )
            SELECT DISTINCT
                shop_norm AS value,
                MIN(shop_raw) AS label
            FROM norm
            GROUP BY shop_norm
            ORDER BY value
        """)
        result = db.execute(query_stg, {"user_id": str(user_id)})
        rows = result.fetchall()
        
        if rows:
            logger.info(f"get_storage_shops: found {len(rows)} shops from stg_storage.shop_raw")
            shops = [
                Shop(shop_id=row[0] or "", shop_name=row[1] or row[0] or "")
                for row in rows
            ]
            if max_shops is not None:
                shops = shops[:max_shops]
        else:
            logger.info(f"get_storage_shops: no shops found")
    except Exception as e:
        logger.error(f"Failed to query storage shops: {e}", exc_info=True)
        shops = []
    
    return ShopsResponse(shops=shops)
