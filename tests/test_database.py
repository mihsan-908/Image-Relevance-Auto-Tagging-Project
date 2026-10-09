"""Database connection and model metadata tests for Stage 1.

These tests verify that:
1. All SQLAlchemy models can be imported cleanly.
2. Base.metadata contains the 6 required table schemas.
3. The application can connect to PostgreSQL using DATABASE_URL from settings.
4. The required tables actually exist in the target database.

No data is inserted, updated, or deleted during these tests.
"""

from sqlalchemy import create_engine, inspect, text
from app.config import get_settings
from app.models import Base, Image, Tag, Post, Embedding, Suggestion, Review


def test_models_import_and_metadata():
    """Verify that all 6 models import and are registered in Base.metadata."""
    # List of expected table names defined by our SQLAlchemy models
    expected_tables = {"images", "tags", "posts", "embeddings", "suggestions", "reviews"}
    
    # Get table names registered in SQLAlchemy metadata
    metadata_tables = set(Base.metadata.tables.keys())
    
    # Assert all expected tables exist in metadata
    assert expected_tables.issubset(metadata_tables), (
        f"Missing tables in metadata. Expected {expected_tables}, got {metadata_tables}"
    )


def test_database_connection():
    """Verify that we can establish a live connection to PostgreSQL."""
    settings = get_settings()
    engine = create_engine(str(settings.DATABASE_URL))
    
    # Execute a lightweight query to confirm connection health
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()
        assert result == 1, "Database ping failed"
        
    engine.dispose()


def test_database_tables_exist():
    """Verify that the required tables exist in the connected PostgreSQL database."""
    settings = get_settings()
    engine = create_engine(str(settings.DATABASE_URL))
    
    # Use SQLAlchemy inspector to check table names in the database
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    expected_tables = {"images", "tags", "posts", "embeddings", "suggestions", "reviews"}
    
    assert expected_tables.issubset(existing_tables), (
        f"Missing tables in PostgreSQL database. Expected {expected_tables}, found {existing_tables}"
    )
    
    engine.dispose()
