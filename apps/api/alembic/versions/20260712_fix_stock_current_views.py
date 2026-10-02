"""Fix v_current_batch and v_current_leftout for stock views

Revision ID: 20260712_fix_stock_current_views
Revises: 20260711_manual_product_cogs_history
"""

from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260712_fix_stock_current_views"
down_revision: Union[str, None] = "20260711_manual_product_cogs_history"
branch_labels = None
depends_on = None

SCHEMA = "app"


def upgrade() -> None:
    # Fresh/local DBs may have fact_* tables without columns the original SQL schema had.
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{SCHEMA}.fact_leftout_snapshot') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.fact_leftout_snapshot
                        ADD COLUMN IF NOT EXISTS snap_id bigserial;
                    ALTER TABLE {SCHEMA}.fact_leftout_snapshot
                        ADD COLUMN IF NOT EXISTS loaded_at timestamptz NOT NULL DEFAULT now();
                END IF;
                IF to_regclass('{SCHEMA}.fact_leftout_old_snapshot') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
                        ADD COLUMN IF NOT EXISTS loaded_at timestamptz NOT NULL DEFAULT now();
                    ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
                        ADD COLUMN IF NOT EXISTS fbs_qty integer NOT NULL DEFAULT 0;
                    ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
                        ADD COLUMN IF NOT EXISTS in_sale_qty integer NOT NULL DEFAULT 0;
                    ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
                        ADD COLUMN IF NOT EXISTS barcode text;
                END IF;
            END $$;
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE OR REPLACE VIEW {SCHEMA}.v_current_batch AS
            SELECT DISTINCT ON (user_id)
                user_id,
                upload_batch_id,
                created_at
            FROM {SCHEMA}.upload_batch
            WHERE status = 'success' OR is_current = true
            ORDER BY user_id, is_current DESC, created_at DESC NULLS LAST
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE OR REPLACE VIEW {SCHEMA}.v_current_leftout AS
            SELECT
                l.snap_id,
                l.user_id,
                l.upload_batch_id,
                l.shop_id,
                l.product_name,
                l.product_id,
                l.sku,
                l.barcode,
                l.ending,
                l.availability_indicator,
                l.planned_end_date,
                l.coverage_days,
                l.recommended_qty,
                l.fbs_stock,
                l.marketplace_side,
                l.in_supply,
                l.in_sale,
                l.to_customer,
                l.from_customer,
                l.sdh_stock,
                l.photo_stock,
                l.defect_stock,
                l.potential_per_unit,
                l.potential_total,
                l.loaded_at
            FROM {SCHEMA}.fact_leftout_snapshot l
            JOIN {SCHEMA}.v_current_batch cb
              ON cb.user_id = l.user_id AND cb.upload_batch_id = l.upload_batch_id
            UNION ALL
            SELECT
                NULL::bigint AS snap_id,
                lo.user_id,
                lo.upload_batch_id,
                NULL::uuid AS shop_id,
                NULL::text AS product_name,
                NULL::text AS product_id,
                NULL::text AS sku,
                lo.barcode,
                NULL::text AS ending,
                NULL::text AS availability_indicator,
                NULL::date AS planned_end_date,
                NULL::numeric(10,2) AS coverage_days,
                NULL::integer AS recommended_qty,
                lo.fbs_qty::integer AS fbs_stock,
                lo.in_sale_qty::integer AS marketplace_side,
                NULL::integer AS in_supply,
                lo.in_sale_qty::integer AS in_sale,
                NULL::integer AS to_customer,
                NULL::integer AS from_customer,
                NULL::integer AS sdh_stock,
                NULL::integer AS photo_stock,
                NULL::integer AS defect_stock,
                NULL::numeric(18,2) AS potential_per_unit,
                NULL::numeric(18,2) AS potential_total,
                lo.loaded_at
            FROM {SCHEMA}.fact_leftout_old_snapshot lo
            JOIN (
                SELECT DISTINCT ON (user_id) user_id, upload_batch_id
                FROM {SCHEMA}.fact_leftout_old_snapshot
                ORDER BY user_id, loaded_at DESC NULLS LAST
            ) latest_old
              ON latest_old.user_id = lo.user_id
             AND latest_old.upload_batch_id = lo.upload_batch_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM {SCHEMA}.fact_leftout_snapshot fls
                JOIN {SCHEMA}.v_current_batch cb
                  ON cb.user_id = fls.user_id
                 AND cb.upload_batch_id = fls.upload_batch_id
                WHERE fls.user_id = lo.user_id
            )
            """
        )
    )
    # Backfill is_current for existing successful imports (latest batch per user).
    op.execute(
        text(
            f"""
            WITH latest AS (
                SELECT DISTINCT ON (user_id) user_id, upload_batch_id
                FROM {SCHEMA}.upload_batch
                WHERE status = 'success'
                ORDER BY user_id, created_at DESC NULLS LAST
            )
            UPDATE {SCHEMA}.upload_batch ub
            SET is_current = (ub.upload_batch_id = latest.upload_batch_id)
            FROM latest
            WHERE ub.user_id = latest.user_id
              AND ub.status = 'success'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE OR REPLACE VIEW {SCHEMA}.v_current_batch AS
            SELECT DISTINCT ON (user_id)
                user_id,
                upload_batch_id,
                created_at
            FROM {SCHEMA}.upload_batch
            WHERE is_current = true
            ORDER BY user_id, created_at DESC
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE OR REPLACE VIEW {SCHEMA}.v_current_leftout AS
            SELECT
                l.snap_id,
                l.user_id,
                l.upload_batch_id,
                l.shop_id,
                l.product_name,
                l.product_id,
                l.sku,
                l.barcode,
                l.ending,
                l.availability_indicator,
                l.planned_end_date,
                l.coverage_days,
                l.recommended_qty,
                l.fbs_stock,
                l.marketplace_side,
                l.in_supply,
                l.in_sale,
                l.to_customer,
                l.from_customer,
                l.sdh_stock,
                l.photo_stock,
                l.defect_stock,
                l.potential_per_unit,
                l.potential_total,
                l.loaded_at
            FROM {SCHEMA}.fact_leftout_snapshot l
            JOIN {SCHEMA}.v_current_batch cb
              ON cb.user_id = l.user_id AND cb.upload_batch_id = l.upload_batch_id
            """
        )
    )
