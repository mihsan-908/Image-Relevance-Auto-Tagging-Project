"""Unit tests for the embedding generation and storage services."""

import pytest
from unittest.mock import patch
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.image import Image
from app.models.post import Post
from app.models.embedding import Embedding
from app.schemas.embedding_schema import EmbeddingSchema
from app.services.text_representation_service import build_image_embedding_text, build_post_embedding_text
from app.services.embedding_storage_service import store_image_embedding, store_post_embedding
from app.services.embedding_generation_service import EMBEDDING_MODEL, EMBEDDING_DIMENSIONALITY


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


def test_image_text_representation():
    """Verify that image metadata forms a correct text string."""
    image = Image(
        path="dummy.jpg", 
        filename="dummy.jpg",
        subject="red fox",
        category="wildlife",
        attributes=["red fur", "bushy tail"],
        caption="A fox in the wild."
    )
    
    text = build_image_embedding_text(image)
    
    assert "Subject: red fox" in text
    assert "Category: wildlife" in text
    assert "Attributes: red fur, bushy tail" in text
    assert "Caption: A fox in the wild." in text


def test_post_text_representation():
    """Verify that post metadata forms a correct text string."""
    post = Post(
        title="Red Fox Guide",
        content="This is a guide about red foxes."
    )
    
    text = build_post_embedding_text(post)
    
    assert "Title: Red Fox Guide" in text
    assert "Content: This is a guide about red foxes." in text


def test_embedding_schema_validation():
    """Verify that the embedding schema accepts valid vectors and rejects invalid ones."""
    # Valid
    valid_schema = EmbeddingSchema(
        vector=[0.1, 0.2, 0.3],
        model_name="test-model",
        dimensionality=3
    )
    assert len(valid_schema.vector) == 3
    
    # Invalid (empty vector)
    with pytest.raises(ValidationError):
        EmbeddingSchema(
            vector=[],
            model_name="test-model",
            dimensionality=0
        )


def dummy_generate_embedding(text: str, db=None) -> EmbeddingSchema:
    """Mock function to simulate Gemini's embedding API."""
    return EmbeddingSchema(
        vector=[0.1, 0.2, 0.3], # Small dummy vector
        model_name=EMBEDDING_MODEL,
        dimensionality=EMBEDDING_DIMENSIONALITY
    )


def test_image_embedding_persistence(db_session):
    """Verify that an image embedding is correctly stored in the database."""
    image = Image(
        path="dummy.jpg", 
        filename="dummy.jpg",
        subject="red fox",
        category="wildlife",
    )
    db_session.add(image)
    db_session.commit()
    
    with patch("app.services.embedding_storage_service.generate_embedding", side_effect=dummy_generate_embedding):
        embedding_record = store_image_embedding(db_session, image)
        
        assert embedding_record.id is not None
        assert embedding_record.image_id == image.id
        assert embedding_record.post_id is None
        assert embedding_record.vector == [0.1, 0.2, 0.3]
        assert embedding_record.model_name == EMBEDDING_MODEL


def test_post_embedding_persistence(db_session):
    """Verify that a post embedding is correctly stored in the database."""
    post = Post(
        title="Red Fox Guide",
        content="This is a guide about red foxes."
    )
    db_session.add(post)
    db_session.commit()
    
    with patch("app.services.embedding_storage_service.generate_embedding", side_effect=dummy_generate_embedding):
        embedding_record = store_post_embedding(db_session, post)
        
        assert embedding_record.id is not None
        assert embedding_record.post_id == post.id
        assert embedding_record.image_id is None
        assert embedding_record.vector == [0.1, 0.2, 0.3]
        assert embedding_record.model_name == EMBEDDING_MODEL


def test_image_embedding_idempotency(db_session):
    """Verify that running the embedding process twice for an image does not create duplicate rows."""
    image = Image(
        path="dummy.jpg", 
        filename="dummy.jpg",
        subject="red fox",
    )
    db_session.add(image)
    db_session.commit()
    
    with patch("app.services.embedding_storage_service.generate_embedding", side_effect=dummy_generate_embedding):
        # Run first time
        record1 = store_image_embedding(db_session, image)
        assert record1.id == 1
        
        # Run second time
        record2 = store_image_embedding(db_session, image)
        assert record2.id == 1  # Should be the exact same row ID
        
        # Check total rows in database
        total_embeddings = db_session.query(Embedding).count()
        assert total_embeddings == 1


def test_post_embedding_idempotency(db_session):
    """Verify that running the embedding process twice for a post does not create duplicate rows."""
    post = Post(
        title="Fox",
        content="Fox post."
    )
    db_session.add(post)
    db_session.commit()
    
    with patch("app.services.embedding_storage_service.generate_embedding", side_effect=dummy_generate_embedding):
        # Run first time
        record1 = store_post_embedding(db_session, post)
        assert record1.id == 1
        
        # Run second time
        record2 = store_post_embedding(db_session, post)
        assert record2.id == 1  # Should be the exact same row ID
        
        # Check total rows in database
        total_embeddings = db_session.query(Embedding).count()
        assert total_embeddings == 1
