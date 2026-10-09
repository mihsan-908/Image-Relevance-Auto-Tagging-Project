"""Unit tests for the batch processor service.

These tests run offline and verify image discovery, idempotency,
retries, failure isolation, and summary reporting.
"""

import os
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image import Image
from app.schemas.image_metadata import ImageMetadataSchema
from app.services.batch_processor import process_image_batch, BatchSummary


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

@pytest.fixture
def test_images_dir(tmp_path):
    """Create a temporary directory with dummy image files."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    
    # Create some supported and unsupported files
    (images_dir / "fox.jpg").write_text("dummy")
    (images_dir / "dog.png").write_text("dummy")
    (images_dir / "bear.webp").write_text("dummy")
    (images_dir / "notes.txt").write_text("dummy") # Unsupported
    
    return str(images_dir)

def dummy_metadata():
    return ImageMetadataSchema(
        subject="test subject",
        category="test category",
        attributes=["test"],
        caption="test caption",
        confidence=0.9
    )

def test_image_discovery(test_images_dir, db_session):
    """Test that only supported extensions are processed."""
    with patch("app.services.batch_processor.analyze_image_file") as mock_analyze:
        mock_analyze.return_value = dummy_metadata()
        
        summary = process_image_batch(test_images_dir, db_session)
        
        # 3 valid images, 1 invalid txt file
        assert summary.total == 3
        assert summary.completed == 3
        assert mock_analyze.call_count == 3


def test_successful_processing(test_images_dir, db_session):
    """Test standard successful processing pipeline."""
    with patch("app.services.batch_processor.analyze_image_file") as mock_analyze:
        mock_analyze.return_value = dummy_metadata()
        
        summary = process_image_batch(test_images_dir, db_session)
        
        assert summary.completed == 3
        assert summary.failed == 0
        
        # Check DB statuses
        images = db_session.query(Image).all()
        assert len(images) == 3
        for img in images:
            assert img.status == "COMPLETED"
            assert img.subject == "test subject"


def test_retry_after_simulated_failure(test_images_dir, db_session):
    """Test that a failure triggers a retry and eventually succeeds."""
    call_counts = {"count": 0}
    
    def side_effect(*args, **kwargs):
        call_counts["count"] += 1
        if call_counts["count"] == 1:
            raise ValueError("Simulated network error")
        return dummy_metadata()
        
    # We use a directory with just one valid image to isolate the test
    single_image_dir = os.path.dirname(test_images_dir) + "/single"
    os.makedirs(single_image_dir, exist_ok=True)
    with open(os.path.join(single_image_dir, "test.jpg"), "w") as f:
        f.write("dummy")

    with patch("app.services.batch_processor.analyze_image_file", side_effect=side_effect):
        # We also patch time.sleep to avoid waiting during tests
        with patch("app.services.batch_processor.time.sleep"):
            summary = process_image_batch(single_image_dir, db_session)
            
            assert call_counts["count"] == 2 # Failed once, succeeded next
            assert summary.completed == 1
            assert summary.failed == 0
            
            image = db_session.query(Image).first()
            assert image.status == "COMPLETED"


def test_permanent_failure(test_images_dir, db_session):
    """Test that max retries exhausted marks image as FAILED."""
    single_image_dir = os.path.dirname(test_images_dir) + "/single2"
    os.makedirs(single_image_dir, exist_ok=True)
    with open(os.path.join(single_image_dir, "fail.jpg"), "w") as f:
        f.write("dummy")
        
    def side_effect(*args, **kwargs):
        raise ValueError("Simulated persistent error")

    with patch("app.services.batch_processor.analyze_image_file", side_effect=side_effect):
        with patch("app.services.batch_processor.time.sleep"):
            summary = process_image_batch(single_image_dir, db_session)
            
            assert summary.completed == 0
            assert summary.failed == 1
            
            image = db_session.query(Image).first()
            assert image.status == "FAILED"


def test_failure_isolation(test_images_dir, db_session):
    """Test that one image failing does not stop the others."""
    
    def side_effect(image_path, **kwargs):
        if "dog.png" in image_path:
            raise ValueError("Simulated error for dog")
        return dummy_metadata()
        
    with patch("app.services.batch_processor.analyze_image_file", side_effect=side_effect):
        with patch("app.services.batch_processor.time.sleep"):
            summary = process_image_batch(test_images_dir, db_session)
            
            assert summary.total == 3
            assert summary.completed == 2
            assert summary.failed == 1
            
            failed_image = db_session.query(Image).filter(Image.filename == "dog.png").first()
            assert failed_image.status == "FAILED"
            
            success_images = db_session.query(Image).filter(Image.filename != "dog.png").all()
            for img in success_images:
                assert img.status == "COMPLETED"


def test_idempotency_skip_completed(test_images_dir, db_session):
    """Test that already COMPLETED images are skipped."""
    
    # Pretend fox.jpg is already in DB as COMPLETED
    fox_path = os.path.join(test_images_dir, "fox.jpg")
    existing_image = Image(path=fox_path, filename="fox.jpg", status="COMPLETED")
    db_session.add(existing_image)
    db_session.commit()
    
    with patch("app.services.batch_processor.analyze_image_file") as mock_analyze:
        mock_analyze.return_value = dummy_metadata()
        
        summary = process_image_batch(test_images_dir, db_session)
        
        assert summary.total == 3
        assert summary.skipped == 1
        assert summary.completed == 2 
        assert mock_analyze.call_count == 2
        
        images = db_session.query(Image).all()
        assert len(images) == 3 # No duplicates created


def test_low_confidence_reporting(test_images_dir, db_session):
    """Test that low confidence images are reported properly."""
    def side_effect(*args, **kwargs):
        meta = dummy_metadata()
        meta.confidence = 0.5 # Below 0.70 threshold
        return meta

    with patch("app.services.batch_processor.analyze_image_file", side_effect=side_effect):
        summary = process_image_batch(test_images_dir, db_session)
        
        assert summary.completed == 3
        assert summary.low_confidence == 3
        
        images = db_session.query(Image).all()
        for img in images:
            assert img.low_confidence is True
