"""fact_leftout_old_snapshot: fbs_qty for FBS stock metric on summary

Revision ID: 20260629_fbs_qty
Revises: 20260628_exp_shop
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260629_fbs_qty"
down_revision: Union[str, None] = "20260628_exp_shop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{SCHEMA}.fact_leftout_old_snapshot') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
                    ADD COLUMN IF NOT EXISTS fbs_qty integer NOT NULL DEFAULT 0;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(f"ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot DROP COLUMN IF EXISTS fbs_qty")
    )
