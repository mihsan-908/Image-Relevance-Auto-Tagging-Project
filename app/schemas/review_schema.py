"""Pydantic schemas for the Review API and suggestion responses."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ReviewActionRequest(BaseModel):
    """Request payload when approving or rejecting a suggestion."""
    reason: str | None = None


class ReviewResponse(BaseModel):
    """Schema representing a review record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    suggestion_id: int
    approved: bool
    reason: str | None
    reviewed_at: datetime


class ImageSummarySchema(BaseModel):
    """Image details embedded within a suggestion response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    subject: str | None
    category: str | None
    caption: str | None
    confidence: float | None
    low_confidence: bool


class PostSummarySchema(BaseModel):
    """Post details embedded within a suggestion response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str


class SuggestionDetailResponse(BaseModel):
    """Detailed suggestion response schema for reviewers."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    image_id: int
    score: float
    status: str
    explanation: str | None
    accepted_by_guard: bool
    created_at: datetime
    updated_at: datetime
    image: ImageSummarySchema | None = None
    post: PostSummarySchema | None = None
    reviews: list[ReviewResponse] = []


class SuggestionListItemResponse(BaseModel):
    """Suggestion item in the post suggestions listing."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    image_id: int
    score: float
    status: str
    explanation: str | None
    accepted_by_guard: bool
    image_subject: str | None
    image_category: str | None
    image_confidence: float | None
    image_filename: str
