"""Add workflow tracking timestamp columns.

Revision ID: 2026-01-22_workflow_timestamps
Revises: cefa2952f188
Create Date: 2026-01-22

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2026012201"
down_revision: str | None = "2a7b3a1f4c9e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add timestamp columns to agent_runs
    op.add_column(
        "agent_runs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_runs",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )

    # Add phase timing columns to agent_checkpoints
    op.add_column(
        "agent_checkpoints",
        sa.Column("phase_start_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_checkpoints",
        sa.Column("phase_end_time", sa.DateTime(timezone=True), nullable=True),
    )

    # Add timing columns to agent_candidates
    op.add_column(
        "agent_candidates",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_candidates",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_candidates",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # Remove columns from agent_candidates
    op.drop_column("agent_candidates", "duration_ms")
    op.drop_column("agent_candidates", "completed_at")
    op.drop_column("agent_candidates", "started_at")

    # Remove columns from agent_checkpoints
    op.drop_column("agent_checkpoints", "phase_end_time")
    op.drop_column("agent_checkpoints", "phase_start_time")

    # Remove columns from agent_runs
    op.drop_column("agent_runs", "duration_ms")
    op.drop_column("agent_runs", "completed_at")
    op.drop_column("agent_runs", "started_at")
