"""
Добавляет колонку preferred_language в app.users (если её ещё нет).
Используйте, если миграция 20260153 не применилась через alembic.

Запуск из apps/api:
  python scripts/add_preferred_language_column.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from app.settings import get_settings


def main():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    schema = settings.DB_SCHEMA
    with engine.connect() as conn:
        conn.execute(text(f"""
            ALTER TABLE {schema}.users
            ADD COLUMN IF NOT EXISTS preferred_language varchar(10) NULL
        """))
        conn.commit()
    print("OK: app.users.preferred_language добавлена (или уже есть)")


if __name__ == "__main__":
    main()
