"""Database engine and session management.

"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings

settings = get_settings()

# Create standard SQLAlchemy engine using database URL from settings
engine = create_engine(str(settings.DATABASE_URL))

# Session factory for generating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    Ensures the session is cleanly closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
