from datetime import datetime
from sqlalchemy import Boolean, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Review(Base):
    """Represents a human review decision (approval or rejection) on an AI Suggestion."""
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    suggestion_id: Mapped[int] = mapped_column(ForeignKey("suggestions.id", ondelete="CASCADE"), nullable=False)
    
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    suggestion: Mapped["Suggestion"] = relationship("Suggestion", back_populates="reviews")
