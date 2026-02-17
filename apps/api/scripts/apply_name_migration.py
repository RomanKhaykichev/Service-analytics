#!/usr/bin/env python3
"""
Direct SQL script to add name column to manual_expenses if migration can't be run.
This is a fallback if alembic is not available.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text

settings = get_settings()

def apply_migration_direct():
    """Apply name migration directly via SQL."""
    print("=" * 60)
    print("Applying name column migration directly via SQL")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Check if name already exists
            check_query = text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema 
                  AND table_name = 'manual_expenses' 
                  AND column_name = 'name'
            """)
            result = conn.execute(check_query, {"schema": settings.DB_SCHEMA})
            if result.fetchone():
                print(f"[OK] name column already exists in {settings.DB_SCHEMA}.manual_expenses")
                trans.rollback()
                return True
            
            print(f"1. Adding name column to {settings.DB_SCHEMA}.manual_expenses...")
            add_column_query = text(f"""
                ALTER TABLE {settings.DB_SCHEMA}.manual_expenses
                ADD COLUMN name text NULL
            """)
            conn.execute(add_column_query)
            print("   [OK] Column added")
            
            trans.commit()
            print()
            print("[SUCCESS] Migration applied successfully!")
            print()
            print("You can now use the 'name' field when creating/updating expenses.")
            return True
            
        except Exception as e:
            trans.rollback()
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def verify():
    """Verify migration."""
    print()
    print("=" * 60)
    print("Verification")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        check_query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses' 
              AND column_name = 'name'
        """)
        result = conn.execute(check_query, {"schema": settings.DB_SCHEMA})
        row = result.fetchone()
        
        if row:
            print(f"[OK] name column exists:")
            print(f"     Type: {row[1]}")
            print(f"     Nullable: {row[2]}")
            return True
        else:
            print("[ERROR] name column NOT found!")
            return False

if __name__ == "__main__":
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print(f"Schema: {settings.DB_SCHEMA}")
    print()
    
    if apply_migration_direct():
        verify()
    else:
        print()
        print("Migration failed. Please check the error above.")
        sys.exit(1)
