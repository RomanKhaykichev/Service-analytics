"""manual_product_cogs: effective_from date

Revision ID: 20260710_manual_product_cogs_effective_from
Revises: 20260709_manual_product_cogs
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260710_manual_product_cogs_effective_from"
down_revision: Union[str, None] = "20260709_manual_product_cogs"
branch_labels = None
depends_on = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.manual_product_cogs
            ADD COLUMN IF NOT EXISTS effective_from date
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.manual_product_cogs
            DROP COLUMN IF EXISTS effective_from
            """
        )
    )
