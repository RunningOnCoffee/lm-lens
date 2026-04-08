"""Add seed and prompt_plan to benchmarks for reproducible runs.

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "007"
down_revision = "006"


def upgrade() -> None:
    op.add_column("benchmarks", sa.Column("seed", sa.Integer(), nullable=True))
    op.add_column("benchmarks", sa.Column("prompt_plan", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("benchmarks", "prompt_plan")
    op.drop_column("benchmarks", "seed")
