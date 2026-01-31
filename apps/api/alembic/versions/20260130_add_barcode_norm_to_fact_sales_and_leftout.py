"""add barcode_norm to fact_sales and fact_leftout_snapshot

Revision ID: 20260130_barcode_norm_sales_leftout
Revises: 20260129_fix_fss_and_version
Create Date: 2026-01-30 00:00:00.000000

- Add barcode_norm column to app.fact_sales and app.fact_leftout_snapshot.
- Create index (user_id, barcode_norm) on each for fast joins/filters.
- Backfill barcode_norm from barcode using same normalization as elsewhere.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260130_barcode_norm_sales_leftout"
down_revision: Union[str, None] = "20260129_fix_fss_and_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
BARCODE_NORM_EXPR = "NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')"


def upgrade() -> None:
    # fact_sales
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.fact_sales ADD COLUMN IF NOT EXISTS barcode_norm text;
            """
        )
    )
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.fact_sales
            SET barcode_norm = {BARCODE_NORM_EXPR}
            WHERE barcode_norm IS NULL AND barcode IS NOT NULL;
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_fact_sales_user_barcode_norm
            ON {SCHEMA}.fact_sales (user_id, barcode_norm);
            """
        )
    )

    # fact_leftout_snapshot
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.fact_leftout_snapshot ADD COLUMN IF NOT EXISTS barcode_norm text;
            """
        )
    )
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.fact_leftout_snapshot
            SET barcode_norm = {BARCODE_NORM_EXPR}
            WHERE barcode_norm IS NULL AND barcode IS NOT NULL;
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_fact_leftout_snapshot_user_barcode_norm
            ON {SCHEMA}.fact_leftout_snapshot (user_id, barcode_norm);
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS app.ix_fact_leftout_snapshot_user_barcode_norm;"))
    op.execute(text("DROP INDEX IF EXISTS app.ix_fact_sales_user_barcode_norm;"))
    op.execute(text("ALTER TABLE app.fact_leftout_snapshot DROP COLUMN IF EXISTS barcode_norm;"))
    op.execute(text("ALTER TABLE app.fact_sales DROP COLUMN IF EXISTS barcode_norm;"))
