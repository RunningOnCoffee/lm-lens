"""Add benchmark tables

Revision ID: 004
Revises: 003
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'benchmarks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('scenario_id', UUID(as_uuid=True), sa.ForeignKey('scenarios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('scenario_snapshot', JSONB, nullable=False, server_default='{}'),
        sa.Column('results_summary', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'benchmark_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_id', UUID(as_uuid=True), sa.ForeignKey('benchmarks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('profile_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('session_id', UUID(as_uuid=True), nullable=False),
        sa.Column('turn_number', sa.Integer, nullable=False, server_default='0'),
        sa.Column('ttft_ms', sa.Float, nullable=True),
        sa.Column('tgt_ms', sa.Float, nullable=True),
        sa.Column('inter_token_latencies', JSONB, nullable=True),
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('tokens_per_second', sa.Float, nullable=True),
        sa.Column('http_status', sa.Integer, nullable=True),
        sa.Column('error_type', sa.String(64), nullable=True),
        sa.Column('error_detail', sa.Text, nullable=True),
        sa.Column('model_reported', sa.String(128), nullable=True),
        sa.Column('request_body', JSONB, nullable=True),
        sa.Column('response_text', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index('ix_benchreq_benchmark_created', 'benchmark_requests', ['benchmark_id', 'created_at'])
    op.create_index('ix_benchreq_benchmark_profile', 'benchmark_requests', ['benchmark_id', 'profile_id'])

    op.create_table(
        'benchmark_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('benchmark_id', UUID(as_uuid=True), sa.ForeignKey('benchmarks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('active_users', sa.Integer, nullable=False, server_default='0'),
        sa.Column('requests_in_flight', sa.Integer, nullable=False, server_default='0'),
        sa.Column('completed_requests', sa.Integer, nullable=False, server_default='0'),
        sa.Column('failed_requests', sa.Integer, nullable=False, server_default='0'),
        sa.Column('p50_ttft_ms', sa.Float, nullable=True),
        sa.Column('p95_ttft_ms', sa.Float, nullable=True),
        sa.Column('p99_ttft_ms', sa.Float, nullable=True),
        sa.Column('p50_tgt_ms', sa.Float, nullable=True),
        sa.Column('p95_tgt_ms', sa.Float, nullable=True),
        sa.Column('p99_tgt_ms', sa.Float, nullable=True),
        sa.Column('throughput_rps', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('throughput_tps', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('error_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('per_profile', JSONB, nullable=True),
    )

    op.create_index('ix_benchsnap_benchmark_ts', 'benchmark_snapshots', ['benchmark_id', 'timestamp'])


def downgrade() -> None:
    op.drop_table('benchmark_snapshots')
    op.drop_table('benchmark_requests')
    op.drop_table('benchmarks')
