#!/usr/bin/env python3
"""
Скрипт для удаления данных seller-storage с пустым/NULL магазином ("не определено") из БД.

ВАЖНО: Перед запуском сделайте бэкап БД!
Удаляет ТОЛЬКО данные seller-storage (stg_storage и fact_storage_snapshot).
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


def get_user_id():
    """Get user_id from environment or prompt."""
    user_id = os.getenv("USER_ID")
    if not user_id:
        print("\nВНИМАНИЕ: USER_ID не указан в переменных окружения.")
        print("Укажите user_id для удаления данных.")
        user_id = input("user_id (UUID): ").strip()
        if not user_id:
            raise ValueError("user_id обязателен для выполнения скрипта")
    return user_id


def diagnose_storage_undefined_shops(conn, schema: str, user_id: str):
    """Диагностика: подсчет строк seller-storage с пустым/NULL магазином."""
    print("\n" + "="*80)
    print("ДИАГНОСТИКА: Подсчет строк seller-storage с пустым/NULL магазином")
    print("="*80)
    print(f"user_id: {user_id}")
    
    results = {}
    
    # Условие "не определено"
    undefined_condition = """
        shop_raw IS NULL 
        OR TRIM(COALESCE(shop_raw, '')) = ''
        OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
    """
    
    # 1. stg_storage: shop_raw пустое/NULL или "не определено"
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(*) FILTER (WHERE shop_raw IS NULL OR TRIM(COALESCE(shop_raw, '')) = '') as null_or_empty,
                COUNT(*) FILTER (WHERE lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')) as undefined_string,
                COUNT(*) FILTER (WHERE {undefined_condition}) as total_undefined
            FROM {schema}.stg_storage
            WHERE user_id = CAST(:user_id AS uuid)
        """, {"user_id": user_id})
        row = cur.fetchone()
        results['stg_storage'] = {
            'total': row['total_rows'],
            'null_or_empty': row['null_or_empty'],
            'undefined_string': row['undefined_string'],
            'total_undefined': row['total_undefined']
        }
        print(f"\n1. stg_storage:")
        print(f"   Всего строк для user_id: {row['total_rows']}")
        print(f"   shop_raw IS NULL или пустое: {row['null_or_empty']}")
        print(f"   shop_raw = 'не определено' и т.д.: {row['undefined_string']}")
        print(f"   ИТОГО к удалению: {row['total_undefined']}")
        
        # Показать примеры значений shop_raw
        cur.execute(f"""
            SELECT DISTINCT shop_raw, COUNT(*) as cnt
            FROM {schema}.stg_storage
            WHERE user_id = CAST(:user_id AS uuid)
              AND ({undefined_condition})
            GROUP BY shop_raw
            ORDER BY cnt DESC
            LIMIT 20
        """, {"user_id": user_id})
        examples = cur.fetchall()
        if examples:
            print(f"   Примеры значений shop_raw:")
            for ex in examples:
                shop_val = ex['shop_raw'] if ex['shop_raw'] is not None else 'NULL'
                print(f"     '{shop_val}': {ex['cnt']} строк")
        else:
            print(f"   Примеры значений shop_raw: нет")
    
    # 2. fact_storage_snapshot: shop_id ссылается на "не определено" через dim_shop
    with conn.cursor() as cur:
        # Сначала найдем shop_id для "не определено"
        cur.execute(f"""
            SELECT shop_id, shop_name
            FROM {schema}.dim_shop
            WHERE user_id = CAST(:user_id AS uuid)
              AND lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
        """, {"user_id": user_id})
        undefined_shops = cur.fetchall()
        undefined_shop_ids = [s['shop_id'] for s in undefined_shops]
        
        if undefined_shop_ids:
            cur.execute(f"""
                SELECT COUNT(*) as total_rows
                FROM {schema}.fact_storage_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  AND shop_id = ANY(%s)
            """, (undefined_shop_ids,))
            row = cur.fetchone()
            results['fact_storage_snapshot'] = {
                'total_undefined': row['total_rows'],
                'undefined_shops': undefined_shops
            }
            print(f"\n2. fact_storage_snapshot:")
            print(f"   Строк с shop_id 'не определено': {row['total_rows']}")
            print(f"   Магазины 'не определено':")
            for shop in undefined_shops:
                print(f"     shop_id={shop['shop_id']}, shop_name='{shop['shop_name']}'")
        else:
            results['fact_storage_snapshot'] = {
                'total_undefined': 0,
                'undefined_shops': []
            }
            print(f"\n2. fact_storage_snapshot:")
            print(f"   Строк с shop_id 'не определено': 0 (нет магазинов 'не определено' в dim_shop)")
    
    # 3. Проверка upload_batch_id для удаления "мусорных" батчей
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT upload_batch_id, COUNT(*) as row_count
            FROM {schema}.stg_storage
            WHERE user_id = CAST(:user_id AS uuid)
              AND ({undefined_condition})
            GROUP BY upload_batch_id
            ORDER BY row_count DESC
            LIMIT 10
        """, {"user_id": user_id})
        undefined_batches = cur.fetchall()
        results['undefined_batches'] = undefined_batches
        print(f"\n3. upload_batch_id с пустым магазином:")
        if undefined_batches:
            print(f"   Найдено батчей: {len(undefined_batches)}")
            for batch in undefined_batches[:10]:
                print(f"     upload_batch_id={batch['upload_batch_id']}: {batch['row_count']} строк")
        else:
            print(f"   Батчей с пустым магазином: 0")
    
    print("\n" + "="*80)
    return results


def delete_storage_undefined_shops(conn, schema: str, user_id: str, dry_run: bool = True):
    """Удаление данных seller-storage с пустым/NULL магазином."""
    print("\n" + "="*80)
    if dry_run:
        print("РЕЖИМ ПРОВЕРКИ (DRY RUN): Показываем SQL без выполнения")
    else:
        print("УДАЛЕНИЕ: Удаляем данные seller-storage с пустым/NULL магазином")
    print("="*80)
    
    # Условие "не определено"
    undefined_condition = """
        shop_raw IS NULL 
        OR TRIM(COALESCE(shop_raw, '')) = ''
        OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
    """
    
    # Получаем список shop_id для "не определено"
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT shop_id, shop_name
            FROM {schema}.dim_shop
            WHERE user_id = CAST(:user_id AS uuid)
              AND lower(TRIM(shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
        """, {"user_id": user_id})
        undefined_shops = cur.fetchall()
        undefined_shop_ids = [s['shop_id'] for s in undefined_shops]
    
    # SQL запросы для удаления
    queries = []
    
    # 1. Удалить из fact_storage_snapshot
    if undefined_shop_ids:
        queries.append({
            'table': 'fact_storage_snapshot',
            'sql': f"""
                DELETE FROM {schema}.fact_storage_snapshot
                WHERE user_id = CAST(:user_id AS uuid)
                  AND shop_id = ANY(%s)
            """,
            'params': (undefined_shop_ids,),
            'description': 'Удаление из fact_storage_snapshot по shop_id "не определено"'
        })
    
    # 2. Удалить из stg_storage (по shop_raw)
    queries.append({
        'table': 'stg_storage',
        'sql': f"""
            DELETE FROM {schema}.stg_storage
            WHERE user_id = CAST(:user_id AS uuid)
              AND ({undefined_condition})
        """,
        'params': None,
        'description': 'Удаление из stg_storage по shop_raw пустое/NULL/не определено'
    })
    
    # Выполняем запросы
    deleted_counts = {}
    
    if dry_run:
        print("\nSQL запросы для выполнения:")
        for i, q in enumerate(queries, 1):
            print(f"\n{i}. {q['table']} ({q['description']}):")
            print(f"   {q['sql']}")
            if q['params']:
                print(f"   Параметры: {q['params']}")
    else:
        print("\nВыполняем удаление в транзакции...")
        try:
            with conn.cursor() as cur:
                for q in queries:
                    if q['params']:
                        # Для fact_storage_snapshot используем shop_id массив
                        cur.execute(q['sql'], {"user_id": user_id}, q['params'])
                    else:
                        cur.execute(q['sql'], {"user_id": user_id})
                    deleted_counts[q['table']] = cur.rowcount
                    print(f"   {q['table']}: удалено {cur.rowcount} строк")
            
            conn.commit()
            print("\n[OK] Транзакция успешно завершена.")
        except Exception as e:
            conn.rollback()
            print(f"\n[ERROR] Ошибка при удалении: {e}")
            raise
    
    return deleted_counts


