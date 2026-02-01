"""fact_leftout_old_snapshot: exact schema for left-out-report_old (Склад block)

Revision ID: 20260137_leftout_old_exact
Revises: 20260136_leftout_old_cols
Create Date: 2026-01-37 00:00:00.000000

- Recreate app.fact_leftout_old_snapshot with exact columns only:
  user_id, upload_batch_id, barcode, barcode_norm, in_sale_qty, cost_sum, price_sum, loaded_at
- Indexes: (user_id, upload_batch_id), (user_id, barcode_norm)
- Ensures table exists and SQL/KPI stop failing.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260137_leftout_old_exact"
down_revision: Union[str, None] = "20260136_leftout_old_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "fact_leftout_old_snapshot"


def upgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE}"))
    op.execute(text(f"""
        CREATE TABLE {SCHEMA}.{TABLE} (
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
        CREATE INDEX ix_fact_leftout_old_snapshot_user_batch
        ON {SCHEMA}.{TABLE} (user_id, upload_batch_id)
    """))
    op.execute(text(f"""
        CREATE INDEX ix_fact_leftout_old_snapshot_user_barcode_norm
        ON {SCHEMA}.{TABLE} (user_id, barcode_norm)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_barcode_norm"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_fact_leftout_old_snapshot_user_batch"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.{TABLE}"))
