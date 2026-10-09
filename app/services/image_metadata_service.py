"""Service for persisting image metadata and tags to PostgreSQL.

Handles saving the validated Gemini Vision metadata onto the Image record,
determining confidence flags, and creating unique Tag records safely.
"""

from sqlalchemy.orm import Session
from app.models.image import Image
from app.models.tag import Tag
from app.schemas.image_metadata import ImageMetadataSchema

# Project decision: We consider confidence below 0.70 as "low confidence".
# This flag will be used later in the mismatch guard flow.
LOW_CONFIDENCE_THRESHOLD = 0.70


def save_image_metadata(db: Session, image: Image, metadata: ImageMetadataSchema) -> Image:
    """Save the validated metadata to the image and generate tags.

    This function operates within a single transaction. If tag creation fails,
    the image update is rolled back.

    Args:
        db: The SQLAlchemy database session.
        image: The existing Image database record to update.
        metadata: The validated metadata from Gemini Vision.

    Returns:
        The updated Image record.
    """
    try:
        # 1. Update the Image record with explicit metadata columns
        image.subject = metadata.subject
        image.category = metadata.category
        image.caption = metadata.caption
        image.attributes = metadata.attributes
        
        # 2. Update confidence and set the low_confidence flag
        image.confidence = metadata.confidence
        image.low_confidence = metadata.confidence < LOW_CONFIDENCE_THRESHOLD
        
        # Mark as processed successfully
        image.status = "COMPLETED"

        db.add(image)
        
        # 3. Create searchable tags
        # Collect all tag strings we want to save
        new_tag_names = set()
        if metadata.subject:
            new_tag_names.add(metadata.subject.strip().lower())
        if metadata.category:
            new_tag_names.add(metadata.category.strip().lower())
        if metadata.attributes:
            for attr in metadata.attributes:
                new_tag_names.add(attr.strip().lower())
        
        # Find existing tags to prevent duplicates on this image
        existing_tags = {tag.name.lower() for tag in image.tags}
        
        # Create new tags that don't already exist for this image
        for tag_name in new_tag_names:
            if tag_name not in existing_tags:
                new_tag = Tag(image_id=image.id, name=tag_name)
                db.add(new_tag)
                # Keep track locally in case of duplicates within the same run
                existing_tags.add(tag_name)

        # 4. Commit the transaction safely
        db.commit()
        db.refresh(image)
        
        return image
        
    except Exception as e:
        db.rollback()
        raise e
