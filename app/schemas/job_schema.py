"""Pydantic schemas for background batch jobs."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CreateJobRequest(BaseModel):
    """Request payload to initiate a background batch processing job."""
    directory: str = "data/images"


class BatchJobResponse(BaseModel):
    """Response model representing the status and progress of a background job."""
    id: int
    directory: str
    status: str
    total_images: int
    processed_count: int
    completed_count: int
    failed_count: int
    skipped_count: int
    low_confidence_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
