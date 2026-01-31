"""fix storage snapshot barcode_norm/shop_raw and alembic_version.version_num length

Revision ID: 20260129_fix_fss_and_version
Revises: 20260128_shop_raw_fss
Create Date: 2026-01-29 00:00:00.000000

- Widen app.alembic_version.version_num to varchar(128) so long revision IDs do not break upgrades.
- Ensure app.fact_storage_snapshot has barcode_norm and shop_raw (ADD COLUMN IF NOT EXISTS).
- Create index ix_fact_storage_snapshot_user_barcode_norm if not exists.
- Backfill barcode_norm from barcode; backfill shop_raw from app.dim_shop where applicable.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260129_fix_fss_and_version"
down_revision: Union[str, None] = "20260128_shop_raw_fss"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
FSS = "fact_storage_snapshot"
BARCODE_NORM_EXPR = "NULLIF(TRIM(regexp_replace(CAST(barcode AS text), '\\s+', '', 'g')), '')"
INDEX_NAME = "ix_fact_storage_snapshot_user_barcode_norm"


def upgrade() -> None:
    # 1) Widen alembic_version.version_num so long revision IDs do not break upgrades
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.alembic_version
            ALTER COLUMN version_num TYPE varchar(128);
            """
        )
    )

    # 2) Ensure columns exist in fact_storage_snapshot
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.{FSS} ADD COLUMN IF NOT EXISTS barcode_norm text;
            ALTER TABLE {SCHEMA}.{FSS} ADD COLUMN IF NOT EXISTS shop_raw text;
            """
        )
    )

    # 3) Index for KPI joins
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS {INDEX_NAME}
            ON {SCHEMA}.{FSS} (user_id, barcode_norm);
            """
        )
    )

    # 4) Backfill barcode_norm from barcode (only where NULL)
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.{FSS}
            SET barcode_norm = {BARCODE_NORM_EXPR}
            WHERE barcode_norm IS NULL AND barcode IS NOT NULL;
            """
        )
    )

    # 5) Backfill shop_raw from dim_shop where fact has shop_id but shop_raw is NULL
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.{FSS} fss
            SET shop_raw = ds.shop_name
            FROM {SCHEMA}.dim_shop ds
            WHERE ds.user_id = fss.user_id
              AND ds.shop_id = fss.shop_id
              AND fss.shop_raw IS NULL
              AND ds.shop_name IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.{INDEX_NAME};"))
    # Do not drop columns or shrink version_num to avoid data loss / break existing DBs
    pass
