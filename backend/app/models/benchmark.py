import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False
    )
    endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("endpoints.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    scenario_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    endpoint_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    results_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    scenario: Mapped["Scenario"] = relationship(lazy="selectin")  # noqa: F821
    requests: Mapped[list["BenchmarkRequest"]] = relationship(
        back_populates="benchmark", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["BenchmarkSnapshot"]] = relationship(
        back_populates="benchmark", cascade="all, delete-orphan"
    )


class BenchmarkRequest(Base):
    __tablename__ = "benchmark_requests"
    __table_args__ = (
        Index("ix_benchreq_benchmark_created", "benchmark_id", "created_at"),
        Index("ix_benchreq_benchmark_profile", "benchmark_id", "profile_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ttft_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tgt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    inter_token_latencies: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_reported: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_body: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    benchmark: Mapped["Benchmark"] = relationship(back_populates="requests")


class BenchmarkSnapshot(Base):
    __tablename__ = "benchmark_snapshots"
    __table_args__ = (
        Index("ix_benchsnap_benchmark_ts", "benchmark_id", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requests_in_flight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p50_ttft_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_ttft_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99_ttft_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p50_tgt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95_tgt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    p99_tgt_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    throughput_rps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    throughput_tps: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    per_profile: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    benchmark: Mapped["Benchmark"] = relationship(back_populates="snapshots")
