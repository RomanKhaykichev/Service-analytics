#!/usr/bin/env python3
"""
Check current schema of manual_expenses table.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text

settings = get_settings()

def main():
    print("=" * 60)
    print("Current manual_expenses Schema")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        query = text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = 'manual_expenses'
            ORDER BY ordinal_position
        """)
        result = conn.execute(query, {"schema": settings.DB_SCHEMA})
        columns = result.fetchall()
        
        print(f"Columns in {settings.DB_SCHEMA}.manual_expenses:")
        print()
        for col_name, col_type, nullable, default in columns:
            default_str = f" DEFAULT {default}" if default else ""
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  - {col_name}: {col_type} {nullable_str}{default_str}")
        
        print()
        print("=" * 60)
        print("Required columns check:")
        print("=" * 60)
        
        required = {
            "id": False,
            "user_id": False,
            "expense_date": False,
            "amount_sum": False,
            "shop_id": False,
            "category": False,
            "comment": False,
            "created_at": False,
            "updated_at": False,
            "is_deleted": False
        }
        
        for col_name, _, _, _ in columns:
            if col_name in required:
                required[col_name] = True
        
        for col, exists in required.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {col}")
        
        missing = [col for col, exists in required.items() if not exists]
        if missing:
            print()
            print(f"Missing columns: {', '.join(missing)}")
        else:
            print()
            print("All required columns exist!")

if __name__ == "__main__":
    main()
