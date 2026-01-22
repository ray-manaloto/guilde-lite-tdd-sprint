"""Add sprint track_id

Revision ID: b2e4d8c2d0f4
Revises: 2a7b3a1f4c9e
Create Date: 2026-01-22 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2e4d8c2d0f4"
down_revision: Union[str, None] = "2a7b3a1f4c9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sprints", sa.Column("track_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("sprints_track_id_idx"), "sprints", ["track_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("sprints_track_id_idx"), table_name="sprints")
    op.drop_column("sprints", "track_id")
