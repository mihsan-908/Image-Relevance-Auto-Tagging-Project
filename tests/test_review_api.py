"""Tests for the Review API and suggestion endpoints.

Verifies:
1. List suggestions for a post
2. Get a suggestion with full details
3. Suggestion not found returns 404
4. Post not found returns 404 when listing suggestions
5. Approve suggestion marks status APPROVED
6. Reject suggestion marks status REJECTED
7. Review reason is persisted in review table
8. Existing mismatch explanation is preserved
9. Repeated approval does not create duplicate review records
10. Repeated rejection does not create duplicate review records
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.post import Post
from app.models.image import Image
from app.models.suggestion import Suggestion
from app.models.review import Review
from app.main import app
from app.database import get_db

# Create an in-memory SQLite database with StaticPool for thread-safe TestClient operations
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables for each test and override get_db."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    # Override FastAPI dependency to use testing session factory
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()


    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    return TestClient(app)


def test_list_suggestions_for_post(client, db_session):
    """Test listing suggestions for a specific post."""
    post = Post(title="Fox Story", content="A nice fox.")
    image = Image(path="fox.jpg", filename="fox.jpg", subject="red fox", category="wildlife", confidence=0.9, status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.88,
        status="PENDING",
        explanation="Passed mismatch guard."
    )
    db_session.add(suggestion)
    db_session.commit()

    response = client.get(f"/posts/{post.id}/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == suggestion.id
    assert data[0]["image_id"] == image.id
    assert data[0]["image_subject"] == "red fox"
    assert data[0]["accepted_by_guard"] is True
    assert data[0]["score"] == pytest.approx(0.88)


def test_list_suggestions_post_not_found(client, db_session):
    """Test listing suggestions for a non-existent post returns 404."""
    response = client.get("/posts/9999/suggestions")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_get_suggestion_detail(client, db_session):
    """Test getting single suggestion with post and image metadata."""
    post = Post(title="Bird Watching", content="Observing eagles.")
    image = Image(path="bird.jpg", filename="bird.jpg", subject="eagle", category="birds", confidence=0.92, status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.79,
        status="PENDING",
        explanation="High semantic similarity."
    )
    db_session.add(suggestion)
    db_session.commit()

    response = client.get(f"/suggestions/{suggestion.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == suggestion.id
    assert data["post"]["title"] == "Bird Watching"
    assert data["image"]["subject"] == "eagle"
    assert data["reviews"] == []


def test_get_suggestion_not_found(client, db_session):
    """Test getting a non-existent suggestion returns 404."""
    response = client.get("/suggestions/9999")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_approve_suggestion(client, db_session):
    """Test approving a suggestion updates status to APPROVED and creates review record."""
    post = Post(title="Post", content="Content")
    image = Image(path="img.jpg", filename="img.jpg", status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.85,
        status="PENDING",
        explanation="Matched"
    )
    db_session.add(suggestion)
    db_session.commit()

    response = client.post(
        f"/suggestions/{suggestion.id}/approve",
        json={"reason": "Looks great for the article"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["approved"] is True
    assert data["reviews"][0]["reason"] == "Looks great for the article"

    # Verify directly in DB
    db_session.expire_all()
    db_record = db_session.query(Suggestion).filter(Suggestion.id == suggestion.id).first()
    assert db_record.status == "APPROVED"
    assert len(db_record.reviews) == 1



def test_reject_suggestion(client, db_session):
    """Test rejecting a suggestion updates status to REJECTED and preserves guard explanation."""
    post = Post(title="Post", content="Content")
    image = Image(path="img.jpg", filename="img.jpg", status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    guard_explanation = "Passed mismatch guard. Ranked by semantic similarity for human review."
    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.72,
        status="PENDING",
        explanation=guard_explanation
    )
    db_session.add(suggestion)
    db_session.commit()

    response = client.post(
        f"/suggestions/{suggestion.id}/reject",
        json={"reason": "Subject lighting is poor"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REJECTED"
    # Preserves original guard explanation on suggestion
    assert data["explanation"] == guard_explanation
    # Records human rejection reason on review
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["approved"] is False
    assert data["reviews"][0]["reason"] == "Subject lighting is poor"


def test_repeated_approval_idempotency(client, db_session):
    """Test that repeated approval updates the review rather than creating duplicate records."""
    post = Post(title="Post", content="Content")
    image = Image(path="img.jpg", filename="img.jpg", status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.85,
        status="PENDING"
    )
    db_session.add(suggestion)
    db_session.commit()

    # Call approve twice with updated reason
    resp1 = client.post(f"/suggestions/{suggestion.id}/approve", json={"reason": "First review"})
    assert resp1.status_code == 200

    resp2 = client.post(f"/suggestions/{suggestion.id}/approve", json={"reason": "Updated review note"})
    assert resp2.status_code == 200

    reviews = db_session.query(Review).filter(Review.suggestion_id == suggestion.id).all()
    assert len(reviews) == 1
    assert reviews[0].reason == "Updated review note"
    assert reviews[0].approved is True


def test_repeated_rejection_idempotency(client, db_session):
    """Test that repeated rejection updates the review rather than creating duplicate records."""
    post = Post(title="Post", content="Content")
    image = Image(path="img.jpg", filename="img.jpg", status="COMPLETED")
    db_session.add_all([post, image])
    db_session.commit()

    suggestion = Suggestion(
        post_id=post.id,
        image_id=image.id,
        score=0.65,
        status="PENDING"
    )
    db_session.add(suggestion)
    db_session.commit()

    client.post(f"/suggestions/{suggestion.id}/reject", json={"reason": "Initial rejection"})
    client.post(f"/suggestions/{suggestion.id}/reject", json={"reason": "Confirmed rejection"})

    reviews = db_session.query(Review).filter(Review.suggestion_id == suggestion.id).all()
    assert len(reviews) == 1
    assert reviews[0].reason == "Confirmed rejection"
    assert reviews[0].approved is False


def test_review_nonexistent_suggestion_returns_404(client, db_session):
    """Test approving or rejecting a nonexistent suggestion returns 404."""
    resp_approve = client.post("/suggestions/9999/approve", json={"reason": "test"})
    assert resp_approve.status_code == 404

    resp_reject = client.post("/suggestions/9999/reject", json={"reason": "test"})
    assert resp_reject.status_code == 404
