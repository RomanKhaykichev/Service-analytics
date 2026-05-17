"""Check alembic revision vs tables in DB."""
from pathlib import Path
import re
from sqlalchemy import text
from app.db import SessionLocal
from app.settings import get_settings

HEAD_REVISION = "20260413_engagement"

def main():
    s = get_settings()
    db = SessionLocal()
    schema = s.DB_SCHEMA

    print("Database:", (s.DATABASE_URL or "").split("@")[-1])
    print("Schema:", schema)

    try:
        rows = db.execute(text(f"SELECT version_num FROM {schema}.alembic_version")).fetchall()
        current = rows[-1][0] if rows else None
        if len(rows) > 1:
            print("alembic_version rows:", [r[0] for r in rows])
        col = db.execute(
            text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_schema = :s AND table_name = 'alembic_version' AND column_name = 'version_num'"
            ),
            {"s": schema},
        ).fetchone()
        if col:
            print("version_num max length:", col[0])
    except Exception as e:
        current = None
        print("alembic_version error:", e)

    print("Current revision:", current, f"(len={len(current) if current else 0})")
    print("Expected head:", HEAD_REVISION)
    print("At head:", current == HEAD_REVISION)

    all_tables = db.execute(
        text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_name IN ('import_file_attempts', 'pending_registrations')"
        )
    ).fetchall()
    if all_tables:
        print("\nExtra tables lookup:", all_tables)

    tables = [
        "login_events",
        "training_page_views",
        "tariff_payment_opens",
        "landing_visits",
        "promo_try_clicks",
        "import_file_attempts",
        "support_tickets",
    ]
    print("\nTables:")
    for t in tables:
        r = db.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = :s AND table_name = :t"
            ),
            {"s": schema, "t": t},
        ).fetchone()
        print(f"  {t}: {'OK' if r else 'MISSING'}")

    db.close()


if __name__ == "__main__":
    main()
