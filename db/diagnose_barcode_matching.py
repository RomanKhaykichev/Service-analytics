#!/usr/bin/env python3
"""
Диагностический скрипт для проверки совпадений по barcode_norm между источниками данных.

Проверяет:
- % совпадений по barcode_norm между leftout ↔ sales, storage ↔ sales, leftout ↔ storage
- Топ-20 "не матчится" barcode (есть в одном источнике, нет в другом)
- Количество строк с пустым barcode_norm по каждому источнику

Использование:
    python db/diagnose_barcode_matching.py [user_id]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()

def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD")
    )

def diagnose_barcode_matching(conn, user_id: str = None):
    """Run diagnostic queries for barcode_norm matching."""
    
    schema = "app"
    params = {}
    user_filter = ""
    
    if user_id:
        user_filter = "AND user_id = CAST(:user_id AS uuid)"
        params["user_id"] = user_id
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        print("=" * 80)
        print("ДИАГНОСТИКА СОВПАДЕНИЙ ПО BARCODE_NORM")
        print("=" * 80)
        print()
        
        # 1. Coverage: количество строк с barcode_norm по каждому источнику
        print("1. ПОКРЫТИЕ BARCODE_NORM ПО ИСТОЧНИКАМ:")
        print("-" * 80)
        
        cur.execute(f"""
            SELECT 
                'fact_sales' AS source,
                COUNT(*) AS total_rows,
                COUNT(barcode_norm) AS rows_with_barcode_norm,
                COUNT(*) - COUNT(barcode_norm) AS rows_without_barcode_norm,
                ROUND(100.0 * COUNT(barcode_norm) / NULLIF(COUNT(*), 0), 2) AS coverage_pct
            FROM {schema}.fact_sales
            WHERE 1=1 {user_filter}
            UNION ALL
            SELECT 
                'fact_leftout_snapshot',
                COUNT(*),
                COUNT(barcode_norm),
                COUNT(*) - COUNT(barcode_norm),
                ROUND(100.0 * COUNT(barcode_norm) / NULLIF(COUNT(*), 0), 2)
            FROM {schema}.fact_leftout_snapshot
            WHERE 1=1 {user_filter}
            UNION ALL
            SELECT 
                'fact_storage_snapshot',
                COUNT(*),
                COUNT(barcode_norm),
                COUNT(*) - COUNT(barcode_norm),
                ROUND(100.0 * COUNT(barcode_norm) / NULLIF(COUNT(*), 0), 2)
            FROM {schema}.fact_storage_snapshot
            WHERE 1=1 {user_filter}
            ORDER BY source
        """, params)
        
        for row in cur.fetchall():
            print(f"  {row['source']:25} | Всего: {row['total_rows']:8} | "
                  f"С barcode_norm: {row['rows_with_barcode_norm']:8} | "
                  f"Без: {row['rows_without_barcode_norm']:8} | "
                  f"Покрытие: {row['coverage_pct']:6.2f}%")
        print()
        
        # 2. Совпадения между источниками
        print("2. СОВПАДЕНИЯ ПО BARCODE_NORM МЕЖДУ ИСТОЧНИКАМИ:")
        print("-" * 80)
        
        cur.execute(f"""
            WITH leftout_barcodes AS (
                SELECT DISTINCT barcode_norm
                FROM {schema}.fact_leftout_snapshot
                WHERE barcode_norm IS NOT NULL {user_filter}
            ),
            sales_barcodes AS (
                SELECT DISTINCT barcode_norm
                FROM {schema}.fact_sales
                WHERE barcode_norm IS NOT NULL {user_filter}
            ),
            storage_barcodes AS (
                SELECT DISTINCT barcode_norm
                FROM {schema}.fact_storage_snapshot
                WHERE barcode_norm IS NOT NULL {user_filter}
            ),
            leftout_sales_match AS (
                SELECT COUNT(*) AS matched
                FROM leftout_barcodes l
                INNER JOIN sales_barcodes s ON l.barcode_norm = s.barcode_norm
            ),
            storage_sales_match AS (
                SELECT COUNT(*) AS matched
                FROM storage_barcodes st
                INNER JOIN sales_barcodes s ON st.barcode_norm = s.barcode_norm
            ),
            leftout_storage_match AS (
                SELECT COUNT(*) AS matched
                FROM leftout_barcodes l
                INNER JOIN storage_barcodes st ON l.barcode_norm = st.barcode_norm
            )
            SELECT 
                (SELECT COUNT(*) FROM leftout_barcodes) AS leftout_unique,
                (SELECT COUNT(*) FROM sales_barcodes) AS sales_unique,
                (SELECT COUNT(*) FROM storage_barcodes) AS storage_unique,
                (SELECT matched FROM leftout_sales_match) AS leftout_sales_matched,
                (SELECT matched FROM storage_sales_match) AS storage_sales_matched,
                (SELECT matched FROM leftout_storage_match) AS leftout_storage_matched
        """, params)
        
        match_row = cur.fetchone()
        if match_row:
            leftout_total = match_row['leftout_unique'] or 0
            sales_total = match_row['sales_unique'] or 0
            storage_total = match_row['storage_unique'] or 0
            leftout_sales_matched = match_row['leftout_sales_matched'] or 0
            storage_sales_matched = match_row['storage_sales_matched'] or 0
            leftout_storage_matched = match_row['leftout_storage_matched'] or 0
            
            print(f"  leftout ↔ sales:")
            print(f"    Уникальных в leftout: {leftout_total}")
            print(f"    Уникальных в sales: {sales_total}")
            print(f"    Совпадает: {leftout_sales_matched} "
                  f"({100.0 * leftout_sales_matched / max(leftout_total, 1):.2f}% от leftout, "
                  f"{100.0 * leftout_sales_matched / max(sales_total, 1):.2f}% от sales)")
            print()
            
            print(f"  storage ↔ sales:")
            print(f"    Уникальных в storage: {storage_total}")
            print(f"    Уникальных в sales: {sales_total}")
            print(f"    Совпадает: {storage_sales_matched} "
                  f"({100.0 * storage_sales_matched / max(storage_total, 1):.2f}% от storage, "
                  f"{100.0 * storage_sales_matched / max(sales_total, 1):.2f}% от sales)")
            print()
            
            print(f"  leftout ↔ storage:")
            print(f"    Уникальных в leftout: {leftout_total}")
            print(f"    Уникальных в storage: {storage_total}")
            print(f"    Совпадает: {leftout_storage_matched} "
                  f"({100.0 * leftout_storage_matched / max(leftout_total, 1):.2f}% от leftout, "
                  f"{100.0 * leftout_storage_matched / max(storage_total, 1):.2f}% от storage)")
        print()
        
        # 3. Топ-20 "не матчится" barcode
        print("3. ТОП-20 BARCODE, КОТОРЫЕ ЕСТЬ В ОДНОМ ИСТОЧНИКЕ, НО НЕТ В ДРУГОМ:")
        print("-" * 80)
        
        # leftout без sales
        cur.execute(f"""
            SELECT 
                l.barcode_norm,
                COUNT(*) AS leftout_count,
                0 AS sales_count
            FROM {schema}.fact_leftout_snapshot l
            WHERE l.barcode_norm IS NOT NULL {user_filter}
              AND NOT EXISTS (
                  SELECT 1 FROM {schema}.fact_sales s
                  WHERE s.barcode_norm = l.barcode_norm {user_filter}
              )
            GROUP BY l.barcode_norm
            ORDER BY leftout_count DESC
            LIMIT 10
        """, params)
        
        print("  В leftout, но НЕТ в sales:")
        for row in cur.fetchall():
            print(f"    {row['barcode_norm']:30} | leftout: {row['leftout_count']:5} | sales: {row['sales_count']:5}")
        print()
        
        # sales без leftout
        cur.execute(f"""
            SELECT 
                s.barcode_norm,
                0 AS leftout_count,
                COUNT(*) AS sales_count
            FROM {schema}.fact_sales s
            WHERE s.barcode_norm IS NOT NULL {user_filter}
              AND NOT EXISTS (
                  SELECT 1 FROM {schema}.fact_leftout_snapshot l
                  WHERE l.barcode_norm = s.barcode_norm {user_filter}
              )
            GROUP BY s.barcode_norm
            ORDER BY sales_count DESC
            LIMIT 10
        """, params)
        
        print("  В sales, но НЕТ в leftout:")
        for row in cur.fetchall():
            print(f"    {row['barcode_norm']:30} | leftout: {row['leftout_count']:5} | sales: {row['sales_count']:5}")
        print()
        
        # storage без sales
        cur.execute(f"""
            SELECT 
                st.barcode_norm,
                COUNT(*) AS storage_count,
                0 AS sales_count
            FROM {schema}.fact_storage_snapshot st
            WHERE st.barcode_norm IS NOT NULL {user_filter}
              AND NOT EXISTS (
                  SELECT 1 FROM {schema}.fact_sales s
                  WHERE s.barcode_norm = st.barcode_norm {user_filter}
              )
            GROUP BY st.barcode_norm
            ORDER BY storage_count DESC
            LIMIT 10
        """, params)
        
        print("  В storage, но НЕТ в sales:")
        for row in cur.fetchall():
            print(f"    {row['barcode_norm']:30} | storage: {row['storage_count']:5} | sales: {row['sales_count']:5}")
        print()
        
        # 4. map_shop_barcode статистика
        print("4. СТАТИСТИКА MAP_SHOP_BARCODE:")
        print("-" * 80)
        
        cur.execute(f"""
            SELECT 
                COUNT(*) AS total_mappings,
                COUNT(DISTINCT barcode_norm) AS unique_barcodes,
                COUNT(DISTINCT shop_id) AS unique_shops,
                COUNT(DISTINCT sku) AS unique_skus
            FROM {schema}.map_shop_barcode
            WHERE 1=1 {user_filter}
        """, params)
        
        map_row = cur.fetchone()
        if map_row:
            print(f"  Всего маппингов: {map_row['total_mappings']}")
            print(f"  Уникальных barcode_norm: {map_row['unique_barcodes']}")
            print(f"  Уникальных shop_id: {map_row['unique_shops']}")
            print(f"  Уникальных sku: {map_row['unique_skus']}")
        print()
        
        print("=" * 80)
        print("ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 80)

def main():
    """Main entry point."""
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if user_id:
        print(f"Диагностика для user_id: {user_id}")
    else:
        print("Диагностика для всех пользователей")
    print()
    
    conn = get_connection()
    try:
        diagnose_barcode_matching(conn, user_id)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
