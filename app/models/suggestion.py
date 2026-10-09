from datetime import datetime
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Suggestion(Base):
    """Represents an AI-generated match suggestion connecting an Image to a Post.

    Includes a composite index on (post_id, status) for fast lookup of pending
    or approved suggestions for a given post.
    """
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    
    score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    post: Mapped["Post"] = relationship("Post", back_populates="suggestions")
    image: Mapped["Image"] = relationship("Image", back_populates="suggestions")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="suggestion", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_suggestions_post_id_status", "post_id", "status"),
    )
