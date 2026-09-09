import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Bisect-2 (live): full app import; /health surfaces any boot traceback.
from fastapi import FastAPI

try:
    from src.main import app  # noqa: F401 — required by Vercel
except Exception as _boot_error:  # pragma: no cover
    import traceback

    _tb = traceback.format_exc()

    _fallback = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @_fallback.get("/health")
    async def _boot_failure():
        from fastapi.responses import HTMLResponse
        safe = _tb.replace("<", "&lt;").replace(">", "&gt;")
        return HTMLResponse(content=f"<h2>boot failure</h2><pre>{safe}</pre>", status_code=500)

    app = _fallback