def verify_deletion(conn, schema: str, user_id: str):
    """Проверка после удаления."""
    print("\n" + "="*80)
    print("ПРОВЕРКА: Подсчет строк после удаления")
    print("="*80)
    
    undefined_condition = """
        shop_raw IS NULL 
        OR TRIM(COALESCE(shop_raw, '')) = ''
        OR lower(TRIM(COALESCE(shop_raw, ''))) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
    """
    
    # Проверяем stg_storage
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) as count
            FROM {schema}.stg_storage
            WHERE user_id = CAST(:user_id AS uuid)
              AND ({undefined_condition})
        """, {"user_id": user_id})
        row = cur.fetchone()
        print(f"\nstg_storage с пустым магазином: {row['count']} (должно быть 0)")
    
    # Проверяем fact_storage_snapshot
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT COUNT(*) as count
            FROM {schema}.fact_storage_snapshot fss
            WHERE fss.user_id = CAST(:user_id AS uuid)
              AND EXISTS (
                  SELECT 1 FROM {schema}.dim_shop ds
                  WHERE ds.shop_id = fss.shop_id
                    AND ds.user_id = CAST(:user_id AS uuid)
                    AND lower(TRIM(ds.shop_name)) IN ('не определено', 'неопределено', 'undefined', 'null', '(не определено)', 'не определен')
              )
        """, {"user_id": user_id})
        row = cur.fetchone()
        print(f"fact_storage_snapshot с shop_id 'не определено': {row['count']} (должно быть 0)")
    
    print("\n" + "="*80)


