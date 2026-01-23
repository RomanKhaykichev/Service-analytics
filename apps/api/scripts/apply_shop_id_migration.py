#!/usr/bin/env python3
"""
Script to diagnose and apply shop_id migration to manual_expenses.
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

def print_db_info():
    """Print database connection info."""
    parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"))
    print("=" * 60)
    print("Database Connection Info (from DATABASE_URL):")
    print(f"  Host: {parsed.hostname or 'localhost'}")
    print(f"  Port: {parsed.port or 5432}")
    print(f"  Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
    print(f"  User: {parsed.username or 'N/A'}")
    print(f"  Schema: {settings.DB_SCHEMA}")
    print("=" * 60)
    print()

def diagnose_before_migration():
    """Run diagnostic queries before migration."""
    print("=" * 60)
    print("DIAGNOSTIC: Before Migration")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        # 1. Current database and schema
        db_info_query = text("""
            SELECT 
                current_database() as db,
                current_schema() as schema,
                (SELECT setting FROM pg_settings WHERE name = 'search_path') as search_path
        """)
        db_info = conn.execute(db_info_query).fetchone()
        print(f"1. Current database: {db_info[0]}")
        print(f"   Current schema: {db_info[1]}")
        print(f"   Search path: {db_info[2]}")
        print()
        
        # 2. Where is manual_expenses table
        table_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'manual_expenses'
            ORDER BY table_schema
        """)
        table_locations = conn.execute(table_query).fetchall()
        print(f"2. manual_expenses table locations:")
        if table_locations:
            for schema, table in table_locations:
                print(f"   - {schema}.{table}")
        else:
            print("   ❌ NOT FOUND")
        print()
        
        # 3. Columns in app.manual_expenses
        if any(schema == settings.DB_SCHEMA for schema, _ in table_locations):
            columns_query = text(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema AND table_name = 'manual_expenses'
                ORDER BY column_name
            """)
            columns = conn.execute(columns_query, {"schema": settings.DB_SCHEMA}).fetchall()
            print(f"3. Columns in {settings.DB_SCHEMA}.manual_expenses:")
            for col_name, col_type, nullable in columns:
                print(f"   - {col_name} ({col_type}, nullable={nullable})")
            
            has_shop_id = any(col[0] == 'shop_id' for col in columns)
            print()
            print(f"4. shop_id column exists: {'YES' if has_shop_id else 'NO'}")
        else:
            print(f"3. Table not found in schema '{settings.DB_SCHEMA}'")
            print(f"4. shop_id column: N/A (table not found)")
        
        print()
        return {
            "db_name": db_info[0],
            "schema": db_info[1],
            "table_exists": len(table_locations) > 0,
            "table_in_schema": any(schema == settings.DB_SCHEMA for schema, _ in table_locations),
            "has_shop_id": any(schema == settings.DB_SCHEMA for schema, _ in table_locations) and 
                          any(col[0] == 'shop_id' for col in conn.execute(columns_query, {"schema": settings.DB_SCHEMA}).fetchall()) if any(schema == settings.DB_SCHEMA for schema, _ in table_locations) else False
        }

def check_alembic_version():
    """Check current Alembic migration version."""
    print("=" * 60)
    print("Checking Alembic Migration Status")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        # Check if alembic_version table exists
        version_table_query = text("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_name = 'alembic_version'
            ORDER BY table_schema
        """)
        version_tables = conn.execute(version_table_query).fetchall()
        
        if version_tables:
            # Get version from expected schema
            version_in_schema = [t for t in version_tables if t[0] == settings.DB_SCHEMA]
            if version_in_schema:
                version_query = text(f"""
                    SELECT version_num
                    FROM {settings.DB_SCHEMA}.alembic_version
                    ORDER BY version_num DESC
                    LIMIT 1
                """)
                result = conn.execute(version_query)
                version = result.scalar()
                print(f"Current Alembic version in {settings.DB_SCHEMA}.alembic_version: {version or 'None'}")
                print(f"Expected migration: 20260123_223716")
                is_applied = version == '20260123_223716'
                print(f"Migration applied: {'YES' if is_applied else 'NO'}")
                return is_applied
            else:
                print(f"alembic_version table not found in schema '{settings.DB_SCHEMA}'")
                print("Available locations:")
                for schema, table in version_tables:
                    print(f"  - {schema}.{table}")
                return False
        else:
            print("[ERROR] alembic_version table not found (no migrations applied yet)")
            return False

def diagnose_after_migration():
    """Run diagnostic queries after migration."""
    print()
    print("=" * 60)
    print("DIAGNOSTIC: After Migration")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        # Check if shop_id exists
        shop_id_query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses' 
              AND column_name = 'shop_id'
        """)
        result = conn.execute(shop_id_query, {"schema": settings.DB_SCHEMA})
        shop_id_info = result.fetchone()
        
        if shop_id_info:
            print(f"[OK] shop_id column found in {settings.DB_SCHEMA}.manual_expenses:")
            print(f"   - Type: {shop_id_info[1]}")
            print(f"   - Nullable: {shop_id_info[2]}")
            
            # Check index
            index_query = text(f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = :schema
                  AND tablename = 'manual_expenses'
                  AND indexname = 'ix_manual_expenses_user_shop_date'
            """)
            index_result = conn.execute(index_query, {"schema": settings.DB_SCHEMA})
            index_info = index_result.fetchone()
            
            if index_info:
                print(f"[OK] Index found: {index_info[0]}")
            else:
                print(f"[WARNING] Index ix_manual_expenses_user_shop_date not found")
            
            return True
        else:
            print(f"[ERROR] shop_id column NOT found in {settings.DB_SCHEMA}.manual_expenses")
            return False

def main():
    """Main function."""
    print("=" * 60)
    print("Shop ID Migration Diagnostic and Application")
    print("=" * 60)
    print()
    
    # Print DB connection info
    print_db_info()
    
    # Diagnose before
    before_info = diagnose_before_migration()
    
    # Check Alembic version
    migration_applied = check_alembic_version()
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Database: {before_info['db_name']}")
    print(f"Schema: {settings.DB_SCHEMA}")
    print(f"Table exists: {'YES' if before_info['table_exists'] else 'NO'}")
    print(f"Table in schema: {'YES' if before_info['table_in_schema'] else 'NO'}")
    print(f"shop_id exists: {'YES' if before_info['has_shop_id'] else 'NO'}")
    print(f"Migration applied: {'YES' if migration_applied else 'NO'}")
    print()
    
    if before_info['has_shop_id']:
        print("[OK] shop_id column already exists. No action needed.")
        return 0
    
    if not migration_applied:
        print("=" * 60)
        print("ACTION REQUIRED: Apply Migration")
        print("=" * 60)
        print()
        print("To apply the migration, run:")
        print("  cd apps/api")
        print("  python -m alembic upgrade head")
        print()
        print("After applying, run this script again to verify.")
        return 1
    else:
        print("[WARNING] Migration is marked as applied, but shop_id doesn't exist.")
        print("   This might indicate a schema mismatch or migration issue.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
