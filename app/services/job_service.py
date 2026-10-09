"""Service for managing asynchronous background batch jobs."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.job import BatchJob
from app.services.batch_processor import process_image_batch


def create_batch_job(db: Session, directory: str = "data/images") -> BatchJob:
    """Create a new batch job in PENDING status.

    Args:
        db: SQLAlchemy database session.
        directory: Image directory path to process.

    Returns:
        BatchJob: Newly created database record.
    """
    job = BatchJob(
        directory=directory,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def execute_batch_job(job_id: int, directory: str) -> None:
    """Worker function executed in the background by FastAPI BackgroundTasks.

    Opens its own DB session, updates status, executes batch processing,
    and records completion.

    Args:
        job_id: The ID of the BatchJob record.
        directory: Image directory path to process.
    """
    db: Session = SessionLocal()
    try:
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            return

        job.status = "PROCESSING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        # Run batch processor (passes job_id to update progress in real time)
        summary = process_image_batch(directory=directory, db=db, job_id=job_id)

        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        job.completed_count = summary.completed
        job.failed_count = summary.failed
        job.skipped_count = summary.skipped
        job.low_confidence_count = summary.low_confidence
        db.commit()

    except Exception as e:
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def get_batch_job(db: Session, job_id: int) -> BatchJob:
    """Retrieve details for a specific batch job.

    """
    job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
    if not job:
        raise ValueError(f"Batch job with ID {job_id} does not exist.")
    return job


def list_batch_jobs(db: Session) -> list[BatchJob]:
    """List all batch jobs ordered by creation date descending."""
    return db.query(BatchJob).order_by(BatchJob.created_at.desc()).all()
