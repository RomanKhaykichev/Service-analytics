"""merge multiple heads into one

Revision ID: 20260146_merge_heads
Revises: 20260145_ensure_auth_tables, 20260138_ensure_leftout_old, leftout_old_tables
Create Date: 2026-01-46 00:00:00.000000

Merges all branch heads so 'alembic upgrade head' has a single target.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260146_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("20260145_ensure_auth_tables", "20260138_ensure_leftout_old", "leftout_old_tables")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
