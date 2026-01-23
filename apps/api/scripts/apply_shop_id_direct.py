#!/usr/bin/env python3
"""
Direct SQL script to add shop_id to manual_expenses if migration can't be run.
This is a fallback if alembic is not available.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text

settings = get_settings()

def apply_migration_direct():
    """Apply shop_id migration directly via SQL."""
    print("=" * 60)
    print("Applying shop_id migration directly via SQL")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check if shop_id already exists
            check_query = text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema 
                  AND table_name = 'manual_expenses' 
                  AND column_name = 'shop_id'
            """)
            result = conn.execute(check_query, {"schema": settings.DB_SCHEMA})
            if result.fetchone():
                print(f"[OK] shop_id column already exists in {settings.DB_SCHEMA}.manual_expenses")
                trans.rollback()
                return True
            
            print(f"1. Adding shop_id column to {settings.DB_SCHEMA}.manual_expenses...")
            add_column_query = text(f"""
                ALTER TABLE {settings.DB_SCHEMA}.manual_expenses
                ADD COLUMN shop_id uuid NULL
            """)
            conn.execute(add_column_query)
            print("   [OK] Column added")
            
            print(f"2. Creating index ix_manual_expenses_user_shop_date...")
            create_index_query = text(f"""
                CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_shop_date
                ON {settings.DB_SCHEMA}.manual_expenses (user_id, shop_id, expense_date)
            """)
            conn.execute(create_index_query)
            print("   [OK] Index created")
            
            # Create alembic_version table if it doesn't exist
            print(f"3. Creating alembic_version table if needed...")
            create_version_table = text(f"""
                CREATE TABLE IF NOT EXISTS {settings.DB_SCHEMA}.alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """)
            conn.execute(create_version_table)
            
            # Insert migration version
            print(f"4. Recording migration version...")
            insert_version = text(f"""
                INSERT INTO {settings.DB_SCHEMA}.alembic_version (version_num)
                VALUES ('20260123_223716')
                ON CONFLICT (version_num) DO NOTHING
            """)
            conn.execute(insert_version)
            print("   [OK] Version recorded")
            
            # Commit transaction
            trans.commit()
            print()
            print("[SUCCESS] Migration applied successfully!")
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def verify_migration():
    """Verify that migration was applied."""
    print()
    print("=" * 60)
    print("Verification")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Check shop_id
        check_query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses' 
              AND column_name = 'shop_id'
        """)
        result = conn.execute(check_query, {"schema": settings.DB_SCHEMA})
        shop_id_info = result.fetchone()
        
        if shop_id_info:
            print(f"[OK] shop_id column exists:")
            print(f"   - Type: {shop_id_info[1]}")
            print(f"   - Nullable: {shop_id_info[2]}")
        else:
            print("[ERROR] shop_id column NOT found")
            return False
        
        # Check index
        index_query = text(f"""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = :schema
              AND tablename = 'manual_expenses'
              AND indexname = 'ix_manual_expenses_user_shop_date'
        """)
        index_result = conn.execute(index_query, {"schema": settings.DB_SCHEMA})
        if index_result.fetchone():
            print("[OK] Index ix_manual_expenses_user_shop_date exists")
        else:
            print("[WARNING] Index not found")
        
        return True

def main():
    """Main function."""
    print("=" * 60)
    print("Direct Migration Application (Fallback)")
    print("=" * 60)
    print()
    print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print(f"Schema: {settings.DB_SCHEMA}")
    print()
    
    if apply_migration_direct():
        if verify_migration():
            print()
            print("=" * 60)
            print("[SUCCESS] All checks passed!")
            print("=" * 60)
            print()
            print("Next steps:")
            print("1. Restart the API")
            print("2. Test POST /api/extra-expenses")
            return 0
        else:
            print()
            print("[ERROR] Verification failed")
            return 1
    else:
        print()
        print("[ERROR] Migration application failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
