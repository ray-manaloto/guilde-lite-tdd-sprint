"""Add agent run fork metadata.

Revision ID: cefa2952f188
Revises: 943237da85b0
Create Date: 2025-03-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "cefa2952f188"
down_revision = "943237da85b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("parent_run_id", postgresql.UUID(as_uuid=True)))
    op.add_column(
        "agent_runs",
        sa.Column("parent_checkpoint_id", postgresql.UUID(as_uuid=True)),
    )
    op.add_column("agent_runs", sa.Column("fork_label", sa.String(length=100)))
    op.add_column("agent_runs", sa.Column("fork_reason", sa.Text()))
    op.create_index(
        op.f("ix_agent_runs_parent_run_id"),
        "agent_runs",
        ["parent_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_runs_parent_checkpoint_id"),
        "agent_runs",
        ["parent_checkpoint_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("agent_runs_parent_run_id_fkey"),
        "agent_runs",
        "agent_runs",
        ["parent_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("agent_runs_parent_checkpoint_id_fkey"),
        "agent_runs",
        "agent_checkpoints",
        ["parent_checkpoint_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("agent_runs_parent_checkpoint_id_fkey"),
        "agent_runs",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("agent_runs_parent_run_id_fkey"),
        "agent_runs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_agent_runs_parent_checkpoint_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_parent_run_id"), table_name="agent_runs")
    op.drop_column("agent_runs", "fork_reason")
    op.drop_column("agent_runs", "fork_label")
    op.drop_column("agent_runs", "parent_checkpoint_id")
    op.drop_column("agent_runs", "parent_run_id")
