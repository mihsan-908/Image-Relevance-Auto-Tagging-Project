"""Pydantic schema for validating Gemini embedding results."""

from pydantic import BaseModel, Field

class EmbeddingSchema(BaseModel):
    """Schema for validating an embedding vector from Gemini."""
    
    vector: list[float] = Field(..., min_length=1)
    model_name: str
    dimensionality: int
    
