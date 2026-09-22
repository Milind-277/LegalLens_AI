"""LegalLens AI — Request logging middleware."""

from __future__ import annotations

import time

import structlog
from flask import Flask, g, request

logger = structlog.get_logger(__name__)


def register_request_logging(app: Flask) -> None:
    """Register request lifecycle logging.

    Logs request start, duration, and status — but NEVER logs
    document contents, API keys, or sensitive query content.
    """

    @app.before_request
    def log_request_start() -> None:
        g.request_start_time = time.perf_counter()

    @app.after_request
    def log_request_end(response):
        duration_ms = 0.0
        if hasattr(g, "request_start_time"):
            duration_ms = (time.perf_counter() - g.request_start_time) * 1000

        # Log request (sanitized — no sensitive data)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            content_length=response.content_length,
        )

        return response
