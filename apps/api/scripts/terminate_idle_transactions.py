"""Terminate idle-in-transaction backends."""
from sqlalchemy import create_engine, text

from app.settings import get_settings


def main() -> None:
    engine = create_engine(get_settings().DATABASE_URL, connect_args={"connect_timeout": 5})
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT pid FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state = 'idle in transaction'
                  AND pid <> pg_backend_pid()
                """
            )
        ).fetchall()
        for (pid,) in rows:
            conn.execute(text("SELECT pg_terminate_backend(:p)"), {"p": pid})
            print("terminated", pid)
        conn.commit()


if __name__ == "__main__":
    main()
