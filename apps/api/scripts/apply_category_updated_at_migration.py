#!/usr/bin/env python3
"""
Direct SQL script to add category and updated_at to manual_expenses.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text

settings = get_settings()

def apply_migration():
    """Apply category and updated_at migration directly via SQL."""
    print("=" * 60)
    print("Applying category and updated_at migration")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Check if category exists
            check_category = text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema 
                  AND table_name = 'manual_expenses' 
                  AND column_name = 'category'
            """)
            if conn.execute(check_category, {"schema": settings.DB_SCHEMA}).fetchone():
                print("[OK] category column already exists")
            else:
                print("1. Adding category column...")
                conn.execute(text(f"""
                    ALTER TABLE {settings.DB_SCHEMA}.manual_expenses
                    ADD COLUMN category text NULL
                """))
                print("   [OK] Column added")
            
            # Check if updated_at exists
            check_updated_at = text(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema 
                  AND table_name = 'manual_expenses' 
                  AND column_name = 'updated_at'
            """)
            if conn.execute(check_updated_at, {"schema": settings.DB_SCHEMA}).fetchone():
                print("[OK] updated_at column already exists")
            else:
                print("2. Adding updated_at column...")
                conn.execute(text(f"""
                    ALTER TABLE {settings.DB_SCHEMA}.manual_expenses
                    ADD COLUMN updated_at timestamp with time zone NOT NULL DEFAULT now()
                """))
                print("   [OK] Column added")
            
            # Create index if not exists
            print("3. Creating index ix_manual_expenses_user_date...")
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_date
                ON {settings.DB_SCHEMA}.manual_expenses (user_id, expense_date)
            """))
            print("   [OK] Index created")
            
            # Update alembic_version
            print("4. Updating alembic_version...")
            conn.execute(text(f"""
                INSERT INTO {settings.DB_SCHEMA}.alembic_version (version_num)
                VALUES ('20260124_add_category_updated_at')
                ON CONFLICT (version_num) DO NOTHING
            """))
            print("   [OK] Version recorded")
            
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

def verify():
    """Verify migration."""
    print()
    print("=" * 60)
    print("Verification")
    print("=" * 60)
    
    with engine.connect() as conn:
        query = text(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = :schema 
              AND table_name = 'manual_expenses' 
              AND column_name IN ('category', 'updated_at')
            ORDER BY column_name
        """)
        result = conn.execute(query, {"schema": settings.DB_SCHEMA})
        cols = result.fetchall()
        
        for col_name, col_type, nullable in cols:
            print(f"[OK] {col_name}: {col_type} (nullable={nullable})")
        
        return len(cols) == 2

def main():
    if apply_migration():
        if verify():
            print()
            print("[SUCCESS] All checks passed!")
            return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
