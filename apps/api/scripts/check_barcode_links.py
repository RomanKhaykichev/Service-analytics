#!/usr/bin/env python3
"""
Диагностический скрипт для проверки связей по штрихкоду между источниками данных.

Проверяет:
- Заполненность штрихкода в каждой таблице
- Coverage: процент совпадений между источниками
- Примеры несоответствий (топ-20 missing barcodes)

Использование:
    python apps/api/scripts/check_barcode_links.py [user_id] [shop_id]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
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

def normalize_barcode(barcode_expr: str) -> str:
    """Return SQL expression for normalized barcode."""
    return f"NULLIF(TRIM(regexp_replace({barcode_expr}, '\\s+', '', 'g')), '')"

def check_barcode_links(conn, user_id: str = None, shop_id: str = None):
    """Run diagnostic queries for barcode linking."""
    
    schema = "app"
    params = {}
    user_filter = ""
    shop_filter = ""
    
    if user_id:
        user_filter = "AND user_id = CAST(:user_id AS uuid)"
        params["user_id"] = user_id
    
    if shop_id:
        shop_filter = "AND shop_id = CAST(:shop_id AS uuid)"
        params["shop_id"] = shop_id
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        print("=" * 80)
        print("ДИАГНОСТИКА СВЯЗЕЙ ПО ШТРИХКОДУ")
        print("=" * 80)
        if user_id:
            print(f"User ID: {user_id}")
        if shop_id:
            print(f"Shop ID: {shop_id}")
        print()
        
        # A) Заполненность штрихкода
        print("A) ЗАПОЛНЕННОСТЬ ШТРИХКОДА ПО ТАБЛИЦАМ:")
        print("-" * 80)
        
        cur.execute(f"""
            SELECT 
                'fact_leftout_snapshot' AS table_name,
                COUNT(*) AS total_rows,
                COUNT(CASE WHEN barcode IS NULL OR TRIM(barcode) = '' THEN 1 END) AS empty_barcode,
                COUNT(DISTINCT barcode) AS distinct_barcode,
                COUNT(DISTINCT {normalize_barcode('barcode')}) AS distinct_barcode_norm
            FROM {schema}.fact_leftout_snapshot
            WHERE 1=1 {user_filter} {shop_filter}
            UNION ALL
            SELECT 
                'fact_sales',
                COUNT(*),
                COUNT(CASE WHEN barcode IS NULL OR TRIM(barcode) = '' THEN 1 END),
                COUNT(DISTINCT barcode),
                COUNT(DISTINCT {normalize_barcode('barcode')})
            FROM {schema}.fact_sales
            WHERE 1=1 {user_filter} {shop_filter}
            UNION ALL
            SELECT 
                'fact_storage_snapshot',
                COUNT(*),
                COUNT(CASE WHEN barcode IS NULL OR TRIM(barcode) = '' THEN 1 END),
                COUNT(DISTINCT barcode),
                COUNT(DISTINCT {normalize_barcode('barcode')})
            FROM {schema}.fact_storage_snapshot
            WHERE 1=1 {user_filter} {shop_filter}
            ORDER BY table_name
        """, params)
        
        for row in cur.fetchall():
            empty_pct = (row['empty_barcode'] / row['total_rows'] * 100) if row['total_rows'] > 0 else 0
            print(f"  {row['table_name']:25} | Всего строк: {row['total_rows']:8} | "
                  f"Пустых barcode: {row['empty_barcode']:6} ({empty_pct:5.2f}%) | "
                  f"Уникальных barcode: {row['distinct_barcode']:6} | "
                  f"Уникальных (норм): {row['distinct_barcode_norm']:6}")
        print()
        
        # Получить последний snapshot для leftout
        cur.execute(f"""
            SELECT MAX(loaded_at) AS snap_loaded_at
            FROM {schema}.fact_leftout_snapshot
            WHERE 1=1 {user_filter} {shop_filter}
        """, params)
        snap_result = cur.fetchone()
        snap_loaded_at = snap_result['snap_loaded_at'] if snap_result else None
        
        if not snap_loaded_at:
            print("⚠️  Нет данных в fact_leftout_snapshot для выбранного user_id/shop_id")
            return
        
        params["snap_loaded_at"] = snap_loaded_at
        params["date_90d_ago"] = (datetime.now() - timedelta(days=90)).date().isoformat()
        
        # B) Coverage: leftout -> sales
        print("B) COVERAGE: leftout -> sales (за последние 90 дней):")
        print("-" * 80)
        
        cur.execute(f"""
            WITH lo AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_leftout_snapshot
                WHERE user_id = CAST(:user_id AS uuid) 
                  AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            ),
            sa AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_sales
                WHERE user_id = CAST(:user_id AS uuid)
                  AND date_created >= CAST(:date_90d_ago AS date)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            )
            SELECT
                COUNT(*) AS lo_total,
                SUM(CASE WHEN sa.b IS NOT NULL THEN 1 ELSE 0 END) AS matched,
                ROUND(100.0 * SUM(CASE WHEN sa.b IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS matched_pct
            FROM lo
            LEFT JOIN sa ON lo.b = sa.b
        """, params)
        
        leftout_sales = cur.fetchone()
        if leftout_sales:
            print(f"  Уникальных barcode в leftout: {leftout_sales['lo_total']}")
            print(f"  Найдено в sales: {leftout_sales['matched']}")
            print(f"  Процент совпадений: {leftout_sales['matched_pct']:.2f}%")
        print()
        
        # C) Coverage: storage -> sales
        print("C) COVERAGE: storage -> sales (за последние 90 дней):")
        print("-" * 80)
        
        cur.execute(f"""
            WITH st AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_storage_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            ),
            sa AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_sales
                WHERE user_id = CAST(:user_id AS uuid)
                  AND date_created >= CAST(:date_90d_ago AS date)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            )
            SELECT
                COUNT(*) AS st_total,
                SUM(CASE WHEN sa.b IS NOT NULL THEN 1 ELSE 0 END) AS matched,
                ROUND(100.0 * SUM(CASE WHEN sa.b IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS matched_pct
            FROM st
            LEFT JOIN sa ON st.b = sa.b
        """, params)
        
        storage_sales = cur.fetchone()
        if storage_sales:
            print(f"  Уникальных barcode в storage: {storage_sales['st_total']}")
            print(f"  Найдено в sales: {storage_sales['matched']}")
            print(f"  Процент совпадений: {storage_sales['matched_pct']:.2f}%")
        print()
        
        # D) Coverage: leftout <-> storage
        print("D) COVERAGE: leftout <-> storage (пересечение):")
        print("-" * 80)
        
        cur.execute(f"""
            WITH lo AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_leftout_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            ),
            st AS (
                SELECT DISTINCT {normalize_barcode('barcode')} AS b
                FROM {schema}.fact_storage_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
            )
            SELECT
                (SELECT COUNT(*) FROM lo) AS lo_total,
                (SELECT COUNT(*) FROM st) AS st_total,
                COUNT(*) AS intersection,
                ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM lo), 0), 2) AS pct_from_lo,
                ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM st), 0), 2) AS pct_from_st
            FROM lo
            INNER JOIN st ON lo.b = st.b
        """, params)
        
        leftout_storage = cur.fetchone()
        if leftout_storage:
            print(f"  Уникальных barcode в leftout: {leftout_storage['lo_total']}")
            print(f"  Уникальных barcode в storage: {leftout_storage['st_total']}")
            print(f"  Пересечение: {leftout_storage['intersection']}")
            print(f"  Процент от leftout: {leftout_storage['pct_from_lo']:.2f}%")
            print(f"  Процент от storage: {leftout_storage['pct_from_st']:.2f}%")
        print()
        
        # E) Примеры несоответствий
        print("E) ПРИМЕРЫ НЕСООТВЕТСТВИЙ (топ-20):")
        print("-" * 80)
        
        # leftout без sales
        cur.execute(f"""
            SELECT 
                {normalize_barcode('l.barcode')} AS barcode_norm,
                l.barcode AS barcode_raw,
                COUNT(*) AS leftout_count,
                0 AS sales_count
            FROM {schema}.fact_leftout_snapshot l
            WHERE l.user_id = CAST(:user_id AS uuid)
              AND l.loaded_at = CAST(:snap_loaded_at AS timestamp)
              {shop_filter}
              AND l.barcode IS NOT NULL
              AND TRIM(l.barcode) != ''
              AND NOT EXISTS (
                  SELECT 1 FROM {schema}.fact_sales s
                  WHERE s.user_id = CAST(:user_id AS uuid)
                    AND s.date_created >= CAST(:date_90d_ago AS date)
                    {shop_filter}
                    AND {normalize_barcode('s.barcode')} = {normalize_barcode('l.barcode')}
              )
            GROUP BY {normalize_barcode('l.barcode')}, l.barcode
            ORDER BY leftout_count DESC
            LIMIT 20
        """, params)
        
        print("  В leftout, но НЕТ в sales (топ-20):")
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"    {i:2}. barcode_norm='{row['barcode_norm']}' | "
                  f"raw='{row['barcode_raw']}' | leftout: {row['leftout_count']:5} строк")
        print()
        
        # storage без sales
        cur.execute(f"""
            SELECT 
                {normalize_barcode('st.barcode')} AS barcode_norm,
                st.barcode AS barcode_raw,
                COUNT(*) AS storage_count,
                0 AS sales_count
            FROM {schema}.fact_storage_snapshot st
            WHERE st.user_id = CAST(:user_id AS uuid)
              {shop_filter}
              AND st.barcode IS NOT NULL
              AND TRIM(st.barcode) != ''
              AND NOT EXISTS (
                  SELECT 1 FROM {schema}.fact_sales s
                  WHERE s.user_id = CAST(:user_id AS uuid)
                    AND s.date_created >= CAST(:date_90d_ago AS date)
                    {shop_filter}
                    AND {normalize_barcode('s.barcode')} = {normalize_barcode('st.barcode')}
              )
            GROUP BY {normalize_barcode('st.barcode')}, st.barcode
            ORDER BY storage_count DESC
            LIMIT 20
        """, params)
        
        print("  В storage, но НЕТ в sales (топ-20):")
        for i, row in enumerate(cur.fetchall(), 1):
            print(f"    {i:2}. barcode_norm='{row['barcode_norm']}' | "
                  f"raw='{row['barcode_raw']}' | storage: {row['storage_count']:5} строк")
        print()
        
        # F) Анализ форматов barcode
        print("F) АНАЛИЗ ФОРМАТОВ BARCODE:")
        print("-" * 80)
        
        cur.execute(f"""
            WITH samples AS (
                SELECT 
                    'leftout' AS source,
                    barcode,
                    {normalize_barcode('barcode')} AS barcode_norm,
                    LENGTH(barcode) AS len_raw,
                    LENGTH({normalize_barcode('barcode')}) AS len_norm
                FROM {schema}.fact_leftout_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  AND loaded_at = CAST(:snap_loaded_at AS timestamp)
                  {shop_filter}
                  AND barcode IS NOT NULL
                  AND TRIM(barcode) != ''
                LIMIT 100
            )
            SELECT 
                source,
                COUNT(*) AS total_samples,
                COUNT(CASE WHEN len_raw != len_norm THEN 1 END) AS with_spaces,
                COUNT(CASE WHEN barcode ~ '^0' THEN 1 END) AS leading_zeros,
                MIN(len_norm) AS min_len,
                MAX(len_norm) AS max_len,
                AVG(len_norm) AS avg_len
            FROM samples
            GROUP BY source
        """, params)
        
        for row in cur.fetchall():
            print(f"  {row['source']}:")
            print(f"    Всего образцов: {row['total_samples']}")
            print(f"    С пробелами (raw != norm): {row['with_spaces']}")
            print(f"    С лидирующими нулями: {row['leading_zeros']}")
            print(f"    Длина: min={row['min_len']}, max={row['max_len']}, avg={row['avg_len']:.1f}")
        print()
        
        print("=" * 80)
        print("ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("=" * 80)
        
        # Итоговый вывод
        print("\nИТОГОВЫЙ ВЫВОД:")
        print("-" * 80)
        print("Используемые таблицы и колонки:")
        print("  - fact_leftout_snapshot: barcode (Штрихкод), in_sale (В продаже, шт)")
        print("  - fact_storage_snapshot: barcode (Штрихкод), avg_stock_15d, avg_sales_15d, fbo_stock_total")
        print("  - fact_sales: barcode (Штрихкод), qty, revenue_sum, cogs_sum")
        print()
        
        if leftout_sales and storage_sales:
            print("Процент совпадений:")
            print(f"  leftout -> sales: {leftout_sales['matched_pct']:.2f}%")
            print(f"  storage -> sales: {storage_sales['matched_pct']:.2f}%")
            if leftout_storage:
                print(f"  leftout <-> storage: {leftout_storage['pct_from_lo']:.2f}% (от leftout), {leftout_storage['pct_from_st']:.2f}% (от storage)")
            print()
            
            # Оценка качества связи
            if leftout_sales['matched_pct'] >= 80 and storage_sales['matched_pct'] >= 80:
                print("✅ Связь по штрихкоду: НОРМАЛЬНАЯ")
                print("   Большинство товаров успешно связываются между источниками.")
            elif leftout_sales['matched_pct'] >= 50 or storage_sales['matched_pct'] >= 50:
                print("⚠️  Связь по штрихкоду: ЧАСТИЧНАЯ")
                print("   Есть значительное количество товаров, которые не связываются.")
                print("   Возможные причины: разные форматы, пробелы, лидирующие нули.")
            else:
                print("❌ Связь по штрихкоду: ПРОБЛЕМА")
                print("   Большинство товаров не связываются между источниками.")
                print("   Требуется проверка форматов данных и нормализации.")

def main():
    """Main entry point."""
    user_id = sys.argv[1] if len(sys.argv) > 1 else None
    shop_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not user_id:
        print("Использование: python apps/api/scripts/check_barcode_links.py <user_id> [shop_id]")
        sys.exit(1)
    
    print(f"Диагностика для user_id: {user_id}")
    if shop_id:
        print(f"Shop ID: {shop_id}")
    print()
    
    conn = get_connection()
    try:
        check_barcode_links(conn, user_id, shop_id)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
