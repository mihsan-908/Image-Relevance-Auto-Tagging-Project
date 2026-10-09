from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Tag(Base):
    """Represents an auto-generated or manual tag associated with an Image.

    For example, 'red fox', 'wildlife', 'forest'.
    """
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Relationship back to Image
    image: Mapped["Image"] = relationship("Image", back_populates="tags")
