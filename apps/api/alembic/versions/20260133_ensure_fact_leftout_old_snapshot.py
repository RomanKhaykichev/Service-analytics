"""ensure app.fact_leftout_old_snapshot and app.stg_leftout_old exist (idempotent)

Revision ID: 20260133_ensure_leftout_old
Revises: 20260132_leftout_old
Create Date: 2026-01-33 00:00:00.000000

- app.fact_leftout_old_snapshot: user_id, upload_batch_id, barcode, barcode_norm,
  sku, product_id, product_name, in_sale, loaded_at. PK (user_id, upload_batch_id, barcode_norm).
  Indexes: (user_id, upload_batch_id), (user_id, barcode_norm).
- app.stg_leftout_old: staging for left-out-report_old (IF NOT EXISTS).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260133_ensure_leftout_old"
down_revision: Union[str, None] = "20260132_leftout_old"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    # Staging: IF NOT EXISTS so safe if 20260132 already created it
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.stg_leftout_old (
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            row_num int4,
            barcode_raw text,
            barcode_norm text,
            product_name_raw text,
            sku_raw text,
            product_id_raw text,
            in_sale_raw text,
            to_ship_raw text,
            total_stock_raw text,
            available_to_ship_raw text
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_stg_leftout_old_user_batch_barcode_norm
        ON {SCHEMA}.stg_leftout_old (user_id, upload_batch_id, barcode_norm)
    """))

    # Fact: exact schema requested (user_id, upload_batch_id, barcode, barcode_norm,
    # sku, product_id, product_name, in_sale, loaded_at)
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.fact_leftout_old_snapshot (
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            barcode text,
            barcode_norm text,
            sku text,
            product_id text,
            product_name text,
            in_sale int4,
            loaded_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, upload_batch_id, barcode_norm)
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_fact_leftout_old_snapshot_user_batch
        ON {SCHEMA}.fact_leftout_old_snapshot (user_id, upload_batch_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_fact_leftout_old_snapshot_user_barcode_norm
        ON {SCHEMA}.fact_leftout_old_snapshot (user_id, barcode_norm)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_barcode_norm"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_batch"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.fact_leftout_old_snapshot"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_stg_leftout_old_user_batch_barcode_norm"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.stg_leftout_old"))
