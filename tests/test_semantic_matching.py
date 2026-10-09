"""Unit tests for semantic matching and ranking service."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.post import Post
from app.models.image import Image
from app.models.embedding import Embedding
from app.models.suggestion import Suggestion
from app.services.semantic_matching_service import rank_images_for_post

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


def test_ranking_with_mocked_vectors(db_session):
    """Test standard ranking flow with known mock vectors."""
    # 1. Setup Post and Post Embedding
    post = Post(title="Test Post", content="Post content")
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    
    post_emb = Embedding(post_id=post.id, vector=[1.0, 0.0, 0.0], model_name="test")
    db_session.add(post_emb)
    
    # 2. Setup Images and their Embeddings
    img_a = Image(path="a.jpg", filename="a.jpg", subject="Image A", status="COMPLETED")
    img_b = Image(path="b.jpg", filename="b.jpg", subject="Image B", status="COMPLETED")
    img_c = Image(path="c.jpg", filename="c.jpg", subject="Image C", status="COMPLETED")
    db_session.add_all([img_a, img_b, img_c])
    db_session.commit()
    
    # Image A is exactly identical vector
    emb_a = Embedding(image_id=img_a.id, vector=[1.0, 0.0, 0.0], model_name="test")
    
    # Image B is partially aligned
    emb_b = Embedding(image_id=img_b.id, vector=[0.7, 0.7, 0.0], model_name="test")
    
    # Image C is orthogonal (0 similarity)
    emb_c = Embedding(image_id=img_c.id, vector=[0.0, 1.0, 0.0], model_name="test")
    
    db_session.add_all([emb_a, emb_b, emb_c])
    db_session.commit()
    
    # 3. Perform Ranking
    result = rank_images_for_post(db_session, post.id, limit=3)
    
    # Image A (similarity 1.0) and Image B (similarity ~0.71) pass SEMANTIC_ACCEPT_THRESHOLD (0.60)
    # Image C (similarity 0.0) is rejected by mismatch guard, so accepted candidates length is 2
    assert len(result.candidates) == 2
    
    # Highest similarity should be first (Image A)
    assert result.candidates[0].image_id == img_a.id
    assert result.candidates[0].similarity_score == pytest.approx(1.0)
    assert result.candidates[0].rank == 1
    
    # Next is Image B
    assert result.candidates[1].image_id == img_b.id
    assert result.candidates[1].similarity_score > 0.0
    assert result.candidates[1].rank == 2
    
    # 4. Check if Suggestions were persisted (both accepted and rejected)
    suggestions = db_session.query(Suggestion).all()
    assert len(suggestions) == 3

    # Image C should be persisted as REJECTED
    rejected_c = db_session.query(Suggestion).filter(Suggestion.image_id == img_c.id).first()
    assert rejected_c is not None
    assert rejected_c.status == "REJECTED"
    assert "below threshold" in rejected_c.explanation



def test_ranking_idempotency(db_session):
    """Test that repeated ranking updates rather than duplicates suggestions."""
    post = Post(title="Test", content="Content")
    db_session.add(post)
    db_session.commit()
    
    db_session.add(Embedding(post_id=post.id, vector=[1.0], model_name="test"))
    
    img = Image(path="a.jpg", filename="a.jpg", status="COMPLETED")
    db_session.add(img)
    db_session.commit()
    
    db_session.add(Embedding(image_id=img.id, vector=[1.0], model_name="test"))
    db_session.commit()
    
    # Run twice
    rank_images_for_post(db_session, post.id, limit=5)
    rank_images_for_post(db_session, post.id, limit=5)
    
    suggestions = db_session.query(Suggestion).all()
    assert len(suggestions) == 1 # No duplicates


def test_missing_post(db_session):
    """Test handling of missing post."""
    with pytest.raises(ValueError, match="does not exist"):
        rank_images_for_post(db_session, 999, limit=5)


def test_missing_post_embedding(db_session):
    """Test handling of a post without an embedding."""
    post = Post(title="No Emb", content="None")
    db_session.add(post)
    db_session.commit()
    
    with pytest.raises(ValueError, match="has no valid embedding"):
        rank_images_for_post(db_session, post.id, limit=5)


def test_no_image_embeddings(db_session):
    """Test handling when post exists but no image embeddings exist."""
    post = Post(title="No Imgs", content="None")
    db_session.add(post)
    db_session.commit()
    
    db_session.add(Embedding(post_id=post.id, vector=[1.0], model_name="test"))
    db_session.commit()
    
    result = rank_images_for_post(db_session, post.id, limit=5)
    assert len(result.candidates) == 0


def test_ranking_limit(db_session):
    """Test that limit is respected."""
    post = Post(title="Test", content="Content")
    db_session.add(post)
    db_session.commit()
    db_session.add(Embedding(post_id=post.id, vector=[1.0], model_name="test"))
    
    for i in range(5):
        img = Image(path=f"{i}.jpg", filename=f"{i}.jpg", status="COMPLETED")
        db_session.add(img)
        db_session.commit()
        db_session.add(Embedding(image_id=img.id, vector=[1.0], model_name="test"))
        
    db_session.commit()
    
    result = rank_images_for_post(db_session, post.id, limit=2)
    assert len(result.candidates) == 2
    
    suggestions = db_session.query(Suggestion).all()
    assert len(suggestions) == 2
