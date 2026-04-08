from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.profile import BehaviorConfig


# --- LLM parameters (scenario-level) ---

class LLMParams(BaseModel):
    max_tokens: int | None = Field(None, ge=1, description="Max tokens per response. None = no limit.")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    stop: list[str] = Field(default_factory=list)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)


# --- Breaking point criteria ---

class BreakingCriteria(BaseModel):
    max_ttft_ms: int = Field(5000, ge=100, description="Max time to first token in ms")
    max_itl_ms: int = Field(500, ge=10, description="Max inter-token latency in ms")
    max_error_rate_pct: float = Field(10.0, ge=0.1, le=100.0, description="Max error rate percentage")


# --- Load configuration ---

class LoadConfig(BaseModel):
    test_mode: str = Field("stress", pattern="^(stress|ramp|breaking_point)$")
    duration_seconds: int = Field(60, ge=1)
    ramp_users_per_step: int = Field(1, ge=1)
    ramp_interval_seconds: int = Field(10, ge=1)
    load_curve: str = Field("step", pattern="^(step|linear|spike|wave)$")
    spike_at_pct: float = Field(50.0, ge=0, le=100, description="When the spike occurs (% of duration)")
    spike_duration_seconds: int = Field(10, ge=1, description="How long the spike lasts")
    wave_period_seconds: int = Field(30, ge=5, description="Period of the sine wave in seconds")
    breaking_criteria: BreakingCriteria | None = None


# --- Scenario-profile junction ---

class ScenarioProfileBase(BaseModel):
    profile_id: UUID
    user_count: int = Field(1, ge=1)
    behavior_overrides: BehaviorConfig | None = None


class ScenarioProfileCreate(ScenarioProfileBase):
    pass


class ScenarioProfileRead(ScenarioProfileBase):
    id: UUID
    scenario_id: UUID
    profile_name: str = ""
    weight: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Scenarios ---

class ScenarioBase(BaseModel):
    name: str
    description: str = ""
    llm_params: LLMParams = Field(default_factory=LLMParams)
    load_config: LoadConfig = Field(default_factory=LoadConfig)
    max_concurrency: int = Field(100, ge=1, le=10000)


class ScenarioCreate(ScenarioBase):
    profiles: list[ScenarioProfileCreate] = []


class ScenarioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    llm_params: LLMParams | None = None
    load_config: LoadConfig | None = None
    max_concurrency: int | None = Field(None, ge=1, le=10000)
    profiles: list[ScenarioProfileCreate] | None = None


class ScenarioRead(ScenarioBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    profiles: list[ScenarioProfileRead] = []

    model_config = {"from_attributes": True}


class ScenarioSummary(BaseModel):
    id: UUID
    name: str
    description: str
    profile_count: int = 0
    total_users: int = 0
    duration_seconds: int = 0
    test_mode: str = "stress"
    created_at: datetime

    model_config = {"from_attributes": True}
