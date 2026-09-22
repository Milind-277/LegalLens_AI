"""LegalLens AI — API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error detail."""

    code: str = Field(description="Error code")
    message: str = Field(description="User-facing error message")


class APIResponse(BaseModel):
    """Standard API response envelope."""

    success: bool = Field(description="Whether the request succeeded")
    data: Any = Field(default=None, description="Response payload")
    error: ErrorDetail | None = Field(default=None, description="Error details if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")

    @classmethod
    def ok(cls, data: Any = None, **metadata: Any) -> APIResponse:
        """Create a successful response."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, code: str, message: str, **metadata: Any) -> APIResponse:
        """Create a failure response."""
        return cls(
            success=False,
            error=ErrorDetail(code=code, message=message),
            metadata=metadata,
        )
