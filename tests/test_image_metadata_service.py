"""Unit tests for the image metadata database service.

These tests run offline and verify the PostgreSQL persistence logic,
confidence flag calculations, and unique tag generation.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image import Image
from app.models.tag import Tag
from app.schemas.image_metadata import ImageMetadataSchema
from app.services.image_metadata_service import save_image_metadata, LOW_CONFIDENCE_THRESHOLD

# Simple in-memory SQLite database for testing without destroying real data.
# Note: Since SQLite doesn't natively support full JSON arrays exactly like PostgreSQL,
# SQLAlchemy handles the basic serialization automatically for this test.
engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database for each test."""
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_save_valid_metadata_and_tags(db_session):
    """Verify that validated metadata is stored properly and tags are created."""
    # 1. Setup initial dummy image
    image = Image(path="data/test.jpg", filename="test.jpg", status="PENDING")
    db_session.add(image)
    db_session.commit()
    db_session.refresh(image)

    # 2. Mock Gemini structured response
    metadata = ImageMetadataSchema(
        subject="red fox",
        category="wildlife",
        attributes=["red fur", "pointed ears", "grass"],
        caption="A fox standing.",
        confidence=0.96
    )

    # 3. Save metadata
    updated_image = save_image_metadata(db_session, image, metadata)

    # 4. Verify Image record
    assert updated_image.status == "COMPLETED"
    assert updated_image.subject == "red fox"
    assert updated_image.category == "wildlife"
    assert updated_image.caption == "A fox standing."
    assert updated_image.attributes == ["red fur", "pointed ears", "grass"]
    assert updated_image.confidence == 0.96
    assert updated_image.low_confidence is False

    # 5. Verify Tag generation (subject, category, attributes)
    tag_names = {tag.name for tag in updated_image.tags}
    assert tag_names == {"red fox", "wildlife", "red fur", "pointed ears", "grass"}


def test_low_confidence_flag_calculation(db_session):
    """Verify the low_confidence flag is set correctly when confidence is below threshold."""
    image = Image(path="data/test2.jpg", filename="test2.jpg")
    db_session.add(image)
    db_session.commit()

    metadata = ImageMetadataSchema(
        subject="blurry shape",
        category="unknown",
        attributes=["blurry"],
        caption="An unclear photo.",
        confidence=LOW_CONFIDENCE_THRESHOLD - 0.1  # Deliberately low
    )

    updated_image = save_image_metadata(db_session, image, metadata)
    assert updated_image.low_confidence is True


def test_duplicate_tag_prevention(db_session):
    """Verify that duplicate tags are not created for the same image."""
    image = Image(path="data/test3.jpg", filename="test3.jpg")
    db_session.add(image)
    db_session.commit()

    # Create a pre-existing tag
    existing_tag = Tag(image_id=image.id, name="wildlife")
    db_session.add(existing_tag)
    db_session.commit()
    db_session.refresh(image)

    # Schema contains "wildlife" which already exists for this image
    metadata = ImageMetadataSchema(
        subject="red fox",
        category="wildlife", # Duplicate tag
        attributes=["red fox"], # Another duplicate tag
        caption="A fox.",
        confidence=0.85
    )

    updated_image = save_image_metadata(db_session, image, metadata)
    
    # Check total tags. We expect: "wildlife" (existing), "red fox" (subject/attribute)
    # The list should only contain 2 tags, not 4.
    tag_names = [tag.name for tag in updated_image.tags]
    assert len(tag_names) == 2
    assert "wildlife" in tag_names
    assert "red fox" in tag_names
