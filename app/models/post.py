from datetime import datetime
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Post(Base):
    """Represents a blog post or article in the system.

    Posts are matched against images in the library using vector similarity.
    """
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    embeddings: Mapped[list["Embedding"]] = relationship("Embedding", back_populates="post", cascade="all, delete-orphan")
    suggestions: Mapped[list["Suggestion"]] = relationship("Suggestion", back_populates="post", cascade="all, delete-orphan")
