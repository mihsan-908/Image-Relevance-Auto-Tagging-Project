"""Pydantic schemas for API cost tracking."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class APICallCostResponse(BaseModel):
    """Details of a single API cost entry."""
    id: int
    operation_type: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostSummaryResponse(BaseModel):
    """Aggregated cost summary across all API calls."""
    total_api_calls: int
    vision_calls: int
    embedding_calls: int
    total_tokens: int
    total_estimated_cost_usd: float
