"""Unit tests for ImageMetadataSchema Pydantic validation.

These tests run locally without making network or Gemini API calls.
"""

import pytest
from pydantic import ValidationError
from app.schemas.image_metadata import ImageMetadataSchema


def test_valid_image_metadata_accepted():
    """Verify that a valid dictionary creates a valid ImageMetadataSchema object."""
    data = {
        "subject": "red fox",
        "category": "wildlife",
        "attributes": ["red fur", "pointed ears", "outdoors"],
        "caption": "A red fox standing in a grassy field.",
        "confidence": 0.95,
    }
    schema = ImageMetadataSchema(**data)
    
    assert schema.subject == "red fox"
    assert schema.category == "wildlife"
    assert schema.attributes == ["red fur", "pointed ears", "outdoors"]
    assert schema.caption == "A red fox standing in a grassy field."
    assert schema.confidence == 0.95


def test_confidence_below_zero_rejected():
    """Verify that confidence scores below 0.0 raise a ValidationError."""
    data = {
        "subject": "red fox",
        "category": "wildlife",
        "attributes": ["red fur"],
        "caption": "A red fox.",
        "confidence": -0.1,
    }
    with pytest.raises(ValidationError):
        ImageMetadataSchema(**data)


def test_confidence_above_one_rejected():
    """Verify that confidence scores above 1.0 raise a ValidationError."""
    data = {
        "subject": "red fox",
        "category": "wildlife",
        "attributes": ["red fur"],
        "caption": "A red fox.",
        "confidence": 1.05,
    }
    with pytest.raises(ValidationError):
        ImageMetadataSchema(**data)


def test_missing_required_fields_rejected():
    """Verify that missing required fields raise a ValidationError."""
    incomplete_data = {
        "subject": "red fox",
        "confidence": 0.8,
        # missing category, attributes, caption
    }
    with pytest.raises(ValidationError):
        ImageMetadataSchema(**incomplete_data)
