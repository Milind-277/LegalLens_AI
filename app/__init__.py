"""LegalLens AI — Application factory."""

from __future__ import annotations

import os

import structlog
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from app.config import get_config
from app.middleware.error_handler import register_error_handlers
from app.middleware.request_logging import register_request_logging
from app.middleware.security import register_security_headers
from app.models.responses import APIResponse

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder="static", template_folder="templates")

    # Load configuration
    config = get_config()
    app.config.from_object(config)

    # Enable CORS (allow all origins for this challenge, but restrict in prod)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Create upload directory if it doesn't exist
    upload_folder = os.path.join(app.root_path, "..", app.config["UPLOAD_FOLDER"])
    os.makedirs(upload_folder, exist_ok=True)

    # Register middleware
    register_request_logging(app)
    register_security_headers(app)
    register_error_handlers(app)

    # Register blueprints
    from app.routes.analysis import bp as analysis_bp
    from app.routes.comparison import bp as comparison_bp
    from app.routes.documents import bp as documents_bp
    from app.routes.qa import bp as qa_bp

    app.register_blueprint(documents_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(comparison_bp)

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check() -> tuple:
        return jsonify(APIResponse.ok(message="LegalLens AI is running").model_dump()), 200

    # AI availability status endpoint
    @app.route("/api/status", methods=["GET"])
    def ai_status() -> tuple:
        """Check AI provider availability without making an actual AI call."""
        api_key = app.config.get("GOOGLE_API_KEY", "")
        ai_configured = bool(
            api_key and api_key not in ("", "your_api_key_here", "test-key-not-real")
        )
        return (
            jsonify(
                APIResponse.ok(
                    data={
                        "ai_configured": ai_configured,
                        "model": app.config.get("AI_MODEL_NAME", "gemini-1.5-flash"),
                        "fallback_available": True,
                        "status": "ai_ready" if ai_configured else "fallback_mode",
                    }
                ).model_dump()
            ),
            200,
        )

    # Serve SPA frontend
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str):
        if path != "" and os.path.exists(os.path.join(app.static_folder or "", path)):
            return send_from_directory(app.static_folder or "", path)
        return send_from_directory(app.template_folder or "", "index.html")

    return app
