"""Service for handling review actions and querying suggestions.

Provides straightforward functions to:
- list suggestions for a post
- get a suggestion with its details
- approve a suggestion
- reject a suggestion
"""

from sqlalchemy.orm import Session
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.models.review import Review
from app.schemas.review_schema import (
    SuggestionDetailResponse,
    SuggestionListItemResponse,
    ImageSummarySchema,
    PostSummarySchema,
    ReviewResponse,
)


def get_suggestions_for_post(db: Session, post_id: int) -> list[SuggestionListItemResponse]:
    """Retrieve all suggestions for a given post.

    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise ValueError(f"Post with ID {post_id} does not exist.")

    suggestions = (
        db.query(Suggestion)
        .filter(Suggestion.post_id == post_id)
        .order_by(Suggestion.score.desc())
        .all()
    )

    items = []
    for s in suggestions:
        # Determine whether suggestion was accepted by mismatch guard
        is_guard_rejected = s.explanation and "Rejected by mismatch guard" in s.explanation
        accepted_by_guard = not is_guard_rejected

        image = s.image
        items.append(
            SuggestionListItemResponse(
                id=s.id,
                post_id=s.post_id,
                image_id=s.image_id,
                score=s.score,
                status=s.status,
                explanation=s.explanation,
                accepted_by_guard=accepted_by_guard,
                image_subject=image.subject if image else None,
                image_category=image.category if image else None,
                image_confidence=image.confidence if image else None,
                image_filename=image.filename if image else "",
            )
        )

    return items


def get_suggestion_detail(db: Session, suggestion_id: int) -> SuggestionDetailResponse:
    """Retrieve full details of a single suggestion.

    """
    suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not suggestion:
        raise ValueError(f"Suggestion with ID {suggestion_id} does not exist.")

    is_guard_rejected = suggestion.explanation and "Rejected by mismatch guard" in suggestion.explanation
    accepted_by_guard = not is_guard_rejected

    image = suggestion.image
    post = suggestion.post

    image_summary = None
    if image:
        image_summary = ImageSummarySchema(
            id=image.id,
            filename=image.filename,
            subject=image.subject,
            category=image.category,
            caption=image.caption,
            confidence=image.confidence,
            low_confidence=image.low_confidence,
        )

    post_summary = None
    if post:
        post_summary = PostSummarySchema(
            id=post.id,
            title=post.title,
            content=post.content,
        )

    review_list = [
        ReviewResponse(
            id=r.id,
            suggestion_id=r.suggestion_id,
            approved=r.approved,
            reason=r.reason,
            reviewed_at=r.reviewed_at,
        )
        for r in suggestion.reviews
    ]

    return SuggestionDetailResponse(
        id=suggestion.id,
        post_id=suggestion.post_id,
        image_id=suggestion.image_id,
        score=suggestion.score,
        status=suggestion.status,
        explanation=suggestion.explanation,
        accepted_by_guard=accepted_by_guard,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
        image=image_summary,
        post=post_summary,
        reviews=review_list,
    )


def review_suggestion(
    db: Session,
    suggestion_id: int,
    approved: bool,
    reason: str | None = None,
) -> SuggestionDetailResponse:
    """Apply a human review decision (approve or reject) to a suggestion.

    Updates suggestion status to APPROVED or REJECTED.
    Idempotent: updates existing Review record if present for this suggestion,
    otherwise creates a new one.

    """
    suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not suggestion:
        raise ValueError(f"Suggestion with ID {suggestion_id} does not exist.")

    # Update suggestion status
    suggestion.status = "APPROVED" if approved else "REJECTED"

    # Check for existing review record to avoid duplicates
    existing_review = (
        db.query(Review)
        .filter(Review.suggestion_id == suggestion_id)
        .first()
    )

    if existing_review:
        existing_review.approved = approved
        existing_review.reason = reason
    else:
        new_review = Review(
            suggestion_id=suggestion_id,
            approved=approved,
            reason=reason,
        )
        db.add(new_review)

    db.commit()
    db.refresh(suggestion)

    return get_suggestion_detail(db, suggestion_id)
