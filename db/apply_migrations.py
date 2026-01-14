#!/usr/bin/env python3
"""
Database Migration Script
Applies migration files from db/migrations/ directory in order.

Usage:
    python db/apply_migrations.py [--dry-run] [--migration-file <file>]

Environment variables required:
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Get database connection from environment variables."""
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")
    
    if not all([db, user, pwd]):
        raise ValueError(
            "Missing database credentials. Set PGDATABASE, PGUSER, PGPASSWORD in .env"
        )
    
    conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return psycopg.connect(conn_str)


def get_migration_files(migrations_dir: Path) -> List[Path]:
    """Get migration files sorted by name."""
    if not migrations_dir.exists():
        return []
    
    files = sorted(migrations_dir.glob("*.sql"))
    return files


def read_sql_file(file_path: Path) -> str:
    """Read SQL file content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def check_migration_applied(conn, migration_name: str) -> bool:
    """Check if migration was already applied (simple check by view existence)."""
    # For this specific migration, check if view exists with correct structure
    if "005_fix_product_current_stock_view" in migration_name:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.views 
                    WHERE table_schema = 'app' 
                      AND table_name = 'v_product_current_stock'
                )
            """)
            view_exists = cur.fetchone()[0]
            
            if view_exists:
                # Check if view has correct structure (no regex in definition)
                cur.execute("""
                    SELECT pg_get_viewdef('app.v_product_current_stock', true)
                """)
                view_def = cur.fetchone()[0]
                # If view definition contains regexp_replace, migration is not applied
                return 'regexp_replace' not in view_def.lower()
            
            return False
    
    # For other migrations, assume not applied if we can't determine
    return False


def apply_migration(conn, migration_file: Path, dry_run: bool = False) -> bool:
    """Apply a single migration file."""
    migration_name = migration_file.name
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {migration_name}")
    
    # Check if already applied
    if check_migration_applied(conn, migration_name):
        print(f"  ✓ Migration already applied, skipping")
        return True
    
    sql_content = read_sql_file(migration_file)
    
    if dry_run:
        print(f"  Would execute {len(sql_content)} characters of SQL")
        print(f"  First 200 chars: {sql_content[:200]}...")
        return True
    
    try:
        with conn.cursor() as cur:
            cur.execute(sql_content)
        conn.commit()
        print(f"  ✓ Migration applied successfully")
        return True
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error applying migration: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without applying migrations"
    )
    parser.add_argument(
        "--migration-file",
        type=str,
        help="Apply specific migration file only (relative to db/migrations/)"
    )
    args = parser.parse_args()
    
    # Get project root (parent of db/)
    project_root = Path(__file__).parent.parent
    migrations_dir = project_root / "db" / "migrations"
    
    if not migrations_dir.exists():
        print(f"Error: Migrations directory not found: {migrations_dir}")
        sys.exit(1)
    
    # Get migration files
    if args.migration_file:
        migration_path = migrations_dir / args.migration_file
        if not migration_path.exists():
            print(f"Error: Migration file not found: {migration_path}")
            sys.exit(1)
        migration_files = [migration_path]
    else:
        migration_files = get_migration_files(migrations_dir)
    
    if not migration_files:
        print("No migration files found")
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    
    # Connect to database
    try:
        conn = get_connection()
        print("Connected to database")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)
    
    # Apply migrations
    success_count = 0
    for migration_file in migration_files:
        if apply_migration(conn, migration_file, dry_run=args.dry_run):
            success_count += 1
        else:
            print(f"\nFailed to apply {migration_file.name}")
            break
    
    conn.close()
    
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Completed: {success_count}/{len(migration_files)} migrations")
    
    if not args.dry_run and success_count == len(migration_files):
        print("\n✓ All migrations applied successfully!")
        print("\nVerification query:")
        print("  SELECT count(*), count(stock_qty), count(coverage_days), count(turnover_days)")
        print("  FROM app.v_product_current_stock WHERE user_id = '<your-user-uuid>';")


if __name__ == "__main__":
    main()
