"""Configuration module.

"""

import os
from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    """

    # Provide a placeholder that allows the app to start; users should replace it.
    DATABASE_URL: PostgresDsn = Field(
        "postgresql+psycopg2://postgres:YOURPASSWORD@localhost:5432/image_relevance_auto_tagging",
        env="DATABASE_URL",
    )
    GEMINI_API_KEY: str | None = Field(default=None, env="GEMINI_API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Return a new Settings instance.

    """
    return Settings()
