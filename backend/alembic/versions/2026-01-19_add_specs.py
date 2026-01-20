"""Add specs

Revision ID: 7b1f0a9c5f45
Revises: 0cda5251cdde
Create Date: 2026-01-19 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7b1f0a9c5f45"
down_revision: Union[str, None] = "0cda5251cdde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "specs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column(
            "complexity",
            sa.Enum("SIMPLE", "STANDARD", "COMPLEX", name="spec_complexity"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "VALIDATED", "APPROVED", "REJECTED", name="spec_status"),
            nullable=False,
        ),
        sa.Column("phases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("specs_user_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("specs_pkey")),
    )
    op.create_index(op.f("specs_user_id_idx"), "specs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("specs_user_id_idx"), table_name="specs")
    op.drop_table("specs")
    op.execute("DROP TYPE IF EXISTS spec_status")
    op.execute("DROP TYPE IF EXISTS spec_complexity")
