"""Gemini Vision classification service.

"""

import os
from google.genai import types
from sqlalchemy.orm import Session
from app.services.gemini_client import get_gemini_client
from app.schemas.image_metadata import ImageMetadataSchema
from app.services.cost_tracking_service import record_vision_api_cost

VISION_MODEL_NAME = "gemini-2.0-flash"


def analyze_image_file(
    image_path: str,
    mime_type: str = "image/png",
    db: Session | None = None,
) -> ImageMetadataSchema:
    """Analyze a single image file using Gemini Vision and return validated metadata.

    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found at path: {image_path}")

    client = get_gemini_client()

    # Read image file bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = (
        "Analyze this image carefully and return structured metadata. "
        "Provide: "
        "1. subject: The main subject visible in the image. "
        "2. category: The primary category (e.g. wildlife, domestic, nature, abstract). "
        "3. attributes: A list of key visual features observed. "
        "4. caption: A concise descriptive summary caption of the image. "
        "5. confidence: A confidence score from 0.0 to 1.0 reflecting analysis certainty."
    )

    # Call Gemini model requesting structured JSON output
    response = client.models.generate_content(
        model=VISION_MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ImageMetadataSchema,
        ),
    )

    # Parse and validate the response using Pydantic model
    raw_text = response.text
    if not raw_text:
        raise ValueError("Gemini returned an empty response.")

    validated_result = ImageMetadataSchema.model_validate_json(raw_text)

    # If call succeeded and db session is provided, record usage and cost
    if db is not None:
        input_tokens = 258
        output_tokens = 100
        if hasattr(response, "usage_metadata") and response.usage_metadata is not None:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 258) or 258
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 100) or 100

        record_vision_api_cost(
            db=db,
            model_name=VISION_MODEL_NAME,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return validated_result
