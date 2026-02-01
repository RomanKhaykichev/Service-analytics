"""left-out-report_old: stg_leftout_old + fact_leftout_old_snapshot

Revision ID: leftout_old_tables (18 chars <= 32)
Revises: 20260131_repair_leftout_barcode_norm
Create Date: 2026-01-39

- app.stg_leftout_old: user_id, upload_batch_id, barcode_raw, in_sale_raw,
  cost_raw, price_raw, loaded_at. Index (user_id, upload_batch_id).
- app.fact_leftout_old_snapshot: user_id, upload_batch_id, barcode, barcode_norm,
  in_sale_qty, cost_sum, price_sum, loaded_at. Indexes (user_id, upload_batch_id), (user_id, barcode_norm).
- Apply: alembic upgrade leftout_old_tables (or alembic upgrade head if this is the target head).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "leftout_old_tables"  # 18 chars <= 32
down_revision: Union[str, None] = "20260131_repair_leftout_barcode_norm"
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
