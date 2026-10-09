from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Embedding(Base):
    """Stores vector embeddings for either an Image or a Post.

    The vector is stored as a JSON array of float values to keep setup simple
    without requiring third-party database extensions like pgvector.
    """
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    
    # JSON list of numbers representing the vector values
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    image: Mapped["Image | None"] = relationship("Image", back_populates="embeddings")
    post: Mapped["Post | None"] = relationship("Post", back_populates="embeddings")
