"""add barcode_norm to fact_storage_snapshot

Revision ID: 20260128_add_barcode_norm_fss
Revises: 20260127_ensure_manual_expenses_schema
Create Date: 2026-01-28 00:00:00.000000

Adds barcode_norm column to app.fact_storage_snapshot for fast joins with
fact_leftout_snapshot in KPI (shop filter). Uses same normalization as
app.utils.barcode.barcode_norm_sql: NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20260128_add_barcode_norm_fss"
down_revision: Union[str, None] = "20260127_ensure_manual_expenses_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# fact_storage_snapshot has column "barcode" (from stg_storage.barcode_raw). Same formula as barcode_norm_sql('barcode').
BARCODE_NORM_SQL = "NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')"
INDEX_NAME = "ix_fact_storage_user_barcode_norm"
TABLE_SCHEMA = "app"
TABLE_NAME = "fact_storage_snapshot"


def upgrade() -> None:
    # Legacy table may be absent on clean DB; apply only if table exists.
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{TABLE_SCHEMA}.{TABLE_NAME}') IS NOT NULL THEN
                    ALTER TABLE {TABLE_SCHEMA}.{TABLE_NAME}
                    ADD COLUMN IF NOT EXISTS barcode_norm text;

                    UPDATE {TABLE_SCHEMA}.{TABLE_NAME}
                    SET barcode_norm = {BARCODE_NORM_SQL}
                    WHERE barcode IS NOT NULL
                      AND (barcode_norm IS NULL OR barcode_norm = '');

                    CREATE INDEX IF NOT EXISTS {INDEX_NAME}
                    ON {TABLE_SCHEMA}.{TABLE_NAME} (user_id, barcode_norm);
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{TABLE_SCHEMA}.{TABLE_NAME}') IS NOT NULL THEN
                    DROP INDEX IF EXISTS {TABLE_SCHEMA}.{INDEX_NAME};
                    ALTER TABLE {TABLE_SCHEMA}.{TABLE_NAME} DROP COLUMN IF EXISTS barcode_norm;
                END IF;
            END $$;
            """
        )
    )
