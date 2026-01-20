"""Add sprints

Revision ID: 0cda5251cdde
Revises: cefa2952f188
Create Date: 2026-01-19 15:59:00.454129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0cda5251cdde"
down_revision: Union[str, None] = "cefa2952f188"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sprints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PLANNED", "ACTIVE", "COMPLETED", name="sprint_status"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("sprints_pkey")),
    )
    op.create_index(op.f("sprints_name_idx"), "sprints", ["name"], unique=False)
    op.create_table(
        "sprint_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("sprint_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("TODO", "IN_PROGRESS", "BLOCKED", "DONE", name="sprint_item_status"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("estimate_points", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["sprint_id"],
            ["sprints.id"],
            name=op.f("sprint_items_sprint_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("sprint_items_pkey")),
    )
    op.create_index(op.f("sprint_items_sprint_id_idx"), "sprint_items", ["sprint_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("sprint_items_sprint_id_idx"), table_name="sprint_items")
    op.drop_table("sprint_items")
    op.drop_index(op.f("sprints_name_idx"), table_name="sprints")
    op.drop_table("sprints")
