"""add uzum_seller_api_key to users

Revision ID: 20260414_uzum_key
Revises: 20260413_engagement
Create Date: 2026-04-14

- app.users: uzum_seller_api_key text NULL — Uzum Seller API token per account
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260414_uzum_key"
down_revision: Union[str, None] = "20260413_engagement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "users"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.{TABLE}
        ADD COLUMN IF NOT EXISTS uzum_seller_api_key text NULL
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.{TABLE}
        DROP COLUMN IF EXISTS uzum_seller_api_key
    """))
