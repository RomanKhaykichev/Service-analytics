#!/usr/bin/env python3
"""
Скрипт для удаления данных с пустым/NULL магазином ("не определено") из БД.

ВАЖНО: Перед запуском сделайте бэкап БД!
"""

import os
import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")
load_dotenv(project_root / "apps" / "api" / ".env")


def get_connection():
    """Get database connection from environment variables."""
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "service_analytics")
    user = os.getenv("PGUSER", "postgres")
    pwd = os.getenv("PGPASSWORD", "postgres")
    
    conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return psycopg.connect(conn_str, row_factory=dict_row)


def get_schema():
    """Get database schema name."""
    return os.getenv("DB_SCHEMA", "app")


def diagnose_undefined_shops(conn, schema: str):
    """Диагностика: подсчет строк с пустым/NULL магазином."""
    print("\n" + "="*80)
    print("ДИАГНОСТИКА: Подсчет строк с пустым/NULL магазином")
    print("="*80)
    
    results = {}
    
    # 1. stg_leftout: shop_raw пустое/NULL или "не определено"
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(*) FILTER (WHERE shop_raw IS NULL OR TRIM(COALESCE(shop_raw, '')) = '') as null_or_empty,
                COUNT(*) FILTER (WHERE lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')) as undefined_string
            FROM {schema}.stg_leftout
        """)
        row = cur.fetchone()
        results['stg_leftout'] = {
            'total': row['total_rows'],
            'null_or_empty': row['null_or_empty'],
            'undefined_string': row['undefined_string'],
            'total_undefined': row['null_or_empty'] + row['undefined_string']
        }
        print(f"\n1. stg_leftout:")
        print(f"   Всего строк: {row['total_rows']}")
        print(f"   shop_raw IS NULL или пустое: {row['null_or_empty']}")
        print(f"   shop_raw = 'не определено' и т.д.: {row['undefined_string']}")
        print(f"   ИТОГО к удалению: {row['null_or_empty'] + row['undefined_string']}")
        
        # Показать примеры значений shop_raw
        cur.execute(f"""
            SELECT DISTINCT shop_raw, COUNT(*) as cnt
            FROM {schema}.stg_leftout
            WHERE shop_raw IS NULL 
               OR TRIM(COALESCE(shop_raw, '')) = ''
               OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
            GROUP BY shop_raw
            ORDER BY cnt DESC
            LIMIT 10
        """)
        examples = cur.fetchall()
        if examples:
            print(f"   Примеры значений shop_raw:")
            for ex in examples:
                shop_val = ex['shop_raw'] if ex['shop_raw'] is not None else 'NULL'
                print(f"     '{shop_val}': {ex['cnt']} строк")
    
    # 2. dim_shop: shop_name = "не определено" и т.д.
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                shop_id,
                shop_name,
                user_id,
                COUNT(*) OVER() as total_count
            FROM {schema}.dim_shop
            WHERE lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
            ORDER BY shop_name
            LIMIT 20
        """)
        undefined_shops = cur.fetchall()
        results['dim_shop'] = {
            'undefined_shops': undefined_shops,
            'count': len(undefined_shops) if undefined_shops else 0
        }
        print(f"\n2. dim_shop:")
        if undefined_shops:
            total_count = undefined_shops[0]['total_count'] if undefined_shops else 0
            print(f"   Магазинов 'не определено': {total_count}")
            print(f"   Примеры (первые 20):")
            for shop in undefined_shops[:20]:
                print(f"     shop_id={shop['shop_id']}, shop_name='{shop['shop_name']}', user_id={shop['user_id']}")
        else:
            print(f"   Магазинов 'не определено': 0")
    
    # 3. fact_leftout_snapshot: shop_id ссылается на "не определено"
    if results['dim_shop']['undefined_shops']:
        undefined_shop_ids = [s['shop_id'] for s in results['dim_shop']['undefined_shops']]
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) as total_rows
                FROM {schema}.fact_leftout_snapshot
                WHERE shop_id = ANY(%s)
            """, (undefined_shop_ids,))
            row = cur.fetchone()
            results['fact_leftout_snapshot'] = {
                'total_undefined': row['total_rows']
            }
            print(f"\n3. fact_leftout_snapshot:")
            print(f"   Строк с shop_id 'не определено': {row['total_rows']}")
    else:
        results['fact_leftout_snapshot'] = {'total_undefined': 0}
        print(f"\n3. fact_leftout_snapshot:")
        print(f"   Строк с shop_id 'не определено': 0")
    
    # 4. map_shop_sku: shop_id ссылается на "не определено"
    if results['dim_shop']['undefined_shops']:
        undefined_shop_ids = [s['shop_id'] for s in results['dim_shop']['undefined_shops']]
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) as total_rows
                FROM {schema}.map_shop_sku
                WHERE shop_id = ANY(%s)
            """, (undefined_shop_ids,))
            row = cur.fetchone()
            results['map_shop_sku'] = {
                'total_undefined': row['total_rows']
            }
            print(f"\n4. map_shop_sku:")
            print(f"   Строк с shop_id 'не определено': {row['total_rows']}")
    else:
        results['map_shop_sku'] = {'total_undefined': 0}
        print(f"\n4. map_shop_sku:")
        print(f"   Строк с shop_id 'не определено': 0")
    
    # 5. fact_storage_snapshot (если есть): shop_id ссылается на "не определено"
    if results['dim_shop']['undefined_shops']:
        undefined_shop_ids = [s['shop_id'] for s in results['dim_shop']['undefined_shops']]
        with conn.cursor() as cur:
            # Проверим, существует ли таблица
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = 'fact_storage_snapshot'
                )
            """, (schema,))
            table_exists = cur.fetchone()['exists']
            
            if table_exists:
                cur.execute(f"""
                    SELECT COUNT(*) as total_rows
                    FROM {schema}.fact_storage_snapshot
                    WHERE shop_id = ANY(%s)
                """, (undefined_shop_ids,))
                row = cur.fetchone()
                results['fact_storage_snapshot'] = {
                    'total_undefined': row['total_rows']
                }
                print(f"\n5. fact_storage_snapshot:")
                print(f"   Строк с shop_id 'не определено': {row['total_rows']}")
            else:
                results['fact_storage_snapshot'] = {'total_undefined': 0}
                print(f"\n5. fact_storage_snapshot:")
                print(f"   Таблица не существует")
    
    print("\n" + "="*80)
    return results


def delete_undefined_shops(conn, schema: str, dry_run: bool = True):
    """Удаление данных с пустым/NULL магазином."""
    print("\n" + "="*80)
    if dry_run:
        print("РЕЖИМ ПРОВЕРКИ (DRY RUN): Показываем SQL без выполнения")
    else:
        print("УДАЛЕНИЕ: Удаляем данные с пустым/NULL магазином")
    print("="*80)
    
    # Получаем список shop_id для "не определено"
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT shop_id, shop_name, user_id
            FROM {schema}.dim_shop
            WHERE lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
        """)
        undefined_shops = cur.fetchall()
        undefined_shop_ids = [s['shop_id'] for s in undefined_shops]
    
    if not undefined_shops:
        print("\nНет магазинов 'не определено' для удаления.")
        return
    
    print(f"\nНайдено {len(undefined_shops)} магазинов 'не определено' для удаления.")
    
    # SQL запросы для удаления
    queries = []
    
    # 1. Удалить из fact_leftout_snapshot
    if undefined_shop_ids:
        queries.append({
            'table': 'fact_leftout_snapshot',
            'sql': f"""
                DELETE FROM {schema}.fact_leftout_snapshot
                WHERE shop_id = ANY(%s)
            """,
            'params': (undefined_shop_ids,)
        })
    
    # 2. Удалить из map_shop_sku
    if undefined_shop_ids:
        queries.append({
            'table': 'map_shop_sku',
            'sql': f"""
                DELETE FROM {schema}.map_shop_sku
                WHERE shop_id = ANY(%s)
            """,
            'params': (undefined_shop_ids,)
        })
    
    # 3. Удалить из fact_storage_snapshot (если существует)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'fact_storage_snapshot'
            )
        """, (schema,))
        table_exists = cur.fetchone()['exists']
        
        if table_exists and undefined_shop_ids:
            queries.append({
                'table': 'fact_storage_snapshot',
                'sql': f"""
                    DELETE FROM {schema}.fact_storage_snapshot
                    WHERE shop_id = ANY(%s)
                """,
                'params': (undefined_shop_ids,)
            })
    
    # 4. Удалить из stg_leftout (по shop_raw)
    queries.append({
        'table': 'stg_leftout',
        'sql': f"""
            DELETE FROM {schema}.stg_leftout
            WHERE shop_raw IS NULL 
               OR TRIM(COALESCE(shop_raw, '')) = ''
               OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
        """,
        'params': None
    })
    
    # 5. Удалить из dim_shop (сам магазин "не определено")
    queries.append({
        'table': 'dim_shop',
        'sql': f"""
            DELETE FROM {schema}.dim_shop
            WHERE lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
        """,
        'params': None
    })
    
    # Выполняем запросы
    deleted_counts = {}
    
    if dry_run:
        print("\nSQL запросы для выполнения:")
        for i, q in enumerate(queries, 1):
            print(f"\n{i}. {q['table']}:")
            print(f"   {q['sql']}")
            if q['params']:
                print(f"   Параметры: {q['params']}")
    else:
        print("\nВыполняем удаление в транзакции...")
        try:
            with conn.cursor() as cur:
                for q in queries:
                    if q['params']:
                        cur.execute(q['sql'], q['params'])
                    else:
                        cur.execute(q['sql'])
                    deleted_counts[q['table']] = cur.rowcount
                    print(f"   {q['table']}: удалено {cur.rowcount} строк")
            
            conn.commit()
            print("\n[OK] Транзакция успешно завершена.")
        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] Ошибка при удалении: {e}")
            raise
    
    return deleted_counts


def verify_deletion(conn, schema: str):
    """Проверка после удаления."""
    print("\n" + "="*80)
    print("ПРОВЕРКА: Подсчет строк после удаления")
    print("="*80)
    
    # Проверяем dim_shop
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) as count
            FROM {schema}.dim_shop
            WHERE lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
        """)
        row = cur.fetchone()
        print(f"\ndim_shop с 'не определено': {row['count']} (должно быть 0)")
    
    # Проверяем stg_leftout
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) as count
            FROM {schema}.stg_leftout
            WHERE shop_raw IS NULL 
               OR TRIM(COALESCE(shop_raw, '')) = ''
               OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)')
        """)
        row = cur.fetchone()
        print(f"stg_leftout с пустым магазином: {row['count']} (должно быть 0)")
    
    print("\n" + "="*80)


def main():
    """Главная функция."""
    print("="*80)
    print("СКРИПТ УДАЛЕНИЯ ДАННЫХ С ПУСТЫМ/NULL МАГАЗИНОМ")
    print("="*80)
    print("\nВАЖНО: Перед запуском сделайте бэкап БД!")
    print("Этот скрипт удалит все данные, относящиеся к магазину 'не определено'.")
    
    schema = get_schema()
    print(f"\nСхема БД: {schema}")
    
    # Подключение к БД
    try:
        conn = get_connection()
        print("[OK] Подключение к БД успешно")
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    try:
        # Диагностика
        results = diagnose_undefined_shops(conn, schema)
        
        # Проверяем, есть ли что удалять
        total_to_delete = (
            results.get('stg_leftout', {}).get('total_undefined', 0) +
            results.get('fact_leftout_snapshot', {}).get('total_undefined', 0) +
            results.get('map_shop_sku', {}).get('total_undefined', 0) +
            results.get('fact_storage_snapshot', {}).get('total_undefined', 0) +
            results.get('dim_shop', {}).get('count', 0)
        )
        
        if total_to_delete == 0:
            print("\n[OK] Нет данных для удаления. Выход.")
            return
        
        # Показываем SQL без выполнения
        print("\n" + "="*80)
        print("ШАГ 1: Показываем SQL запросы (DRY RUN)")
        print("="*80)
        delete_undefined_shops(conn, schema, dry_run=True)
        
        # Запрашиваем подтверждение
        print("\n" + "="*80)
        print("ПОДТВЕРЖДЕНИЕ")
        print("="*80)
        print(f"\nБудет удалено примерно:")
        print(f"  - stg_leftout: {results.get('stg_leftout', {}).get('total_undefined', 0)} строк")
        print(f"  - fact_leftout_snapshot: {results.get('fact_leftout_snapshot', {}).get('total_undefined', 0)} строк")
        print(f"  - map_shop_sku: {results.get('map_shop_sku', {}).get('total_undefined', 0)} строк")
        print(f"  - fact_storage_snapshot: {results.get('fact_storage_snapshot', {}).get('total_undefined', 0)} строк")
        print(f"  - dim_shop: {results.get('dim_shop', {}).get('count', 0)} магазинов")
        
        response = input("\nПродолжить удаление? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\nОтменено пользователем.")
            return
        
        # Выполняем удаление
        print("\n" + "="*80)
        print("ШАГ 2: Выполняем удаление")
        print("="*80)
        deleted_counts = delete_undefined_shops(conn, schema, dry_run=False)
        
        # Проверка после удаления
        verify_deletion(conn, schema)
        
        print("\n" + "="*80)
        print("[OK] ГОТОВО: Удаление завершено успешно")
        print("="*80)
        print("\nСледующие шаги:")
        print("1. Проверьте эндпоинты:")
        print("   - GET /api/shops -> не должно быть 'не определено'")
        print("   - GET /api/kpi/summary?period=30d -> должен возвращать 200")
        print("2. Пользователь может заново загрузить файлы")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
