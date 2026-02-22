"""import_file_attempts: учёт по каждому файлу (успех/ошибка) для метрик импортов

Revision ID: 20260151
Revises: 20260150
Create Date: 2026-01-51 00:00:00.000000

- app.import_file_attempts: одна строка на каждую попытку загрузки файла (upload_batch_id, file_type, status, created_at).
  Метрики: успех = загрузка Excel прошла без ошибки, ошибка = при загрузке вернулась ошибка. Считаем по файлам: 3 успеха + 1 ошибка = success=3, failed=1.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260151"
down_revision: Union[str, None] = "20260150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.import_file_attempts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            upload_batch_id uuid NOT NULL REFERENCES {SCHEMA}.upload_batch(upload_batch_id) ON DELETE CASCADE,
            file_type varchar(50) NOT NULL,
            status varchar(20) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_import_file_attempts_created_at ON {SCHEMA}.import_file_attempts (created_at)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_import_file_attempts_upload_batch_id ON {SCHEMA}.import_file_attempts (upload_batch_id)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.import_file_attempts"))
