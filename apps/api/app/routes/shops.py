from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from uuid import UUID
import logging
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
