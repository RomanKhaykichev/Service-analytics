#!/usr/bin/env python3
"""
Database schema check script.
Verifies that critical tables exist before running imports.

Usage:
    python scripts/check_db.py
    # Or from project root:
    python apps/api/scripts/check_db.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
script_dir = Path(__file__).parent
api_dir = script_dir.parent
sys.path.insert(0, str(api_dir))

from sqlalchemy import create_engine, text
from app.settings import get_settings
from app.db import qname

settings = get_settings()


def check_table_exists(engine, schema: str, table_name: str) -> bool:
    """Check if a table exists in the database."""
    try:
        with engine.connect() as conn:
            # Use PostgreSQL-specific function to check table existence
            result = conn.execute(
                text(f"SELECT to_regclass('{schema}.{table_name}')")
            )
            regclass = result.scalar()
            return regclass is not None
    except Exception as e:
        print(f"❌ Error checking table {schema}.{table_name}: {e}")
        return False


def main():
    """Check critical database tables."""
    print("=" * 60)
    print("Service Analytics - Database Schema Check")
    print("=" * 60)
    
    # Parse DATABASE_URL to show connection info (without password)
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
    
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    print(f"Database: {parsed.hostname or 'localhost'}:{parsed.port or 5432}")
    print(f"Schema: {settings.DB_SCHEMA}")
    print()
    
    # Create engine
    try:
        engine = create_engine(settings.DATABASE_URL)
    except Exception as e:
        print(f"❌ Failed to create database engine: {e}")
        return 1
    
    # Critical tables to check
    critical_tables = [
        "map_shop_barcode",  # Most critical - causes import failures
        "manual_expenses",
        "fact_sales",
        "fact_expenses",
        "dim_shop",
    ]
    
    schema = settings.DB_SCHEMA
    all_ok = True
    
    print("Checking critical tables...")
    print()
    
    for table_name in critical_tables:
        exists = check_table_exists(engine, schema, table_name)
        if exists:
            print(f"✅ {schema}.{table_name} - exists")
        else:
            print(f"❌ {schema}.{table_name} - MISSING!")
            all_ok = False
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ All critical tables exist!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some critical tables are missing!")
        print()
        print("To fix this, run migrations:")
        print("  python -m alembic upgrade head")
        print("  # Or use scripts:")
        print("  .\\scripts\\migrate.ps1  (Windows)")
        print("  ./scripts/migrate.sh     (Linux/Mac)")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
