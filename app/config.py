"""LegalLens AI — Application configuration."""

import os
from pathlib import Path


class BaseConfig:
    """Base configuration shared across all environments."""

    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-change-in-production")

    # Upload settings
    MAX_UPLOAD_SIZE_MB: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "10"))
    MAX_CONTENT_LENGTH: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    UPLOAD_FOLDER: str = os.environ.get("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx", "txt"})

    # AI settings
    GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
    AI_MODEL_NAME: str = os.environ.get("AI_MODEL_NAME", "gemini-3.6-flash")
    AI_MAX_RETRIES: int = int(os.environ.get("AI_MAX_RETRIES", "3"))
    AI_TIMEOUT_SECONDS: int = int(os.environ.get("AI_TIMEOUT_SECONDS", "60"))
    AI_MAX_CONTEXT_CHUNKS: int = int(os.environ.get("AI_MAX_CONTEXT_CHUNKS", "10"))

    # Logging
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # Document processing
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200
    MAX_DOCUMENT_CHARS: int = 500_000


class DevelopmentConfig(BaseConfig):
    """Development configuration."""

    DEBUG: bool = True


class TestingConfig(BaseConfig):
    """Testing configuration — no real AI calls."""

    TESTING: bool = True
    GOOGLE_API_KEY: str = "test-key-not-real"
    UPLOAD_FOLDER: str = "test_uploads"
    MAX_UPLOAD_SIZE_MB: int = 1
    MAX_CONTENT_LENGTH: int = 1 * 1024 * 1024


class ProductionConfig(BaseConfig):
    """Production configuration."""

    DEBUG: bool = False


CONFIG_MAP: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config() -> BaseConfig:
    """Get configuration based on FLASK_ENV environment variable."""
    env = os.environ.get("FLASK_ENV", "development")
    config_class = CONFIG_MAP.get(env, DevelopmentConfig)
    return config_class()
