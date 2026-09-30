"""Wait until PostgreSQL accepts connections. Used by Docker entrypoint."""
import os
import sys
import time

import psycopg2


def _dsn(url: str) -> str:
    url = (url or "").strip().replace("\r", "")
    return url.replace("postgresql+psycopg2://", "postgresql://")


def main() -> int:
    url = _dsn(os.environ.get("DATABASE_URL", ""))
    if not url:
        print("ERROR: DATABASE_URL is empty", flush=True)
        return 1

    retries = 30
    last_err = "unknown"
    for i in range(retries):
        try:
            conn = psycopg2.connect(url)
            conn.close()
            print("Database is ready!", flush=True)
            return 0
        except Exception as exc:
            last_err = str(exc)
            left = retries - i - 1
            print(f"Waiting for database... {left} retries left ({last_err})", flush=True)
            time.sleep(2)

    print(f"ERROR: Database is not available after 60 seconds: {last_err}", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
