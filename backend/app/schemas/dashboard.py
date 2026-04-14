from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FleetOverview(BaseModel):
    total_benchmarks: int = 0
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_quality_overall: float | None = None


class EndpointPerformance(BaseModel):
    endpoint_id: str
    name: str
    model_name: str = ""
    gpu: str | None = None
    inference_engine: str | None = None
    run_count: int = 0
    avg_ttft_p50: float | None = None
    avg_tps_p50: float | None = None
    avg_quality_overall: float | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    last_run_at: datetime | None = None


class ProfileLatencySummary(BaseModel):
    profile_id: str
    profile_name: str
    avg_ttft_p50: float | None = None
    benchmark_count: int = 0


class TokenEconomyEntry(BaseModel):
    group_id: str
    group_name: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    request_count: int = 0


class DashboardResponse(BaseModel):
    fleet: FleetOverview
    endpoints: list[EndpointPerformance]
    profiles: list[ProfileLatencySummary]
    recent_runs: list[dict]
