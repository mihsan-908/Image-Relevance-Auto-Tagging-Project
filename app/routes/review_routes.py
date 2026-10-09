"""API routes for inspecting and reviewing image suggestions."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.review_schema import (
    ReviewActionRequest,
    SuggestionDetailResponse,
    SuggestionListItemResponse,
)
from app.services.review_service import (
    get_suggestions_for_post,
    get_suggestion_detail,
    review_suggestion,
)

router = APIRouter()


@router.get(
    "/posts/{post_id}/suggestions",
    response_model=list[SuggestionListItemResponse],
    summary="List suggestions for a post",
    tags=["Suggestions"],
)
def list_suggestions_for_post(post_id: int, db: Session = Depends(get_db)):
    """Retrieve all image suggestions for a specific blog post."""
    try:
        return get_suggestions_for_post(db, post_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/suggestions/{suggestion_id}",
    response_model=SuggestionDetailResponse,
    summary="Get suggestion details",
    tags=["Suggestions"],
)
def get_suggestion(suggestion_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of a specific image suggestion."""
    try:
        return get_suggestion_detail(db, suggestion_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/suggestions/{suggestion_id}/approve",
    response_model=SuggestionDetailResponse,
    summary="Approve a suggestion",
    tags=["Reviews"],
)
def approve_suggestion(
    suggestion_id: int,
    action: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db),
):
    """Approve an image suggestion and record human review decision."""
    try:
        return review_suggestion(db, suggestion_id, approved=True, reason=action.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/suggestions/{suggestion_id}/reject",
    response_model=SuggestionDetailResponse,
    summary="Reject a suggestion",
    tags=["Reviews"],
)
def reject_suggestion(
    suggestion_id: int,
    action: ReviewActionRequest = ReviewActionRequest(),
    db: Session = Depends(get_db),
):
    """Reject an image suggestion and record human review decision."""
    try:
        return review_suggestion(db, suggestion_id, approved=False, reason=action.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
