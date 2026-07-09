"""manual_product_cogs: user actual unit COGS per barcode

Revision ID: 20260709_manual_product_cogs
Revises: 20260707_drop_trial_shop
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260709_manual_product_cogs"
down_revision: Union[str, None] = "20260707_drop_trial_shop"
branch_labels = None
depends_on = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.manual_product_cogs (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL,
                barcode_norm text NOT NULL,
                barcode text,
                sku text,
                product_name text,
                shop text,
                cogs_sum numeric(18,2) NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                UNIQUE (user_id, barcode_norm)
            )
            """
        )
    )
    op.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_manual_product_cogs_user "
            f"ON {SCHEMA}.manual_product_cogs (user_id)"
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.manual_product_cogs"))
