"""Ensure stg_leftout_old.row_num exists for inventory_old import

Revision ID: 20260715_stg_leftout_old_row_num
Revises: 20260712_fix_stock_current_views

Later leftout_old migrations created stg_leftout_old without row_num
(CREATE TABLE IF NOT EXISTS), while imports.to_staging still inserts row_num.
This breaks Uzum/API sync of inventory_old on databases that never got the column.
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260715_stg_leftout_old_row_num"
down_revision: Union[str, None] = "20260712_fix_stock_current_views"
branch_labels = None
depends_on = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{SCHEMA}.stg_leftout_old') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.stg_leftout_old
                    ADD COLUMN IF NOT EXISTS row_num int4;
                    ALTER TABLE {SCHEMA}.stg_leftout_old
                    ADD COLUMN IF NOT EXISTS data jsonb;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.stg_leftout_old
            DROP COLUMN IF EXISTS row_num
            """
        )
    )
