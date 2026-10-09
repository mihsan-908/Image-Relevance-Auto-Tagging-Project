"""Service for calling the Gemini Embedding API."""

import time
from sqlalchemy.orm import Session
from google.genai import types
from app.services.gemini_client import get_gemini_client
from app.schemas.embedding_schema import EmbeddingSchema
from app.services.cost_tracking_service import record_embedding_api_cost

# Central constants for embeddings so they are consistent across the app
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONALITY = 768


def generate_embedding(text: str, db: Session | None = None) -> EmbeddingSchema:
    """Generate an embedding vector for the given text using Gemini.

    Retries up to 2 times on transient network hiccups.

    Args:
        text: The text to embed.
        db: Optional SQLAlchemy session for recording API cost.

    Returns:
        EmbeddingSchema: A validated schema containing the vector and metadata.
    """
    client = get_gemini_client()
    last_error = None

    for attempt in range(3):
        try:
            # Call Gemini embedding API
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIMENSIONALITY
                ),
            )

            # The response contains a list of embeddings. Since we passed one text,
            # we take the first embedding's values.
            vector = response.embeddings[0].values

            if not vector:
                raise ValueError("Received an empty vector from Gemini.")

            # Validate the result using our simple schema
            result = EmbeddingSchema(
                vector=vector,
                model_name=EMBEDDING_MODEL,
                dimensionality=len(vector),
            )

            # Record cost if db session is provided
            if db is not None:
                # Estimate input tokens based on character length (~4 chars per token)
                estimated_tokens = max(1, len(text) // 4)
                record_embedding_api_cost(
                    db=db,
                    model_name=EMBEDDING_MODEL,
                    input_tokens=estimated_tokens,
                )

            return result

        except Exception as e:
            last_error = e
            if attempt < 2:
                time.sleep(1.0)

    raise last_error
