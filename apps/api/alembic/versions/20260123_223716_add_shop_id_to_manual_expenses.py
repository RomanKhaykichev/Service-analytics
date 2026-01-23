"""add shop_id to manual_expenses

Revision ID: 20260123_223716
Revises: 
Create Date: 2026-01-23 22:37:16.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260123_223716'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add shop_id column to manual_expenses table
    op.add_column(
        'manual_expenses',
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='app'
    )
    
    # Create index for date range queries with shop filter
    op.create_index(
        'ix_manual_expenses_user_shop_date',
        'manual_expenses',
        ['user_id', 'shop_id', 'expense_date'],
        unique=False,
        schema='app'
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index(
        'ix_manual_expenses_user_shop_date',
        table_name='manual_expenses',
        schema='app'
    )
    
    # Drop shop_id column
    op.drop_column('manual_expenses', 'shop_id', schema='app')
