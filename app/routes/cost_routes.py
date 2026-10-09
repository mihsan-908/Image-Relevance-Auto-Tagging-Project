"""API routes for inspecting AI API call costs and usage."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cost import APICallCost
from app.schemas.cost_schema import APICallCostResponse, CostSummaryResponse
from app.services.cost_tracking_service import get_cost_summary

router = APIRouter()


@router.get(
    "/costs/summary",
    response_model=CostSummaryResponse,
    summary="Get aggregated AI API cost summary",
    tags=["Cost Tracking"],
)
def get_costs_summary(db: Session = Depends(get_db)):
    """Retrieve total API calls, token counts, and total estimated USD expenditure."""
    return get_cost_summary(db)


@router.get(
    "/costs",
    response_model=list[APICallCostResponse],
    summary="List individual AI API call records",
    tags=["Cost Tracking"],
)
def list_api_costs(limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve detailed per-call cost and token usage records."""
    return (
        db.query(APICallCost)
        .order_by(APICallCost.created_at.desc())
        .limit(limit)
        .all()
    )
