"""add barcode_norm to stg tables

Revision ID: 20260125_add_barcode_norm_to_stg
Revises: 20260124_add_category_updated_at
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20260125_add_barcode_norm_to_stg'
down_revision: Union[str, None] = '20260124_add_category_updated_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Legacy migration: source staging tables may be absent on a clean DB.
    # Apply only when each table exists.
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_sales') IS NOT NULL THEN
                ALTER TABLE app.stg_sales ADD COLUMN IF NOT EXISTS barcode_norm text;
                UPDATE app.stg_sales
                SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
                WHERE barcode_raw IS NOT NULL
                  AND barcode_norm IS NULL;
                CREATE INDEX IF NOT EXISTS ix_stg_sales_barcode_norm
                    ON app.stg_sales (user_id, upload_batch_id, barcode_norm);
            END IF;
        END $$;
    """))
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_leftout') IS NOT NULL THEN
                ALTER TABLE app.stg_leftout ADD COLUMN IF NOT EXISTS barcode_norm text;
                UPDATE app.stg_leftout
                SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
                WHERE barcode_raw IS NOT NULL
                  AND barcode_norm IS NULL;
                CREATE INDEX IF NOT EXISTS ix_stg_leftout_barcode_norm
                    ON app.stg_leftout (user_id, upload_batch_id, barcode_norm);
            END IF;
        END $$;
    """))
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_storage') IS NOT NULL THEN
                ALTER TABLE app.stg_storage ADD COLUMN IF NOT EXISTS barcode_norm text;
                UPDATE app.stg_storage
                SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
                WHERE barcode_raw IS NOT NULL
                  AND barcode_norm IS NULL;
                CREATE INDEX IF NOT EXISTS ix_stg_storage_barcode_norm
                    ON app.stg_storage (user_id, upload_batch_id, barcode_norm);
            END IF;
        END $$;
    """))


def downgrade() -> None:
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_storage') IS NOT NULL THEN
                DROP INDEX IF EXISTS app.ix_stg_storage_barcode_norm;
                ALTER TABLE app.stg_storage DROP COLUMN IF EXISTS barcode_norm;
            END IF;
        END $$;
    """))
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_leftout') IS NOT NULL THEN
                DROP INDEX IF EXISTS app.ix_stg_leftout_barcode_norm;
                ALTER TABLE app.stg_leftout DROP COLUMN IF EXISTS barcode_norm;
            END IF;
        END $$;
    """))
    op.execute(text("""
        DO $$
        BEGIN
            IF to_regclass('app.stg_sales') IS NOT NULL THEN
                DROP INDEX IF EXISTS app.ix_stg_sales_barcode_norm;
                ALTER TABLE app.stg_sales DROP COLUMN IF EXISTS barcode_norm;
            END IF;
        END $$;
    """))
