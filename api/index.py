import sys
from pathlib import Path

# Add project root to Python sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# TEMP DIAGNOSTIC (WS0 rollback safety): surface cold-start import errors
# directly instead of an opaque 500. Removed once deployment is verified.
try:
    from src.main import app  # noqa: F401 — required by Vercel
except Exception as _boot_error:  # pragma: no cover
    import traceback

    _tb = traceback.format_exc()

    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _boot_failure(full_path: str):
        safe = _tb.replace("<", "&lt;").replace(">", "&gt;")
        return HTMLResponse(
            content=f"<h2>Hudhud boot failure (temp diagnostic)</h2><pre>{safe}</pre>",
            status_code=500,
        )
