"""Unit tests for Stage 3.3 Mismatch Guard.

Verifies the 8 scenarios specified in Stage 3.3 requirements:
1. Red fox image + red fox article -> ACCEPT (PENDING)
2. Wolf image + red fox article -> REJECT (clear subject conflict)
3. Low vision confidence image -> REJECT
4. Low semantic similarity image (< 0.60) -> REJECT
5. Clear category mismatch -> REJECT
6. Ambiguous wildlife article + bear image -> NOT rejected by subject check
7. Rejected suggestions are persisted with their rejection explanation
8. Repeated ranking does not create duplicate suggestions (idempotency)
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.post import Post
from app.models.image import Image
from app.models.embedding import Embedding
from app.models.suggestion import Suggestion
from app.services.mismatch_guard_service import check_candidate
from app.services.semantic_matching_service import rank_images_for_post

engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh in-memory SQLite database per test."""
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_scenario_1_red_fox_accepted():
    """Scenario 1: Red fox article with red fox image -> ACCEPT."""
    post = Post(title="Red Fox in the Woods", content="A red fox walking through a quiet autumn forest.")
    image = Image(
        filename="fox.jpg",
        path="fox.jpg",
        subject="red fox",
        category="wildlife",
        confidence=0.88,
        low_confidence=False
    )
    # High semantic similarity
    result = check_candidate(post=post, image=image, semantic_score=0.85)
    assert result.accepted is True
    assert "Passed all mismatch guard checks" in result.reason


def test_scenario_2_wolf_against_fox_article_rejected():
    """Scenario 2: Red fox article with wolf image -> REJECT (subject conflict)."""
    post = Post(title="Red Fox Study", content="Observing the red fox hunting in the autumn meadow.")
    image = Image(
        filename="wolf.jpg",
        path="wolf.jpg",
        subject="wolf",
        category="wildlife",
        confidence=0.90,
        low_confidence=False
    )
    result = check_candidate(post=post, image=image, semantic_score=0.75)
    assert result.accepted is False
    assert "Clear subject conflict" in result.reason


def test_scenario_3_low_confidence_rejected():
    """Scenario 3: Image with low vision confidence -> REJECT."""
    post = Post(title="Wildlife", content="Wildlife animals in nature.")
    
    # Below confidence threshold (< 0.70)
    img_low_conf = Image(
        filename="blurry.jpg",
        path="blurry.jpg",
        subject="animal",
        confidence=0.55,
        low_confidence=False
    )
    result1 = check_candidate(post=post, image=img_low_conf, semantic_score=0.80)
    assert result1.accepted is False
    assert "below threshold" in result1.reason

    # Flagged low_confidence=True
    img_flagged = Image(
        filename="flagged.jpg",
        path="flagged.jpg",
        subject="animal",
        confidence=0.75,
        low_confidence=True
    )
    result2 = check_candidate(post=post, image=img_flagged, semantic_score=0.80)
    assert result2.accepted is False
    assert "low vision confidence" in result2.reason


def test_scenario_4_low_semantic_similarity_rejected():
    """Scenario 4: Image below semantic similarity threshold (< 0.60) -> REJECT."""
    post = Post(title="Space Exploration", content="Rockets launched to Mars and beyond.")
    image = Image(
        filename="rover.jpg",
        path="rover.jpg",
        subject="spacecraft",
        category="aerospace",
        confidence=0.90,
        low_confidence=False
    )
    result = check_candidate(post=post, image=image, semantic_score=0.45)
    assert result.accepted is False
    assert "below threshold" in result.reason


def test_scenario_5_category_mismatch_rejected():
    """Scenario 5: Clear category conflict -> REJECT."""
    post = Post(title="Cloud Server Optimization", content="Deep dive into cloud computing and server infrastructure.")
    image = Image(
        filename="pasta.jpg",
        path="pasta.jpg",
        subject="spaghetti dish",
        category="food",
        confidence=0.95,
        low_confidence=False
    )
    result = check_candidate(post=post, image=image, semantic_score=0.68)
    assert result.accepted is False
    assert "Category conflict" in result.reason


def test_scenario_6_ambiguous_wildlife_bear_not_rejected():
    """Scenario 6: Ambiguous article ('Wildlife photography in winter') + bear image -> NOT rejected."""
    post = Post(title="Winter Wonders", content="Wildlife photography in winter across northern forests.")
    image = Image(
        filename="bear.jpg",
        path="bear.jpg",
        subject="bear",
        category="wildlife",
        confidence=0.89,
        low_confidence=False
    )
    result = check_candidate(post=post, image=image, semantic_score=0.72)
    assert result.accepted is True


def test_scenario_7_rejected_suggestions_persisted(db_session):
    """Scenario 7: Rejected suggestions are persisted with status REJECTED and explanation."""
    post = Post(title="Red Fox Habitat", content="Detailed guide on the red fox habitat.")
    db_session.add(post)
    db_session.commit()
    db_session.add(Embedding(post_id=post.id, vector=[1.0, 0.0], model_name="test"))

    # Conflicting wolf image with identical vector
    wolf_img = Image(
        filename="wolf.jpg",
        path="wolf.jpg",
        subject="wolf",
        confidence=0.90,
        low_confidence=False,
        status="COMPLETED"
    )
    db_session.add(wolf_img)
    db_session.commit()
    db_session.add(Embedding(image_id=wolf_img.id, vector=[1.0, 0.0], model_name="test"))
    db_session.commit()

    response = rank_images_for_post(db_session, post.id, limit=5)
    
    # Candidate should NOT be returned in ranked candidates
    assert len(response.candidates) == 0

    # But MUST be persisted in suggestions as REJECTED
    persisted = db_session.query(Suggestion).filter(
        Suggestion.post_id == post.id,
        Suggestion.image_id == wolf_img.id
    ).first()
    assert persisted is not None
    assert persisted.status == "REJECTED"
    assert "Clear subject conflict" in persisted.explanation


def test_scenario_8_ranking_idempotency_with_guard(db_session):
    """Scenario 8: Repeated ranking does not create duplicate suggestions."""
    post = Post(title="Red Fox", content="Red fox in the forest.")
    db_session.add(post)
    db_session.commit()
    db_session.add(Embedding(post_id=post.id, vector=[1.0, 0.0], model_name="test"))

    # Image 1: Matching fox
    fox_img = Image(filename="f.jpg", path="f.jpg", subject="red fox", confidence=0.85, status="COMPLETED")
    # Image 2: Conflicting wolf
    wolf_img = Image(filename="w.jpg", path="w.jpg", subject="wolf", confidence=0.85, status="COMPLETED")
    db_session.add_all([fox_img, wolf_img])
    db_session.commit()

    db_session.add(Embedding(image_id=fox_img.id, vector=[1.0, 0.0], model_name="test"))
    db_session.add(Embedding(image_id=wolf_img.id, vector=[1.0, 0.0], model_name="test"))
    db_session.commit()

    # Run ranking twice
    rank_images_for_post(db_session, post.id, limit=5)
    rank_images_for_post(db_session, post.id, limit=5)

    # Exactly 2 suggestions total (1 PENDING, 1 REJECTED)
    total_suggestions = db_session.query(Suggestion).filter(Suggestion.post_id == post.id).all()
    assert len(total_suggestions) == 2

    statuses = {s.image_id: s.status for s in total_suggestions}
    assert statuses[fox_img.id] == "PENDING"
    assert statuses[wolf_img.id] == "REJECTED"
