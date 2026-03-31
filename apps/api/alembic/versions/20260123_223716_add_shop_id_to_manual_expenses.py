"""legacy step for manual_expenses (now no-op)

Revision ID: 20260123_223716
Revises: 
Create Date: 2026-01-23 22:37:16.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '20260123_223716'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kept for revision-chain compatibility.
    # The real baseline for app.manual_expenses is created later in
    # 20260127_ensure_manual_expenses_schema, which is idempotent and
    # safe on an empty database.
    pass


def downgrade() -> None:
    # No-op, see upgrade().
    pass
