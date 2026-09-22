"""LegalLens AI — Error handling middleware."""

from __future__ import annotations

import structlog
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app.models.responses import APIResponse
from app.utils.validators import ValidationError
from app.ai.client import AIClientError

logger = structlog.get_logger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers that return safe, structured responses."""

    @app.errorhandler(400)
    def bad_request(error: Exception) -> tuple:
        return _error_response("BAD_REQUEST", "Invalid request.", 400)

    @app.errorhandler(401)
    def unauthorized(error: Exception) -> tuple:
        return _error_response("UNAUTHORIZED", "Authentication required.", 401)

    @app.errorhandler(403)
    def forbidden(error: Exception) -> tuple:
        return _error_response("FORBIDDEN", "Access denied.", 403)

    @app.errorhandler(404)
    def not_found(error: Exception) -> tuple:
        return _error_response("NOT_FOUND", "Resource not found.", 404)

    @app.errorhandler(405)
    def method_not_allowed(error: Exception) -> tuple:
        return _error_response("METHOD_NOT_ALLOWED", "Method not allowed.", 405)

    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error: Exception) -> tuple:
        return _error_response(
            "FILE_TOO_LARGE",
            "File exceeds maximum allowed size.",
            413,
        )

    @app.errorhandler(415)
    def unsupported_media(error: Exception) -> tuple:
        return _error_response(
            "UNSUPPORTED_FORMAT",
            "Unsupported file format.",
            415,
        )

    @app.errorhandler(422)
    def unprocessable(error: Exception) -> tuple:
        return _error_response("VALIDATION_ERROR", "Request validation failed.", 422)

    @app.errorhandler(429)
    def rate_limited(error: Exception) -> tuple:
        return _error_response(
            "RATE_LIMITED",
            "Too many requests. Please try again later.",
            429,
        )

    @app.errorhandler(500)
    def internal_error(error: Exception) -> tuple:
        logger.error("internal_server_error", error=str(error))
        return _error_response(
            "INTERNAL_ERROR",
            "An internal error occurred. Please try again.",
            500,
        )

    @app.errorhandler(502)
    def bad_gateway(error: Exception) -> tuple:
        return _error_response("BAD_GATEWAY", "Service temporarily unavailable.", 502)

    @app.errorhandler(503)
    def service_unavailable(error: Exception) -> tuple:
        return _error_response(
            "SERVICE_UNAVAILABLE",
            "Service temporarily unavailable. Please try again later.",
            503,
        )

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> tuple:
        # Map specific validation error codes to HTTP statuses
        status_map = {
            "UNAUTHORIZED": 401,
            "FORBIDDEN": 403,
            "NOT_FOUND": 404,
            "DOCUMENT_NOT_FOUND": 404,
            "FILE_TOO_LARGE": 413,
            "UNSUPPORTED_FORMAT": 415,
            "RATE_LIMITED": 429,
        }
        status_code = status_map.get(error.code, 422)
        return _error_response(error.code, error.message, status_code)

    @app.errorhandler(AIClientError)
    def handle_ai_client_error(error: AIClientError) -> tuple:
        msg = str(error).lower()
        if "quota" in msg or "429" in msg or "rate limit" in msg or "exhausted" in msg:
            return _error_response(
                "RATE_LIMITED",
                "Google AI Free Tier rate limit exceeded. Please wait 60 seconds and try again.",
                429,
            )
        return _error_response(
            "SERVICE_UNAVAILABLE",
            "The AI service is temporarily unavailable. Please try again.",
            503,
        )

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception) -> tuple:
        """Catch-all handler — never expose internal details."""
        if isinstance(error, HTTPException):
            return _error_response(
                "HTTP_ERROR",
                error.description or "An error occurred.",
                error.code or 500,
            )

        logger.error("unhandled_exception", error=str(error), type=type(error).__name__)
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again.",
            500,
        )


def _error_response(code: str, message: str, status: int) -> tuple:
    """Build a consistent error response tuple."""
    response = APIResponse.fail(code=code, message=message)
    return jsonify(response.model_dump()), status
