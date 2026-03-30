"""Add scenario tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'scenarios',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text, nullable=False, server_default=''),
        sa.Column('endpoint_url', sa.String(512), nullable=False),
        sa.Column('api_key', sa.String(512), nullable=True),
        sa.Column('model_name', sa.String(128), nullable=False),
        sa.Column('llm_params', JSONB, nullable=False, server_default='{"max_tokens": null, "temperature": 0.7, "top_p": 1.0, "stop": [], "frequency_penalty": 0.0, "presence_penalty": 0.0}'),
        sa.Column('load_config', JSONB, nullable=False, server_default='{"test_mode": "stress", "duration_seconds": 60, "ramp_users_per_step": 1, "ramp_interval_seconds": 10, "breaking_criteria": null}'),
        sa.Column('max_concurrency', sa.Integer, nullable=False, server_default='100'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'scenario_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scenario_id', UUID(as_uuid=True), sa.ForeignKey('scenarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('behavior_overrides', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('scenario_id', 'profile_id', name='uq_scenario_profile'),
    )


def downgrade() -> None:
    op.drop_table('scenario_profiles')
    op.drop_table('scenarios')
