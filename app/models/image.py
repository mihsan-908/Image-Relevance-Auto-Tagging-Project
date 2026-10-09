from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Image(Base):
    """Represents an ingested image in the system.

    Stores metadata such as file path, processing status (e.g. PENDING, PROCESSED),
    and AI confidence level.
    """
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Status column indexed for fast filtering of pending/processed images
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True, nullable=False)
    
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Vision Metadata fields populated by Gemini
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    caption: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attributes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="image", cascade="all, delete-orphan")
    embeddings: Mapped[list["Embedding"]] = relationship("Embedding", back_populates="image", cascade="all, delete-orphan")
    suggestions: Mapped[list["Suggestion"]] = relationship("Suggestion", back_populates="image", cascade="all, delete-orphan")
