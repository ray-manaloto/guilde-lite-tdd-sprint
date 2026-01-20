"""Add sprint spec linkage

Revision ID: 2a7b3a1f4c9e
Revises: 7b1f0a9c5f45
Create Date: 2026-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2a7b3a1f4c9e"
down_revision: Union[str, None] = "7b1f0a9c5f45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sprints", sa.Column("spec_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("sprints_spec_id_fkey"),
        "sprints",
        "specs",
        ["spec_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("sprints_spec_id_fkey"), "sprints", type_="foreignkey")
    op.drop_column("sprints", "spec_id")
