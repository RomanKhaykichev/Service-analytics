"""ensure manual_expenses table schema

Revision ID: 20260127_ensure_manual_expenses_schema
Revises: 20260126_create_map_shop_barcode
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text, inspect

# revision identifiers, used by Alembic.
revision: str = '20260127_ensure_manual_expenses_schema'
down_revision: Union[str, None] = '20260126_create_map_shop_barcode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str, schema: str = 'app') -> bool:
    """Check if table exists in schema."""
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = :schema 
            AND table_name = :table_name
        )
    """), {"schema": schema, "table_name": table_name})
    return result.scalar()


def column_exists(table_name: str, column_name: str, schema: str = 'app') -> bool:
    """Check if column exists in table."""
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_schema = :schema 
            AND table_name = :table_name
            AND column_name = :column_name
        )
    """), {"schema": schema, "table_name": table_name, "column_name": column_name})
    return result.scalar()


def upgrade() -> None:
    schema = 'app'
    table_name = 'manual_expenses'
    
    # Create table if it doesn't exist
    if not table_exists(table_name, schema):
        op.create_table(
            table_name,
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('expense_date', sa.Date(), nullable=False),
            sa.Column('amount_sum', sa.Numeric(18, 2), nullable=False),
            sa.Column('shop_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('category', sa.Text(), nullable=False),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
            schema=schema
        )
    else:
        # Table exists - add missing columns if needed
        if not column_exists(table_name, 'id', schema):
            op.add_column(
                table_name,
                sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
                schema=schema
            )
        
        if not column_exists(table_name, 'user_id', schema):
            op.add_column(
                table_name,
                sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
                schema=schema
            )
        
        if not column_exists(table_name, 'expense_date', schema):
            op.add_column(
                table_name,
                sa.Column('expense_date', sa.Date(), nullable=False),
                schema=schema
            )
        
        if not column_exists(table_name, 'amount_sum', schema):
            op.add_column(
                table_name,
                sa.Column('amount_sum', sa.Numeric(18, 2), nullable=False),
                schema=schema
            )
        
        if not column_exists(table_name, 'shop_id', schema):
            op.add_column(
                table_name,
                sa.Column('shop_id', postgresql.UUID(as_uuid=True), nullable=True),
                schema=schema
            )
        
        if not column_exists(table_name, 'category', schema):
            op.add_column(
                table_name,
                sa.Column('category', sa.Text(), nullable=True),  # Allow NULL initially
                schema=schema
            )
            # Set default for existing rows, then make NOT NULL
            op.execute(text(f"""
                UPDATE {schema}.{table_name}
                SET category = 'Прочее'
                WHERE category IS NULL
            """))
            op.alter_column(
                table_name,
                'category',
                nullable=False,
                schema=schema
            )
        else:
            # Column exists - check if it's nullable and fix if needed
            conn = op.get_bind()
            result = conn.execute(text("""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table_name
                  AND column_name = 'category'
            """), {"schema": schema, "table_name": table_name})
            is_nullable = result.scalar()
            
            if is_nullable == 'YES':
                # Set default for NULL values, then make NOT NULL
                op.execute(text(f"""
                    UPDATE {schema}.{table_name}
                    SET category = 'Прочее'
                    WHERE category IS NULL
                """))
                op.alter_column(
                    table_name,
                    'category',
                    nullable=False,
                    schema=schema
                )
        
        if not column_exists(table_name, 'comment', schema):
            op.add_column(
                table_name,
                sa.Column('comment', sa.Text(), nullable=True),
                schema=schema
            )
        
        if not column_exists(table_name, 'is_deleted', schema):
            op.add_column(
                table_name,
                sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
                schema=schema
            )
        
        if not column_exists(table_name, 'created_at', schema):
            op.add_column(
                table_name,
                sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
                schema=schema
            )
        
        if not column_exists(table_name, 'updated_at', schema):
            op.add_column(
                table_name,
                sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
                schema=schema
            )
    
    # Create indexes (if not exists)
    indexes = [
        ('ix_manual_expenses_user_date', ['user_id', 'expense_date']),
        ('ix_manual_expenses_user_shop', ['user_id', 'shop_id']),
        ('ix_manual_expenses_user_deleted', ['user_id', 'is_deleted']),
    ]
    
    for index_name, columns in indexes:
        try:
            op.create_index(
                index_name,
                table_name,
                columns,
                unique=False,
                schema=schema,
                if_not_exists=True
            )
        except Exception:
            # Index might already exist, skip
            pass


def downgrade() -> None:
    schema = 'app'
    table_name = 'manual_expenses'
    
    # Drop indexes
    indexes = [
        'ix_manual_expenses_user_deleted',
        'ix_manual_expenses_user_shop',
        'ix_manual_expenses_user_date',
    ]
    
    for index_name in indexes:
        try:
            op.drop_index(index_name, table_name=table_name, schema=schema)
        except Exception:
            # Index might not exist, skip
            pass
    
    # Note: We don't drop the table or columns in downgrade
    # to avoid data loss. Manual cleanup if needed.
