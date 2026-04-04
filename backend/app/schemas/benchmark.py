from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Benchmark ---

class BenchmarkCreate(BaseModel):
    scenario_id: UUID
    endpoint_id: UUID


class BenchmarkRead(BaseModel):
    id: UUID
    scenario_id: UUID
    endpoint_id: UUID | None = None
    status: str
    scenario_snapshot: dict = {}
    endpoint_snapshot: dict = {}
    results_summary: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    scenario_name: str = ""
    endpoint_name: str = ""

    model_config = {"from_attributes": True}


class BenchmarkSummary(BaseModel):
    id: UUID
    scenario_id: UUID
    scenario_name: str = ""
    endpoint_name: str = ""
    model_name: str = ""
    gpu: str | None = None
    inference_engine: str | None = None
    status: str
    total_requests: int = 0
    duration_seconds: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Benchmark Request ---

class BenchmarkRequestRead(BaseModel):
    id: UUID
    benchmark_id: UUID
    profile_id: UUID | None = None
    session_id: UUID
    turn_number: int
    ttft_ms: float | None = None
    tgt_ms: float | None = None
    inter_token_latencies: list[float] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tokens_per_second: float | None = None
    http_status: int | None = None
    error_type: str | None = None
    error_detail: str | None = None
    model_reported: str | None = None
    request_body: dict | None = None
    response_text: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Benchmark Snapshot ---

class BenchmarkSnapshotRead(BaseModel):
    id: UUID
    benchmark_id: UUID
    timestamp: datetime
    active_users: int = 0
    requests_in_flight: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    p50_ttft_ms: float | None = None
    p95_ttft_ms: float | None = None
    p99_ttft_ms: float | None = None
    p50_tgt_ms: float | None = None
    p95_tgt_ms: float | None = None
    p99_tgt_ms: float | None = None
    throughput_rps: float = 0.0
    throughput_tps: float = 0.0
    error_count: int = 0
    per_profile: dict | None = None

    model_config = {"from_attributes": True}
