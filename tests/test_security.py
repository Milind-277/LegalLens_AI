"""LegalLens AI — Tests for security configurations."""


def test_security_headers(client):
    """Test that all required security headers are present."""
    resp = client.get("/api/health")

    headers = resp.headers
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "strict-origin-when-cross-origin" in headers.get("Referrer-Policy")
    assert "default-src 'self'" in headers.get("Content-Security-Policy")
    assert headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

    # API endpoints should not be cached
    assert "no-store" in headers.get("Cache-Control")


def test_cors_headers(client):
    """Test CORS configuration."""
    resp = client.options("/api/health", headers={"Origin": "http://localhost:3000"})

    assert resp.headers.get("Access-Control-Allow-Origin") in ("*", "http://localhost:3000")


def test_error_responses_hide_internals(client):
    """Test that error responses don't leak stack traces."""
    # Force a 500 error by sending invalid JSON to an endpoint that expects it
    resp = client.post(
        "/api/documents/compare", data="This is not valid JSON", content_type="application/json"
    )

    assert resp.status_code == 400
    data = resp.json
    assert data["success"] is False
    # Error message should be generic, no stack trace
    assert "Traceback" not in data["error"]["message"]
    assert "KeyError" not in data["error"]["message"]
