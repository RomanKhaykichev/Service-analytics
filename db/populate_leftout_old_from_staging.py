#!/usr/bin/env python3
"""
Бэкфилл fact_leftout_old_snapshot из stg_leftout_old по upload_batch_id.

Используется, если после импорта "Остатки (старый формат)" данные попали
в app.stg_leftout_old, но populate не выполнился и app.fact_leftout_old_snapshot пустой.

Пример:
  python db/populate_leftout_old_from_staging.py 733fa35d-cddd-45b4-8fb7-f64f3591a630

Переменные окружения: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, DB_SCHEMA (по умолчанию app).
"""

import os
import sys
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")
load_dotenv(project_root / "apps" / "api" / ".env")


def get_connection():
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE", "service_analytics")
    user = os.getenv("PGUSER", "postgres")
    pwd = os.getenv("PGPASSWORD", "postgres")
    conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return psycopg.connect(conn_str, row_factory=dict_row)


def get_schema():
    return os.getenv("DB_SCHEMA", "app")


def main():
    if len(sys.argv) < 2:
        print("Usage: python db/populate_leftout_old_from_staging.py <upload_batch_id>")
        print("Example: python db/populate_leftout_old_from_staging.py 733fa35d-cddd-45b4-8fb7-f64f3591a630")
        sys.exit(1)
    batch_id = sys.argv[1].strip()
    schema = get_schema()
    stg = f"{schema}.stg_leftout_old"
    fact = f"{schema}.fact_leftout_old_snapshot"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1) Проверка: есть ли строки в stg по этому batch_id
            cur.execute(
                f"SELECT user_id, COUNT(*) AS cnt FROM {stg} WHERE upload_batch_id = %s::uuid GROUP BY user_id",
                (batch_id,),
            )
            row = cur.fetchone()
            if not row:
                print(f"No rows in {stg} for upload_batch_id = {batch_id}")
                sys.exit(2)
            user_id = str(row["user_id"])
            stg_count = row["cnt"]
            print(f"Found user_id={user_id}, rows in {stg}: {stg_count}")

            # 2) Удалить старые данные в fact по этому user_id и batch_id
            cur.execute(
                f"DELETE FROM {fact} WHERE user_id = %s::uuid AND upload_batch_id = %s::uuid",
                (user_id, batch_id),
            )
            deleted = cur.rowcount
            if deleted:
                print(f"Deleted {deleted} existing rows from {fact}")

            # 3) INSERT из stg в fact (та же логика, что в populate_facts(inventory_old))
            cur.execute(
                f"""
                INSERT INTO {fact} (
                    user_id, upload_batch_id, barcode, barcode_norm, in_sale_qty, cost_sum, price_sum, loaded_at
                )
                SELECT
                    sl.user_id,
                    sl.upload_batch_id,
                    NULLIF(trim(sl.barcode_raw), '') AS barcode,
                    NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') AS barcode_norm,
                    GREATEST(0, COALESCE(CAST(NULLIF(regexp_replace(regexp_replace(trim(COALESCE(sl.in_sale_raw, '')), '\\s+', '', 'g'), ',', '', 'g'), '') AS int), 0)) AS in_sale_qty,
                    CAST(NULLIF(replace(regexp_replace(trim(COALESCE(sl.cost_raw, '')), '\\s+', '', 'g'), ',', '.'), '') AS numeric(18,2)) AS cost_sum,
                    CAST(NULLIF(replace(regexp_replace(trim(COALESCE(sl.price_raw, '')), '\\s+', '', 'g'), ',', '.'), '') AS numeric(18,2)) AS price_sum,
                    now() AS loaded_at
                FROM {stg} sl
                WHERE sl.user_id = %s::uuid AND sl.upload_batch_id = %s::uuid
                  AND NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') IS NOT NULL
                  AND NULLIF(trim(regexp_replace(COALESCE(sl.barcode_raw, ''), '\\s+', '', 'g')), '') != ''
                """,
                (user_id, batch_id),
            )
            inserted = cur.rowcount
        conn.commit()
        print(f"Inserted {inserted} rows into {fact}")
        print(f"Check: SELECT COUNT(*) FROM {fact} WHERE upload_batch_id = '{batch_id}'::uuid;  -- expected {inserted}+")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
