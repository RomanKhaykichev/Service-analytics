"""manual_product_cogs_history: audit log of actual COGS changes

Revision ID: 20260711_manual_product_cogs_history
Revises: 20260710_manual_product_cogs_effective_from
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260711_manual_product_cogs_history"
down_revision: Union[str, None] = "20260710_manual_product_cogs_effective_from"
branch_labels = None
depends_on = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.manual_product_cogs_history (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL,
                barcode_norm text NOT NULL,
                cogs_sum numeric(18,2) NOT NULL,
                effective_from date NOT NULL,
                calculation_source text NOT NULL DEFAULT 'profiboard',
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_manual_product_cogs_history_user_barcode
            ON {SCHEMA}.manual_product_cogs_history (user_id, barcode_norm, effective_from DESC, created_at DESC)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.manual_product_cogs_history"))
