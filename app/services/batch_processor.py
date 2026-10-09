"""Batch image ingestion service.

Processes a directory of images sequentially, sending them to Gemini Vision
and saving metadata to PostgreSQL. Handles retries, failure isolation, and cost tracking.
"""

import os
import time
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Tuple

from app.models.image import Image
from app.models.job import BatchJob
from app.services.vision_service import analyze_image_file
from app.services.image_metadata_service import save_image_metadata

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2


class BatchSummary(BaseModel):
    total: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    low_confidence: int = 0


def get_mime_type(ext: str) -> str:
    """Return basic mime type for supported extensions."""
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def process_image_batch(
    directory: str,
    db: Session,
    job_id: int | None = None,
) -> BatchSummary:
    """Process a directory of images through Gemini Vision.

    Args:
        directory: Path to the local directory containing images.
        db: SQLAlchemy database session.
        job_id: Optional ID of a BatchJob to track progress.

    Returns:
        BatchSummary object with the results.
    """
    summary = BatchSummary()

    if not os.path.isdir(directory):
        print(f"Directory not found: {directory}")
        if job_id is not None:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = f"Directory not found: {directory}"
                db.commit()
        return summary

    # 1. Find supported image files
    image_files = []
    for filename in sorted(os.listdir(directory)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            image_files.append(filename)

    summary.total = len(image_files)

    if job_id is not None:
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if job:
            job.total_images = summary.total
            job.status = "PROCESSING"
            db.commit()

    for idx, filename in enumerate(image_files, 1):
        image_path = os.path.join(directory, filename)
        mime_type = get_mime_type(os.path.splitext(filename)[1].lower())

        print(f"\n[{idx}/{summary.total}] {filename}")

        # 2. Check if image already exists in database
        image = db.query(Image).filter(Image.path == image_path).first()

        if image:
            # 7. Idempotency Check
            if image.status == "COMPLETED":
                print(f"SKIP: {filename} already completed.")
                summary.skipped += 1
                if image.low_confidence:
                    summary.low_confidence += 1

                if job_id is not None:
                    job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
                    if job:
                        job.processed_count = idx
                        job.skipped_count = summary.skipped
                        job.low_confidence_count = summary.low_confidence
                        db.commit()
                continue
        else:
            # Create a new PENDING record
            image = Image(
                path=image_path,
                filename=filename,
                status="PENDING",
            )
            db.add(image)
            db.commit()
            db.refresh(image)

        # 4. Mark PROCESSING
        image.status = "PROCESSING"
        db.add(image)
        db.commit()
        print("PROCESSING")

        success = False

        # 5. Send to Vision Service with Retries and Cost Tracking
        attempts = 0
        max_attempts = MAX_RETRIES + 1

        while attempts < max_attempts:
            attempts += 1
            try:
                # Call Gemini with DB session to track cost
                metadata = analyze_image_file(image_path=image_path, mime_type=mime_type, db=db)
                print("Gemini classification received")

                # 6. Save metadata (updates status to COMPLETED)
                save_image_metadata(db, image, metadata)
                success = True
                print("COMPLETED")
                summary.completed += 1

                # Check low confidence
                if image.low_confidence:
                    summary.low_confidence += 1

                break  

            except Exception as e:
                print(f"Attempt {attempts} failed: {e}")
                if attempts < max_attempts:
                    print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    print("Max retries exhausted.")

        # 8. Handle Failures
        if not success:
            image.status = "FAILED"
            db.add(image)
            db.commit()
            print("FAILED")
            summary.failed += 1

        # Update Job Progress in DB if tracking
        if job_id is not None:
            job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
            if job:
                job.processed_count = idx
                job.completed_count = summary.completed
                job.failed_count = summary.failed
                job.skipped_count = summary.skipped
                job.low_confidence_count = summary.low_confidence
                db.commit()

    return summary
