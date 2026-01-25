"""add barcode_norm to stg tables

Revision ID: 20260125_add_barcode_norm_to_stg
Revises: 20260124_add_category_updated_at
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '20260125_add_barcode_norm_to_stg'
down_revision: Union[str, None] = '20260124_add_category_updated_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add barcode_norm column to stg_sales
    op.add_column(
        'stg_sales',
        sa.Column('barcode_norm', sa.Text(), nullable=True),
        schema='app'
    )
    
    # Add barcode_norm column to stg_leftout
    op.add_column(
        'stg_leftout',
        sa.Column('barcode_norm', sa.Text(), nullable=True),
        schema='app'
    )
    
    # Add barcode_norm column to stg_storage
    op.add_column(
        'stg_storage',
        sa.Column('barcode_norm', sa.Text(), nullable=True),
        schema='app'
    )
    
    # Backfill barcode_norm for existing data in stg_sales
    op.execute(text("""
        UPDATE app.stg_sales
        SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
        WHERE barcode_raw IS NOT NULL
          AND barcode_norm IS NULL
    """))
    
    # Backfill barcode_norm for existing data in stg_leftout
    op.execute(text("""
        UPDATE app.stg_leftout
        SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
        WHERE barcode_raw IS NOT NULL
          AND barcode_norm IS NULL
    """))
    
    # Backfill barcode_norm for existing data in stg_storage
    op.execute(text("""
        UPDATE app.stg_storage
        SET barcode_norm = NULLIF(TRIM(regexp_replace(CAST(barcode_raw AS text), '\\s+', '', 'g')), '')
        WHERE barcode_raw IS NOT NULL
          AND barcode_norm IS NULL
    """))
    
    # Create indexes for better join performance (optional but recommended)
    op.create_index(
        'ix_stg_sales_barcode_norm',
        'stg_sales',
        ['user_id', 'upload_batch_id', 'barcode_norm'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    op.create_index(
        'ix_stg_leftout_barcode_norm',
        'stg_leftout',
        ['user_id', 'upload_batch_id', 'barcode_norm'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    op.create_index(
        'ix_stg_storage_barcode_norm',
        'stg_storage',
        ['user_id', 'upload_batch_id', 'barcode_norm'],
        unique=False,
        schema='app',
        if_not_exists=True
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_stg_storage_barcode_norm', table_name='stg_storage', schema='app')
    op.drop_index('ix_stg_leftout_barcode_norm', table_name='stg_leftout', schema='app')
    op.drop_index('ix_stg_sales_barcode_norm', table_name='stg_sales', schema='app')
    
    # Drop columns
    op.drop_column('stg_storage', 'barcode_norm', schema='app')
    op.drop_column('stg_leftout', 'barcode_norm', schema='app')
    op.drop_column('stg_sales', 'barcode_norm', schema='app')
