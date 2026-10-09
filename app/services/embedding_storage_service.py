"""Service for storing embeddings in PostgreSQL."""

from sqlalchemy.orm import Session
from app.models.image import Image
from app.models.post import Post
from app.models.embedding import Embedding
from app.services.text_representation_service import build_image_embedding_text, build_post_embedding_text
from app.services.embedding_generation_service import generate_embedding


def store_image_embedding(db: Session, image: Image) -> Embedding:
    """Generate and store an embedding for an Image.
    
    If an embedding already exists for this image, it updates the existing row
    to ensure idempotency.
    
    Args:
        db: SQLAlchemy session
        image: The Image model to embed
        
    Returns:
        The created or updated Embedding database record.
    """
    # 1. Build text representation
    text = build_image_embedding_text(image)
    
    if not text.strip():
        raise ValueError("Image text representation is empty. Cannot generate embedding.")
        
    # 2. Call Gemini (recording cost via db)
    result = generate_embedding(text, db=db)
    
    # 3. Check for existing embedding (Idempotency)
    embedding_record = db.query(Embedding).filter(Embedding.image_id == image.id).first()
    
    if embedding_record:
        # Update existing
        embedding_record.vector = result.vector
        embedding_record.model_name = result.model_name
    else:
        # Create new
        embedding_record = Embedding(
            image_id=image.id,
            vector=result.vector,
            model_name=result.model_name
        )
        db.add(embedding_record)
        
    db.commit()
    db.refresh(embedding_record)
    
    return embedding_record


def store_post_embedding(db: Session, post: Post) -> Embedding:
    """Generate and store an embedding for a Post.
    
    If an embedding already exists for this post, it updates the existing row
    to ensure idempotency.
    
    Args:
        db: SQLAlchemy session
        post: The Post model to embed
        
    Returns:
        The created or updated Embedding database record.
    """
    # 1. Build text representation
    text = build_post_embedding_text(post)
    
    if not text.strip():
        raise ValueError("Post text representation is empty. Cannot generate embedding.")
        
    # 2. Call Gemini (recording cost via db)
    result = generate_embedding(text, db=db)
    
    # 3. Check for existing embedding (Idempotency)
    embedding_record = db.query(Embedding).filter(Embedding.post_id == post.id).first()
    
    if embedding_record:
        # Update existing
        embedding_record.vector = result.vector
        embedding_record.model_name = result.model_name
    else:
        # Create new
        embedding_record = Embedding(
            post_id=post.id,
            vector=result.vector,
            model_name=result.model_name
        )
        db.add(embedding_record)
        
    db.commit()
    db.refresh(embedding_record)
    
    return embedding_record
