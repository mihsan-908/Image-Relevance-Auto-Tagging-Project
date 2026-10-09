"""API routes for background batch processing jobs."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.job_schema import CreateJobRequest, BatchJobResponse
from app.services.job_service import (
    create_batch_job,
    execute_batch_job,
    get_batch_job,
    list_batch_jobs,
)

router = APIRouter()


@router.post(
    "/jobs/images/process",
    response_model=BatchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger background batch image processing",
    tags=["Batch Jobs"],
)
def start_batch_processing_job(
    request: CreateJobRequest = CreateJobRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Initiates an asynchronous background job to process an image directory.

    Returns HTTP 202 with the pending job ID immediately, then processes images
    asynchronously using FastAPI BackgroundTasks.
    """
    job = create_batch_job(db=db, directory=request.directory)
    background_tasks.add_task(execute_batch_job, job.id, request.directory)
    return job


@router.get(
    "/jobs/{job_id}",
    response_model=BatchJobResponse,
    summary="Get background job status and progress",
    tags=["Batch Jobs"],
)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Retrieve current status, progress counts, and metrics for a background job."""
    try:
        return get_batch_job(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/jobs",
    response_model=list[BatchJobResponse],
    summary="List all background jobs",
    tags=["Batch Jobs"],
)
def list_jobs(db: Session = Depends(get_db)):
    """Retrieve a list of all background batch jobs."""
    return list_batch_jobs(db)
