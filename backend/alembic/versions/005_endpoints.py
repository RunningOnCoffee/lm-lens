"""Create endpoints table, remove endpoint fields from scenarios, add endpoint fields to benchmarks.

Revision ID: 005
Revises: 004
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create endpoints table
    op.create_table(
        "endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("endpoint_url", sa.String(512), nullable=False),
        sa.Column("api_key", sa.String(512), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("gpu", sa.Text, nullable=True),
        sa.Column("inference_engine", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Remove endpoint columns from scenarios
    op.drop_column("scenarios", "endpoint_url")
    op.drop_column("scenarios", "api_key")
    op.drop_column("scenarios", "model_name")

    # Add endpoint fields to benchmarks
    op.add_column(
        "benchmarks",
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "benchmarks",
        sa.Column("endpoint_snapshot", postgresql.JSONB, nullable=False,
                  server_default="{}"),
    )
    op.create_foreign_key(
        "fk_benchmarks_endpoint_id",
        "benchmarks",
        "endpoints",
        ["endpoint_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_benchmarks_endpoint_id", "benchmarks", type_="foreignkey")
    op.drop_column("benchmarks", "endpoint_snapshot")
    op.drop_column("benchmarks", "endpoint_id")

    op.add_column("scenarios", sa.Column("model_name", sa.String(128), nullable=False, server_default=""))
    op.add_column("scenarios", sa.Column("api_key", sa.String(512), nullable=True))
    op.add_column("scenarios", sa.Column("endpoint_url", sa.String(512), nullable=False, server_default=""))

    op.drop_table("endpoints")
