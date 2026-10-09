"""Service for tracking API token usage and estimated costs per AI call.

Tracks:
1. Gemini Vision calls (input tokens, output tokens, estimated USD cost)
2. Gemini Embedding calls (input tokens, estimated USD cost)

"""

from sqlalchemy.orm import Session
from app.models.cost import APICallCost

# Pricing constants (USD per token)
VISION_INPUT_COST_PER_TOKEN = 0.000000075
VISION_OUTPUT_COST_PER_TOKEN = 0.000000300
EMBEDDING_INPUT_COST_PER_TOKEN = 0.000000020


def calculate_vision_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD for a vision model call."""
    input_cost = input_tokens * VISION_INPUT_COST_PER_TOKEN
    output_cost = output_tokens * VISION_OUTPUT_COST_PER_TOKEN
    return input_cost + output_cost


def calculate_embedding_cost(input_tokens: int) -> float:
    """Calculate estimated cost in USD for an embedding model call."""
    return input_tokens * EMBEDDING_INPUT_COST_PER_TOKEN


def record_vision_api_cost(
    db: Session,
    model_name: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> APICallCost:
    """Record cost and token usage for a successful Gemini Vision API call.

    Args:
        db: SQLAlchemy session.
        model_name: Name of the vision model used.
        input_tokens: Number of prompt/image input tokens.
        output_tokens: Number of completion output tokens.

    Returns:
        APICallCost: Saved database record.
    """
    inp = input_tokens or 0
    out = output_tokens or 0
    total = inp + out
    estimated_cost = calculate_vision_cost(inp, out)

    cost_record = APICallCost(
        operation_type="VISION_CLASSIFICATION",
        model_name=model_name,
        input_tokens=inp,
        output_tokens=out,
        total_tokens=total,
        estimated_cost=estimated_cost,
    )
    db.add(cost_record)
    db.commit()
    db.refresh(cost_record)
    return cost_record


def record_embedding_api_cost(
    db: Session,
    model_name: str,
    input_tokens: int | None = None,
) -> APICallCost:
    """Record cost and token usage for a successful Gemini Embedding API call.

    Args:
        db: SQLAlchemy session.
        model_name: Name of the embedding model used.
        input_tokens: Number of text input tokens.

    Returns:
        APICallCost: Saved database record.
    """
    inp = input_tokens or 0
    total = inp
    estimated_cost = calculate_embedding_cost(inp)

    cost_record = APICallCost(
        operation_type="TEXT_EMBEDDING",
        model_name=model_name,
        input_tokens=inp,
        output_tokens=0,
        total_tokens=total,
        estimated_cost=estimated_cost,
    )
    db.add(cost_record)
    db.commit()
    db.refresh(cost_record)
    return cost_record


def get_cost_summary(db: Session) -> dict:
    """Calculate total API calls, token counts, and total estimated cost.

    Args:
        db: SQLAlchemy session.

    Returns:
        dict: Aggregated cost summary.
    """
    records = db.query(APICallCost).all()

    total_calls = len(records)
    vision_calls = 0
    embedding_calls = 0
    total_tokens = 0
    total_cost = 0.0

    for r in records:
        if r.operation_type == "VISION_CLASSIFICATION":
            vision_calls += 1
        elif r.operation_type == "TEXT_EMBEDDING":
            embedding_calls += 1

        if r.total_tokens:
            total_tokens += r.total_tokens
        if r.estimated_cost:
            total_cost += r.estimated_cost

    return {
        "total_api_calls": total_calls,
        "vision_calls": vision_calls,
        "embedding_calls": embedding_calls,
        "total_tokens": total_tokens,
        "total_estimated_cost_usd": round(total_cost, 6),
    }
