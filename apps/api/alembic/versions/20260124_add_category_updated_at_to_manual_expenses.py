"""legacy step for manual_expenses (now no-op)

Revision ID: 20260124_add_category_updated_at
Revises: 20260123_223716
Create Date: 2026-01-24 00:00:00.000000

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '20260124_add_category_updated_at'
down_revision: Union[str, None] = '20260123_223716'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kept for revision-chain compatibility.
    # app.manual_expenses is created and normalized in
    # 20260127_ensure_manual_expenses_schema.
    pass


def downgrade() -> None:
    # No-op, see upgrade().
    pass
