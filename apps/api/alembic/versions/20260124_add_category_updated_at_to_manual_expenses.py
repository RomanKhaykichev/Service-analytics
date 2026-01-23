"""add category and updated_at to manual_expenses

Revision ID: 20260124_add_category_updated_at
Revises: 20260123_223716
Create Date: 2026-01-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260124_add_category_updated_at'
down_revision: Union[str, None] = '20260123_223716'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category column
    op.add_column(
        'manual_expenses',
        sa.Column('category', sa.Text(), nullable=True),
        schema='app'
    )
    
    # Add updated_at column with default
    op.add_column(
        'manual_expenses',
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='app'
    )
    
    # Create index for user_id and expense_date (if not exists)
    op.create_index(
        'ix_manual_expenses_user_date',
        'manual_expenses',
        ['user_id', 'expense_date'],
        unique=False,
        schema='app',
        if_not_exists=True
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(
        'ix_manual_expenses_user_date',
        table_name='manual_expenses',
        schema='app'
    )
    
    # Drop columns
    op.drop_column('manual_expenses', 'updated_at', schema='app')
    op.drop_column('manual_expenses', 'category', schema='app')
