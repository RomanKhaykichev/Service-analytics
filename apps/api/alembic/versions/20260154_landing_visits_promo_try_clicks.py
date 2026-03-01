"""landing_visits and promo_try_clicks for admin funnel metrics

Revision ID: 20260154
Revises: 20260153
Create Date: 2026-01-54 00:00:00.000000

- app.landing_visits: визиты на лендинг (visitor_key, created_at) — метрика «Зашли на сайт»
- app.promo_try_clicks: клики «Попробовать бесплатно» в промо-окне (visitor_key, created_at) — метрика «Попробовали»
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260154"
down_revision: Union[str, None] = "20260153"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.landing_visits (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            visitor_key varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_landing_visits_visitor_key ON {SCHEMA}.landing_visits (visitor_key)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_landing_visits_created_at ON {SCHEMA}.landing_visits (created_at)
    """))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.promo_try_clicks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            visitor_key varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_promo_try_clicks_visitor_key ON {SCHEMA}.promo_try_clicks (visitor_key)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_promo_try_clicks_created_at ON {SCHEMA}.promo_try_clicks (created_at)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.promo_try_clicks"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.landing_visits"))
