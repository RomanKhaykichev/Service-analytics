"""training_page_views and tariff_payment_opens for admin metrics

Revision ID: 20260413_engagement
Revises: 20260412_support_resolved
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260413_engagement"
down_revision: Union[str, None] = "20260412_support_resolved"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.training_page_views (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_training_page_views_created_at "
            f"ON {SCHEMA}.training_page_views (created_at)"
        )
    )
    op.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_training_page_views_user_id "
            f"ON {SCHEMA}.training_page_views (user_id)"
        )
    )

    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.tariff_payment_opens (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_tariff_payment_opens_created_at "
            f"ON {SCHEMA}.tariff_payment_opens (created_at)"
        )
    )
    op.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_tariff_payment_opens_user_id "
            f"ON {SCHEMA}.tariff_payment_opens (user_id)"
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.tariff_payment_opens"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.training_page_views"))
