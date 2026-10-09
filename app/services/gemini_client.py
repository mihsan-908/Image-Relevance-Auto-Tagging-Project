"""Gemini client initialization module.

"""

from google import genai
from app.config import get_settings


def get_gemini_client() -> genai.Client:
    """Initialize and return a Google Gemini client instance.

    """
    settings = get_settings()

    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "" or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return client
