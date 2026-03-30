# backend/app/utils.py
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import HTTPException


def utcnow() -> datetime:
    """Return current UTC time. Single source of truth for all models."""
    return datetime.now(timezone.utc)


def sanitize_csv_cell(value: str) -> str:
    """Sanitize a string for safe CSV export.

    Prevents CSV injection by prefixing cells that start with
    formula-triggering characters (=, +, -, @) with a single quote.
    """
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def validate_source_url(url: str) -> str:
    """Validate that a source URL uses http or https scheme.

    Rejects javascript:, data:, file:, and other non-http schemes to prevent
    XSS and local file access attacks.
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="source_url cannot be empty.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )
    return url
