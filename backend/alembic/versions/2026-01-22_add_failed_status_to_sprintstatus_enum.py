"""Add failed status to SprintStatus enum

Revision ID: 2bc3b5eee230
Revises: 2026012201
Create Date: 2026-01-22 09:49:50.018199

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2bc3b5eee230'
down_revision: Union[str, None] = '2026012201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'FAILED' value to sprint_status enum type (uppercase to match existing values)
    op.execute("ALTER TYPE sprint_status ADD VALUE IF NOT EXISTS 'FAILED'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type and migrating data
    pass
