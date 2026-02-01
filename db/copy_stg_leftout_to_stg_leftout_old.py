#!/usr/bin/env python3
"""
Одноразовый перенос: копирование строк из app.stg_leftout в app.stg_leftout_old по upload_batch_id.

Если left-out-report_old уже был загружен как "Остатки" и попал в app.stg_leftout,
этот скрипт копирует строки этого batch в app.stg_leftout_old, чтобы не перезагружать файл.
После копирования запустите populate: python db/populate_leftout_old_from_staging.py <batch_id>

Пример:
  python db/copy_stg_leftout_to_stg_leftout_old.py 733fa35d-cddd-45b4-8fb7-f64f3591a630

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
        print("Usage: python db/copy_stg_leftout_to_stg_leftout_old.py <upload_batch_id>")
        print("Example: python db/copy_stg_leftout_to_stg_leftout_old.py 733fa35d-cddd-45b4-8fb7-f64f3591a630")
        sys.exit(1)
    batch_id = sys.argv[1].strip()
    schema = get_schema()
    src = f"{schema}.stg_leftout"
    dst = f"{schema}.stg_leftout_old"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {dst} (user_id, upload_batch_id, barcode_raw, in_sale_raw, cost_raw, price_raw)
                SELECT
                    user_id,
                    upload_batch_id,
                    barcode_raw,
                    COALESCE(in_sale_raw::text, '0'),
                    NULL,
                    NULL
                FROM {src}
                WHERE upload_batch_id = %s::uuid
                """,
                (batch_id,),
            )
            inserted = cur.rowcount
        conn.commit()
        print(f"Copied {inserted} rows from {src} to {dst} for upload_batch_id={batch_id}")
        print(f"Next: python db/populate_leftout_old_from_staging.py {batch_id}")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
