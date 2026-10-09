"""Unit tests for background batch jobs service and API endpoints."""

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models.job import BatchJob
from app.main import app
from app.database import get_db
from app.services.batch_processor import BatchSummary
from app.services.job_service import (
    create_batch_job,
    get_batch_job,
    list_batch_jobs,
    execute_batch_job,
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
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_batch_job(db_session):
    """Verify creating and retrieving a batch job record."""
    job = create_batch_job(db=db_session, directory="data/images")

    assert job.id is not None
    assert job.status == "PENDING"
    assert job.directory == "data/images"

    retrieved = get_batch_job(db=db_session, job_id=job.id)
    assert retrieved.id == job.id
    assert retrieved.status == "PENDING"

    jobs = list_batch_jobs(db=db_session)
    assert len(jobs) == 1


def test_get_nonexistent_job_raises(db_session):
    """Verify querying an invalid job ID raises a ValueError."""
    with pytest.raises(ValueError, match="Batch job with ID 999 does not exist"):
        get_batch_job(db=db_session, job_id=999)


def test_execute_batch_job_success(db_session):
    """Verify execute_batch_job updates job status to COMPLETED upon success."""
    job = create_batch_job(db=db_session, directory="data/images")

    dummy_summary = BatchSummary(
        total=5,
        completed=4,
        failed=0,
        skipped=1,
        low_confidence=0,
    )

    with patch("app.services.job_service.SessionLocal", side_effect=TestingSessionLocal):
        with patch("app.services.job_service.process_image_batch", return_value=dummy_summary):
            execute_batch_job(job_id=job.id, directory="data/images")

    session = TestingSessionLocal()
    updated_job = session.query(BatchJob).filter(BatchJob.id == job.id).first()
    assert updated_job.status == "COMPLETED"
    assert updated_job.completed_count == 4
    assert updated_job.skipped_count == 1
    assert updated_job.completed_at is not None
    session.close()


def test_job_api_endpoints(client, db_session):
    """Verify POST /jobs/images/process and GET /jobs/{id} endpoints."""
    # 1. Trigger background job
    with patch("app.routes.job_routes.execute_batch_job"):
        post_resp = client.post(
            "/jobs/images/process",
            json={"directory": "data/images"},
        )
        assert post_resp.status_code == 202
        data = post_resp.json()
        assert data["status"] == "PENDING"
        assert data["directory"] == "data/images"
        job_id = data["id"]

    # 2. Inspect job status via GET /jobs/{id}
    get_resp = client.get(f"/jobs/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["id"] == job_id

    # 3. List all jobs via GET /jobs
    list_resp = client.get("/jobs")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
