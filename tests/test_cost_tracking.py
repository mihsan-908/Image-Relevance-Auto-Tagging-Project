"""Unit tests for AI usage and cost tracking service and endpoints."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models.cost import APICallCost
from app.main import app
from app.database import get_db
from app.services.cost_tracking_service import (
    calculate_vision_cost,
    calculate_embedding_cost,
    record_vision_api_cost,
    record_embedding_api_cost,
    get_cost_summary,
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh in-memory database tables for each test."""
    Base.metadata.create_all(engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_vision_cost_calculation():
    """Verify vision cost calculation formula."""
    # 1000 input tokens ($0.075/1M) + 100 output tokens ($0.30/1M)
    # input: 1000 * 0.000000075 = 0.000075
    # output: 100 * 0.000000300 = 0.000030
    # total = 0.000105
    cost = calculate_vision_cost(input_tokens=1000, output_tokens=100)
    assert abs(cost - 0.000105) < 1e-8


def test_embedding_cost_calculation():
    """Verify embedding cost calculation formula."""
    # 10,000 input tokens ($0.02/1M) = 10000 * 0.00000002 = 0.0002
    cost = calculate_embedding_cost(input_tokens=10000)
    assert abs(cost - 0.0002) < 1e-8


def test_record_vision_cost_db(db_session):
    """Verify recording a vision API cost record in database."""
    record = record_vision_api_cost(
        db=db_session,
        model_name="gemini-2.5-flash",
        input_tokens=258,
        output_tokens=120,
    )

    assert record.id is not None
    assert record.operation_type == "VISION_CLASSIFICATION"
    assert record.model_name == "gemini-2.5-flash"
    assert record.input_tokens == 258
    assert record.output_tokens == 120
    assert record.total_tokens == 378
    assert record.estimated_cost is not None
    assert record.estimated_cost > 0.0


def test_record_embedding_cost_db(db_session):
    """Verify recording an embedding API cost record in database."""
    record = record_embedding_api_cost(
        db=db_session,
        model_name="gemini-embedding-001",
        input_tokens=150,
    )

    assert record.id is not None
    assert record.operation_type == "TEXT_EMBEDDING"
    assert record.model_name == "gemini-embedding-001"
    assert record.input_tokens == 150
    assert record.output_tokens == 0
    assert record.total_tokens == 150
    assert record.estimated_cost is not None
    assert record.estimated_cost > 0.0


def test_cost_summary_aggregation(db_session):
    """Verify aggregating summary metrics across multiple API calls."""
    record_vision_api_cost(db=db_session, model_name="gemini-2.5-flash", input_tokens=200, output_tokens=100)
    record_vision_api_cost(db=db_session, model_name="gemini-2.5-flash", input_tokens=300, output_tokens=150)
    record_embedding_api_cost(db=db_session, model_name="gemini-embedding-001", input_tokens=500)

    summary = get_cost_summary(db=db_session)
    assert summary["total_api_calls"] == 3
    assert summary["vision_calls"] == 2
    assert summary["embedding_calls"] == 1
    assert summary["total_tokens"] == (200 + 100) + (300 + 150) + 500
    assert summary["total_estimated_cost_usd"] > 0.0


def test_cost_api_endpoints(client, db_session):
    """Verify FastAPI GET /costs and GET /costs/summary endpoints."""
    record_vision_api_cost(db=db_session, model_name="gemini-2.5-flash", input_tokens=258, output_tokens=100)

    # 1. Test /costs/summary
    summary_resp = client.get("/costs/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_api_calls"] == 1
    assert summary_data["vision_calls"] == 1
    assert summary_data["embedding_calls"] == 0

    # 2. Test /costs
    list_resp = client.get("/costs")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert len(list_data) == 1
    assert list_data[0]["operation_type"] == "VISION_CLASSIFICATION"
