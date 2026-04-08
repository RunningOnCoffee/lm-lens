"""Add quality_flag_count to benchmark_snapshots.

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "benchmark_snapshots",
        sa.Column("quality_flag_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("benchmark_snapshots", "quality_flag_count")
