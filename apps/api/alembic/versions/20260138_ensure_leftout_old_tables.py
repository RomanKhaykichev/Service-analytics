"""ensure app.stg_leftout_old and app.fact_leftout_old_snapshot exist (left-out-report_old pipeline)

Revision ID: 20260138_ensure_leftout_old
Revises: 20260137_leftout_old_exact
Create Date: 2026-01-38 00:00:00.000000

- app.stg_leftout_old: minimal raw columns (user_id, upload_batch_id, barcode_raw,
  in_sale_raw, cost_raw, price_raw, loaded_at). CREATE TABLE IF NOT EXISTS.
- app.fact_leftout_old_snapshot: user_id, upload_batch_id, barcode, barcode_norm,
  in_sale_qty int, cost_sum numeric(18,2), price_sum numeric(18,2), loaded_at.
  Indexes (user_id, upload_batch_id), (user_id, barcode_norm).
- Safe when previous leftout_old migrations (32–37) were not applied; no-op if tables exist.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260138_ensure_leftout_old"
down_revision: Union[str, None] = "20260137_leftout_old_exact"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.stg_leftout_old (
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            barcode_raw text,
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
            user_id uuid NOT NULL,
            upload_batch_id uuid NOT NULL,
            barcode text,
            barcode_norm text,
            in_sale_qty int NOT NULL DEFAULT 0,
            cost_sum numeric(18,2),
            price_sum numeric(18,2),
            loaded_at timestamptz NOT NULL DEFAULT now()
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
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_stg_leftout_old_user_batch"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.stg_leftout_old"))
