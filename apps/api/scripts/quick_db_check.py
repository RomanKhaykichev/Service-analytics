"""Quick DB sanity check."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = os.environ.get("DATABASE_URL")
if not url:
    print("DATABASE_URL missing")
    sys.exit(1)

engine = create_engine(url, connect_args={"connect_timeout": 8})
queries = [
    ("users", "SELECT count(*) FROM app.users"),
    ("fact_sales", "SELECT count(*) FROM app.fact_sales"),
    ("fact_storage", "SELECT count(*) FROM app.fact_storage_snapshot"),
    (
        "user_c2e4",
        "SELECT email, plan, allowed_shops "
        "FROM app.users WHERE id = 'c2e4bdf4-83bc-4aba-8966-42d5454d65c4'::uuid",
    ),
    (
        "user_c2e4_sales",
        "SELECT count(*) FROM app.fact_sales "
        "WHERE user_id = 'c2e4bdf4-83bc-4aba-8966-42d5454d65c4'::uuid",
    ),
    (
        "user_c2e4_sales_dates",
        "SELECT min(date_created), max(date_created), count(*) FROM app.fact_sales "
        "WHERE user_id = 'c2e4bdf4-83bc-4aba-8966-42d5454d65c4'::uuid",
    ),
]
with engine.connect() as conn:
    for name, sql in queries:
        try:
            rows = conn.execute(text(sql)).fetchall()
            print(name, rows)
        except Exception as exc:
            print(name, "ERROR", exc)
