"""leftout_old: stg_leftout_old and fact_leftout_old_snapshot (user schema)

Revision ID: 20260135_leftout_old_user
Revises: 20260134_leftout_old_cost_price
Create Date: 2026-01-35 00:00:00.000000

- app.stg_leftout_old: raw Excel columns (barcode_raw, sku_raw, product_id_raw,
  product_name_raw, in_sale_raw, cost_raw, price_raw), loaded_at. Index (user_id, upload_batch_id).
- app.fact_leftout_old_snapshot: snap_id PK, parsed columns (in_sale int, cost_per_unit, price_per_unit),
  barcode_norm. Indexes (user_id, upload_batch_id), (user_id, loaded_at), (user_id, barcode_norm).

Uses DROP IF EXISTS then CREATE so schema matches exactly; safe on empty DB.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260135_leftout_old_user"
down_revision: Union[str, None] = "20260134_leftout_old_cost_price"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    # Drop existing _old_ tables so we create exact user schema (no conflict with 20260132–34)
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.fact_leftout_old_snapshot"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.stg_leftout_old"))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.stg_leftout_old (
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            barcode_raw text,
            sku_raw text,
            product_id_raw text,
            product_name_raw text,
            in_sale_raw text,
            cost_raw text,
            price_raw text,
            loaded_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_stg_leftout_old_user_batch
        ON {SCHEMA}.stg_leftout_old (user_id, upload_batch_id)
    """))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.fact_leftout_old_snapshot (
            snap_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            barcode text,
            barcode_norm text,
            sku text,
            product_id text,
            product_name text,
            in_sale int NOT NULL DEFAULT 0,
            cost_per_unit numeric(18,2) NOT NULL DEFAULT 0,
            price_per_unit numeric(18,2) NOT NULL DEFAULT 0,
            loaded_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_fact_leftout_old_snapshot_user_batch
        ON {SCHEMA}.fact_leftout_old_snapshot (user_id, upload_batch_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_fact_leftout_old_snapshot_user_loaded_at
        ON {SCHEMA}.fact_leftout_old_snapshot (user_id, loaded_at)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_fact_leftout_old_snapshot_user_barcode_norm
        ON {SCHEMA}.fact_leftout_old_snapshot (user_id, barcode_norm)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_barcode_norm"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_loaded_at"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_batch"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.fact_leftout_old_snapshot"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_stg_leftout_old_user_batch"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.stg_leftout_old"))
