"""Add quality_scores JSONB column to benchmark_requests.

Revision ID: 009
Revises: 008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "benchmark_requests",
        sa.Column("quality_scores", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("benchmark_requests", "quality_scores")
