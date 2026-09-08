"""Shared HTTP helpers used across modules (single source of truth)."""
from src.core.logger import logger


def safe_error(e: Exception, meta_detail: str = "") -> str:
    """Client-safe error message: real exception details go to the log;
    clients get a short generic message (no internals, no tokens, no raw
    upstream response bodies). ValueError is intentional user-facing
    validation feedback raised by services — passed through verbatim."""
    logger.error(f"API error [{type(e).__name__}]: {e}{(' | ' + meta_detail) if meta_detail else ''}")
    if isinstance(e, ValueError):
        return str(e)
    return f"{type(e).__name__}: عذراً، فشلت العملية — راجع سجلات الخادم للتفاصيل"


from pathlib import Path  # noqa: E402

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
STATIC_DIR = TEMPLATES_DIR / "static"
