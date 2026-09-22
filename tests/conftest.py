"""LegalLens AI — Pytest configuration and fixtures."""

import io
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.services.document_service import document_store


@pytest.fixture
def app() -> Flask:
    """Create a Flask application for testing."""
    app = create_app()
    # Force testing config
    app.config.update(
        {
            "TESTING": True,
            "GOOGLE_API_KEY": "test-key-no-real-calls",
            "MAX_CONTENT_LENGTH": 1 * 1024 * 1024,  # 1MB for tests
        }
    )
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_store() -> Generator[None, None, None]:
    """Clear document store before and after each test."""
    document_store._documents.clear()
    document_store._hashes.clear()
    yield
    document_store._documents.clear()
    document_store._hashes.clear()


@pytest.fixture
def mock_ai_client(mocker) -> MagicMock:
    """Mock AI Client that doesn't make network calls."""
    mock = mocker.patch("app.ai.client.AIClient", autospec=True)
    # Default to returning valid JSON for tests
    mock.return_value.generate.return_value = "{}"
    return mock.return_value


@pytest.fixture
def sample_txt_bytes() -> bytes:
    """Sample text document bytes."""
    content = """CONFIDENTIALITY AGREEMENT

This Agreement is made on January 1, 2025.

1. PARTIES
Party A and Party B agree to the following terms.

2. CONFIDENTIALITY
Party B shall keep all information confidential.
This obligation survives termination.

3. TERMINATION
Either party may terminate with 30 days written notice.
"""
    return content.encode("utf-8")


@pytest.fixture
def sample_file(sample_txt_bytes) -> tuple[io.BytesIO, str]:
    """File object for upload tests."""
    return (io.BytesIO(sample_txt_bytes), "test_doc.txt")
