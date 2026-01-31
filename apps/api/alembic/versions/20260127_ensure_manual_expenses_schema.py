"""ensure manual_expenses table schema

Revision ID: 20260127_ensure_manual_expenses_schema
Revises: 20260126_create_map_shop_barcode
Create Date: 2026-01-27 00:00:00.000000

Offline-safe: uses only DDL with IF NOT EXISTS (no SELECT/result.scalar()).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20260127_ensure_manual_expenses_schema'
down_revision: Union[str, None] = '20260126_create_map_shop_barcode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = 'app'
TABLE = 'manual_expenses'
Q = f'{SCHEMA}.{TABLE}'  # qualified name


def upgrade() -> None:
    # 1) Create table if not exists (full definition)
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {Q} (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL,
            expense_date date NOT NULL,
            amount_sum numeric(18,2) NOT NULL,
            shop_id uuid,
            category text NOT NULL DEFAULT 'Прочее',
            comment text,
            is_deleted boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """))

    # 2) Add columns if not exist (for tables that existed with fewer columns)
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS user_id uuid"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS expense_date date"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS amount_sum numeric(18,2)"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS shop_id uuid"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS category text"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS comment text"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS is_deleted boolean NOT NULL DEFAULT false"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()"))
    op.execute(text(f"ALTER TABLE {Q} ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()"))

    # 3) Ensure category NOT NULL (backfill NULLs then alter). No SELECT/result.scalar() — safe for offline --sql.
    op.execute(text(f"UPDATE {Q} SET category = 'Прочее' WHERE category IS NULL"))
    op.execute(text(f"ALTER TABLE {Q} ALTER COLUMN category SET DEFAULT 'Прочее'"))
    op.execute(text(f"ALTER TABLE {Q} ALTER COLUMN category SET NOT NULL"))

    # 4) Indexes
    op.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_date ON {Q} (user_id, expense_date)"))
    op.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_shop ON {Q} (user_id, shop_id)"))
    op.execute(text(f"CREATE INDEX IF NOT EXISTS ix_manual_expenses_user_deleted ON {Q} (user_id, is_deleted)"))


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_manual_expenses_user_deleted"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_manual_expenses_user_shop"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_manual_expenses_user_date"))
    # Table/columns not dropped to avoid data loss
