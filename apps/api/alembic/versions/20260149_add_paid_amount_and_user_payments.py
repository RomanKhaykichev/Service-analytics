"""users.paid_amount (Оплачено) + user_payments for subscription revenue by month

Revision ID: 20260149
Revises: 20260148
Create Date: 2026-01-49 00:00:00.000000

- app.users: paid_amount numeric(18,2) DEFAULT 0 — сумма, которую оплатил клиент (колонка «Оплачено»).
- app.user_payments: история платежей для графика дохода по месяцам (user_id, amount, paid_at).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260149"
down_revision: Union[str, None] = "20260148"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS paid_amount numeric(18,2) NOT NULL DEFAULT 0
    """))
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.user_payments (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            amount numeric(18,2) NOT NULL,
            paid_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_user_payments_user_id ON {SCHEMA}.user_payments (user_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_user_payments_paid_at ON {SCHEMA}.user_payments (paid_at)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.user_payments"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS paid_amount"))
