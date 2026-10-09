"""Schemas for semantic ranking suggestions."""

from pydantic import BaseModel
from typing import List

class RankedCandidateSchema(BaseModel):
    """Represents a single ranked image candidate."""
    image_id: int
    filename: str
    subject: str | None
    similarity_score: float
    rank: int


class RankedSuggestionsResponse(BaseModel):
    """Response returned when querying suggestions for a post."""
    post_id: int
    candidates: List[RankedCandidateSchema]
