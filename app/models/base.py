from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models.

    All model classes (Image, Tag, Post, etc.) inherit from this Base class.
    Alembic uses Base.metadata to discover all table definitions and generate migrations.
    """
    pass
