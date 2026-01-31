"""create map_shop_barcode table

Revision ID: 20260126_create_map_shop_barcode
Revises: 20260125_add_barcode_norm_to_stg
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '20260126_create_map_shop_barcode'
down_revision: Union[str, None] = '20260125_add_barcode_norm_to_stg'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schema 'app' if it doesn't exist
    op.execute(text("CREATE SCHEMA IF NOT EXISTS app"))

    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table("map_shop_barcode", schema="app"):
        # Table already exists (e.g. created manually or re-run) — only ensure indexes
        op.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_map_shop_barcode_user_shop_barcode
            ON app.map_shop_barcode (
                user_id,
                (COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid)),
                barcode_norm
            )
        """))
        op.create_index(
            'ix_map_shop_barcode_user_id',
            'map_shop_barcode',
            ['user_id'],
            unique=False,
            schema='app',
            if_not_exists=True
        )
        op.create_index(
            'ix_map_shop_barcode_barcode_norm',
            'map_shop_barcode',
            ['barcode_norm'],
            unique=False,
            schema='app',
            if_not_exists=True
        )
        op.create_index(
            'ix_map_shop_barcode_user_barcode',
            'map_shop_barcode',
            ['user_id', 'barcode_norm'],
            unique=False,
            schema='app',
            if_not_exists=True
        )
        op.create_index(
            'ix_map_shop_barcode_user_shop',
            'map_shop_barcode',
            ['user_id', 'shop_id'],
            unique=False,
            schema='app',
            if_not_exists=True
        )
        op.create_index(
            'ix_map_shop_barcode_user_last_seen',
            'map_shop_barcode',
            ['user_id', 'last_seen_at'],
            unique=False,
            schema='app',
            if_not_exists=True
        )
        return

    # Create map_shop_barcode table
    # This table stores normalized barcode mappings for linking data across reports
    op.create_table(
        'map_shop_barcode',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('upload_batch_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shop_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('barcode_norm', sa.Text(), nullable=False),
        sa.Column('sku', sa.Text(), nullable=True),
        sa.Column('product_id', sa.Text(), nullable=True),
        sa.Column('last_seen_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        schema='app'
    )
    
    # Create unique constraint using expression (COALESCE for shop_id)
    # This matches the ON CONFLICT logic in imports.py:
    # ON CONFLICT (user_id, COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid), barcode_norm)
    op.execute(text("""
        CREATE UNIQUE INDEX uq_map_shop_barcode_user_shop_barcode 
        ON app.map_shop_barcode (
            user_id,
            (COALESCE(shop_id, '00000000-0000-0000-0000-000000000000'::uuid)),
            barcode_norm
        )
    """))
    
    # Create indexes on individual columns for performance
    op.create_index(
        'ix_map_shop_barcode_user_id',
        'map_shop_barcode',
        ['user_id'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    op.create_index(
        'ix_map_shop_barcode_barcode_norm',
        'map_shop_barcode',
        ['barcode_norm'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    # Create additional composite indexes for performance
    op.create_index(
        'ix_map_shop_barcode_user_barcode',
        'map_shop_barcode',
        ['user_id', 'barcode_norm'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    op.create_index(
        'ix_map_shop_barcode_user_shop',
        'map_shop_barcode',
        ['user_id', 'shop_id'],
        unique=False,
        schema='app',
        if_not_exists=True
    )
    
    op.create_index(
        'ix_map_shop_barcode_user_last_seen',
        'map_shop_barcode',
        ['user_id', 'last_seen_at'],
        unique=False,
        schema='app',
        if_not_exists=True
    )


def downgrade() -> None:
    # Drop indexes (using IF EXISTS to avoid errors if they don't exist)
    op.execute(text("DROP INDEX IF EXISTS app.ix_map_shop_barcode_user_last_seen"))
    op.execute(text("DROP INDEX IF EXISTS app.ix_map_shop_barcode_user_shop"))
    op.execute(text("DROP INDEX IF EXISTS app.ix_map_shop_barcode_user_barcode"))
    op.execute(text("DROP INDEX IF EXISTS app.ix_map_shop_barcode_barcode_norm"))
    op.execute(text("DROP INDEX IF EXISTS app.ix_map_shop_barcode_user_id"))
    op.execute(text("DROP INDEX IF EXISTS app.uq_map_shop_barcode_user_shop_barcode"))
    
    # Drop table
    op.drop_table('map_shop_barcode', schema='app')