def main():
    """Главная функция."""
    print("="*80)
    print("СКРИПТ УДАЛЕНИЯ ДАННЫХ SELLER-STORAGE С ПУСТЫМ/NULL МАГАЗИНОМ")
    print("="*80)
    print("\nВАЖНО: Перед запуском сделайте бэкап БД!")
    print("Этот скрипт удалит данные seller-storage с пустым/NULL магазином.")
    
    schema = get_schema()
    print(f"\nСхема БД: {schema}")
    
    user_id = get_user_id()
    print(f"user_id: {user_id}")
    
    # Подключение к БД
    try:
        conn = get_connection()
        print("[OK] Подключение к БД успешно")
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к БД: {e}")
        sys.exit(1)
    
    try:
        # Диагностика
        results = diagnose_storage_undefined_shops(conn, schema, user_id)
        
        # Проверяем, есть ли что удалять
        total_to_delete = (
            results.get('stg_storage', {}).get('total_undefined', 0) +
            results.get('fact_storage_snapshot', {}).get('total_undefined', 0)
        )
        
        if total_to_delete == 0:
            print("\n[OK] Нет данных для удаления. Выход.")
            return
        
        # Показываем SQL без выполнения
        print("\n" + "="*80)
        print("ШАГ 1: Показываем SQL запросы (DRY RUN)")
        print("="*80)
        delete_storage_undefined_shops(conn, schema, user_id, dry_run=True)
        
        # Запрашиваем подтверждение
        print("\n" + "="*80)
        print("ПОДТВЕРЖДЕНИЕ")
        print("="*80)
        print(f"\nБудет удалено примерно:")
        print(f"  - stg_storage: {results.get('stg_storage', {}).get('total_undefined', 0)} строк")
        print(f"  - fact_storage_snapshot: {results.get('fact_storage_snapshot', {}).get('total_undefined', 0)} строк")
        
        response = input("\nПродолжить удаление? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\nОтменено пользователем.")
            return
        
        # Выполняем удаление
        print("\n" + "="*80)
        print("ШАГ 2: Выполняем удаление")
        print("="*80)
        deleted_counts = delete_storage_undefined_shops(conn, schema, user_id, dry_run=False)
        
        # Проверка после удаления
        verify_deletion(conn, schema, user_id)
        
        print("\n" + "="*80)
        print("[OK] ГОТОВО: Удаление завершено успешно")
        print("="*80)
        print("\nСледующие шаги:")
        print("1. Проверьте эндпоинты:")
        print("   - GET /api/shops -> не должно быть 'не определено' из seller-storage")
        print("   - GET /api/kpi/summary?period=30d -> должен возвращать 200")
        print("2. Пользователь может заново загрузить файлы seller-storage")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
