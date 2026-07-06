"""users: trial_display_shop for trial plan shop selection

Revision ID: 20260706_trial_shop
Revises: 20260629_fbs_qty
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260706_trial_shop"
down_revision: Union[str, None] = "20260629_fbs_qty"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"ALTER TABLE {SCHEMA}.users "
            "ADD COLUMN IF NOT EXISTS trial_display_shop varchar(255)"
        )
    )


def downgrade() -> None:
    op.execute(
        text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS trial_display_shop")
    )
