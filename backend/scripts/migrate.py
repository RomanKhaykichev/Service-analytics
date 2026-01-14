#!/usr/bin/env python3
"""
Database Migration Script
Applies all SQL migration files in the correct order.

Order:
1. db/001_schema.sql
2. db/002_load_facts.sql
3. db/003_switch_to_barcode.sql
4. db/004_views.sql
5. db/005_populate_facts.sql
6. db/migrations/*.sql (in alphabetical order)
"""

import os
import sys
from pathlib import Path
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
            "Missing database credentials. Set PGDATABASE, PGUSER, PGPASSWORD"
        )
    
    conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return psycopg.connect(conn_str)


def read_sql_file(file_path: Path) -> str:
    """Read SQL file content."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def apply_sql_file(conn, file_path: Path) -> bool:
    """Apply a single SQL file."""
    print(f"Applying: {file_path.name}...", end=" ", flush=True)
    
    try:
        sql_content = read_sql_file(file_path)
        with conn.cursor() as cur:
            cur.execute(sql_content)
        conn.commit()
        print("✓")
        return True
    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        return False


def main():
    """Apply all migrations in order."""
    # In Docker, db directory is mounted at /app/db via docker-compose volume
    # If not in Docker, try to find db relative to script location
    if Path("/app/db").exists():
        db_dir = Path("/app/db")
    else:
        # Running locally, find db relative to script
        script_dir = Path(__file__).parent
        db_dir = script_dir.parent.parent / "db"
    
    if not db_dir.exists():
        print(f"Error: Database directory not found: {db_dir}")
        sys.exit(1)
    
    # Define migration order
    base_migrations = [
        "001_schema.sql",
        "002_load_facts.sql",
        "003_switch_to_barcode.sql",
        "004_views.sql",
        "005_populate_facts.sql",
    ]
    
    # Get migration files from db/migrations/
    migrations_dir = db_dir / "migrations"
    migration_files = []
    if migrations_dir.exists():
        migration_files = sorted(migrations_dir.glob("*.sql"))
    
    print("=" * 60)
    print("Database Migration Script")
    print("=" * 60)
    
    # Connect to database
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            conn = get_connection()
            print("✓ Connected to database")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                import time
                time.sleep(retry_delay)
            else:
                print(f"Error connecting to database after {max_retries} attempts: {e}")
                sys.exit(1)
    
    # Apply base migrations
    print("\nApplying base migrations:")
    for migration_name in base_migrations:
        migration_path = db_dir / migration_name
        if migration_path.exists():
            if not apply_sql_file(conn, migration_path):
                print(f"\nFailed to apply {migration_name}")
                conn.close()
                sys.exit(1)
        else:
            print(f"Skipping {migration_name} (not found)")
    
    # Apply migration files
    if migration_files:
        print(f"\nApplying migration files ({len(migration_files)} files):")
        for migration_file in migration_files:
            if not apply_sql_file(conn, migration_file):
                print(f"\nFailed to apply {migration_file.name}")
                conn.close()
                sys.exit(1)
    else:
        print("\nNo migration files found in db/migrations/")
    
    conn.close()
    print("\n" + "=" * 60)
    print("✓ All migrations applied successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
