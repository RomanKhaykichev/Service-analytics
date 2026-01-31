"""add shop_raw to fact_storage_snapshot

Revision ID: 20260128_shop_raw_fss
Revises: 20260128_add_barcode_norm_fss
Create Date: 2026-01-28 00:00:00.000000

Adds shop_raw column to app.fact_storage_snapshot for KPI shop filter
(upper(regexp_replace(trim(fss.shop_raw), ...)) = :shop_norm).
Populated by imports.populate_facts from stg_storage.shop_raw.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260128_shop_raw_fss"
down_revision: Union[str, None] = "20260128_add_barcode_norm_fss"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_SCHEMA = "app"
TABLE_NAME = "fact_storage_snapshot"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {TABLE_SCHEMA}.{TABLE_NAME}
            ADD COLUMN IF NOT EXISTS shop_raw text;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {TABLE_SCHEMA}.{TABLE_NAME} DROP COLUMN IF EXISTS shop_raw;
            """
        )
    )
