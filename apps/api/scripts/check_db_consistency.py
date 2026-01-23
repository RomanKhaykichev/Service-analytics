#!/usr/bin/env python3
"""
Script to verify that API, Alembic, and import pipeline use the same database.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text
from urllib.parse import urlparse

settings = get_settings()

def parse_db_url(url: str):
    """Parse DATABASE_URL and return components."""
    parsed = urlparse(url.replace("postgresql+psycopg2://", "postgresql://"))
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") if parsed.path else None,
        "user": parsed.username,
    }

def check_import_pipeline_env():
    """Check if import pipeline env vars match DATABASE_URL."""
    print("=" * 60)
    print("Checking Import Pipeline Environment Variables")
    print("=" * 60)
    
    api_db = parse_db_url(settings.DATABASE_URL)
    
    import_host = os.getenv("PGHOST", "localhost")
    import_port = os.getenv("PGPORT", "5432")
    import_db = os.getenv("PGDATABASE")
    import_user = os.getenv("PGUSER")
    
    print(f"API DATABASE_URL:")
    print(f"  Host: {api_db['host']}")
    print(f"  Port: {api_db['port']}")
    print(f"  Database: {api_db['database']}")
    print(f"  User: {api_db['user']}")
    print()
    print(f"Import Pipeline (PGHOST/PGPORT/PGDATABASE/PGUSER):")
    print(f"  Host: {import_host}")
    print(f"  Port: {import_port}")
    print(f"  Database: {import_db}")
    print(f"  User: {import_user}")
    print()
    
    matches = (
        api_db['host'] == import_host and
        str(api_db['port']) == str(import_port) and
        api_db['database'] == import_db and
        api_db['user'] == import_user
    )
    
    if matches:
        print("✅ Import pipeline env vars match DATABASE_URL")
    else:
        print("❌ Import pipeline env vars DO NOT match DATABASE_URL!")
        print("   Recommendation: Set PGHOST, PGPORT, PGDATABASE, PGUSER to match DATABASE_URL")
    
    return matches

def check_database_tables():
    """Check if fact_sales and manual_expenses are in the same database."""
    print()
    print("=" * 60)
    print("Checking Database Tables")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Get current database
        db_result = conn.execute(text("SELECT current_database()"))
        db_name = db_result.scalar()
        print(f"Connected to database: {db_name}")
        print()
        
        # Check fact_sales locations
        fact_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'fact_sales'
            ORDER BY table_schema
        """)
        fact_result = conn.execute(fact_query)
        fact_locations = fact_result.fetchall()
        
        print(f"fact_sales table locations:")
        if fact_locations:
            for schema, table in fact_locations:
                print(f"  - {schema}.{table}")
        else:
            print("  ❌ NOT FOUND")
        print()
        
        # Check manual_expenses locations
        manual_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'manual_expenses'
            ORDER BY table_schema
        """)
        manual_result = conn.execute(manual_query)
        manual_locations = manual_result.fetchall()
        
        print(f"manual_expenses table locations:")
        if manual_locations:
            for schema, table in manual_locations:
                print(f"  - {schema}.{table}")
        else:
            print("  ❌ NOT FOUND")
        print()
        
        # Check if both exist in expected schema
        expected_schema = settings.DB_SCHEMA
        fact_in_schema = any(schema == expected_schema for schema, _ in fact_locations)
        manual_in_schema = any(schema == expected_schema for schema, _ in manual_locations)
        
        print(f"Expected schema: {expected_schema}")
        print(f"fact_sales in {expected_schema}: {'✅' if fact_in_schema else '❌'}")
        print(f"manual_expenses in {expected_schema}: {'✅' if manual_in_schema else '❌'}")
        print()
        
        # Check manual_expenses columns
        if manual_in_schema:
            columns_query = text(f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'manual_expenses'
                ORDER BY column_name
            """)
            columns_result = conn.execute(columns_query, {"schema": expected_schema})
            columns = columns_result.fetchall()
            
            print(f"manual_expenses columns in {expected_schema}:")
            for col_name, col_type in columns:
                print(f"  - {col_name} ({col_type})")
            
            has_shop_id = any(col[0] == 'shop_id' for col in columns)
            print()
            print(f"shop_id column exists: {'✅' if has_shop_id else '❌'}")
        
        return {
            "same_db": len(fact_locations) > 0 and len(manual_locations) > 0,
            "fact_in_schema": fact_in_schema,
            "manual_in_schema": manual_in_schema,
            "both_in_schema": fact_in_schema and manual_in_schema
        }

def main():
    """Run all checks."""
    print("=" * 60)
    print("Database Consistency Check")
    print("=" * 60)
    print()
    
    # Check API DATABASE_URL
    api_db = parse_db_url(settings.DATABASE_URL)
    print("API Configuration (from DATABASE_URL):")
    print(f"  Host: {api_db['host']}")
    print(f"  Port: {api_db['port']}")
    print(f"  Database: {api_db['database']}")
    print(f"  User: {api_db['user']}")
    print(f"  Schema: {settings.DB_SCHEMA}")
    print()
    
    # Check import pipeline
    import_matches = check_import_pipeline_env()
    
    # Check tables
    table_info = check_database_tables()
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_ok = (
        import_matches and
        table_info["same_db"] and
        table_info["both_in_schema"]
    )
    
    if all_ok:
        print("✅ All checks passed! API, Alembic, and imports use the same database.")
    else:
        print("❌ Issues found:")
        if not import_matches:
            print("  - Import pipeline env vars don't match DATABASE_URL")
        if not table_info["same_db"]:
            print("  - fact_sales and manual_expenses are not in the same database")
        if not table_info["both_in_schema"]:
            print(f"  - Tables are not both in schema '{settings.DB_SCHEMA}'")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
