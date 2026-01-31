"""add stg_leftout_old and fact_leftout_old_snapshot for left-out-report_old import

Revision ID: 20260132_leftout_old
Revises: 20260131_repair_leftout_barcode_norm
Create Date: 2026-01-32 00:00:00.000000

- app.stg_leftout_old: staging for left-out-report_old; all columns as _raw TEXT.
  Required: user_id uuid, upload_batch_id uuid, barcode_raw text, barcode_norm text.
  Index: (user_id, upload_batch_id, barcode_norm).
- app.fact_leftout_old_snapshot: fact table; MVP: user_id, upload_batch_id, loaded_at,
  barcode, barcode_norm, sku, product_id, product_name, in_sale int;
  optional: to_ship, total_stock, available_to_ship.
  No dim_shop/shop_id — binding only via fact_storage_snapshot by barcode_norm.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260132_leftout_old"
down_revision: Union[str, None] = "20260131_repair_leftout_barcode_norm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    # Staging: all columns as _raw TEXT to preserve Excel data
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

    # Fact: MVP core for metrics and barcode join (no shop_id)
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.fact_leftout_old_snapshot (
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            loaded_at timestamptz NOT NULL DEFAULT now(),
            barcode text,
            barcode_norm text,
            sku text,
            product_id text,
            product_name text,
            in_sale int4,
            to_ship int4,
            total_stock int4,
            available_to_ship int4,
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
