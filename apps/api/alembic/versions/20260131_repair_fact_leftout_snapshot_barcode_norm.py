"""repair: ensure app.fact_leftout_snapshot has barcode_norm (column, index, backfill)

Revision ID: 20260131_repair_leftout_barcode_norm
Revises: 20260130_barcode_norm_sales_leftout
Create Date: 2026-01-31 00:00:00.000000

- ADD COLUMN IF NOT EXISTS barcode_norm text on app.fact_leftout_snapshot.
- Backfill from barcode: NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '').
- CREATE INDEX IF NOT EXISTS (user_id, barcode_norm).

Idempotent repair for DBs where 20260130 was not applied or leftout column was missing.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260131_repair_leftout_barcode_norm"
down_revision: Union[str, None] = "20260130_barcode_norm_sales_leftout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "fact_leftout_snapshot"
BARCODE_NORM_EXPR = "NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')"
INDEX_NAME = "ix_fact_leftout_snapshot_user_barcode_norm"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.{TABLE} ADD COLUMN IF NOT EXISTS barcode_norm text;
            """
        )
    )
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.{TABLE}
            SET barcode_norm = {BARCODE_NORM_EXPR}
            WHERE barcode_norm IS NULL AND barcode IS NOT NULL;
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS {INDEX_NAME}
            ON {SCHEMA}.{TABLE} (user_id, barcode_norm);
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.{INDEX_NAME};"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} DROP COLUMN IF EXISTS barcode_norm;"))
