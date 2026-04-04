from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EndpointBase(BaseModel):
    name: str
    endpoint_url: str
    api_key: str | None = None
    model_name: str
    gpu: str | None = None
    inference_engine: str | None = None
    notes: str | None = None


class EndpointCreate(EndpointBase):
    pass


class EndpointUpdate(BaseModel):
    name: str | None = None
    endpoint_url: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    gpu: str | None = None
    inference_engine: str | None = None
    notes: str | None = None


class EndpointRead(EndpointBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EndpointSummary(BaseModel):
    id: UUID
    name: str
    endpoint_url: str
    model_name: str
    gpu: str | None = None
    inference_engine: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Endpoint test (moved from scenario schemas) ---

class EndpointTestRequest(BaseModel):
    endpoint_url: str
    api_key: str | None = None
    model_name: str


class EndpointTestResponse(BaseModel):
    success: bool
    latency_ms: float | None = None
    error: str | None = None
    model_reported: str | None = None
