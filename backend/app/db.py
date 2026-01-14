import os
from typing import Optional, List, Dict, Any
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

# Connection pool (simple approach - one connection per request)
def get_conn():
    """Get database connection."""
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    db = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    pwd = os.getenv("PGPASSWORD")
    
    if not all([db, user, pwd]):
        raise ValueError("Missing database credentials in .env")
    
    conn_str = f"host={host} port={port} dbname={db} user={user} password={pwd}"
    return psycopg.connect(conn_str, row_factory=dict_row)


def _ensure_str_values(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Ensure all text values in row are str (not bytes)."""
    if row is None:
        return None
    result = {}
    for key, value in row.items():
        if isinstance(value, bytes):
            result[key] = value.decode('utf-8')
        else:
            result[key] = value
    return result


def execute_one(query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Execute query and return one row."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            row = cur.fetchone()
            return _ensure_str_values(row)

def execute_all(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute query and return all rows."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            rows = cur.fetchall()
            return [_ensure_str_values(row) for row in rows] if rows else []

