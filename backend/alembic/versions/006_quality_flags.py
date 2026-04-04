"""Add quality_flags column to benchmark_requests.

Revision ID: 006
Revises: 005
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "benchmark_requests",
        sa.Column("quality_flags", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("benchmark_requests", "quality_flags")
