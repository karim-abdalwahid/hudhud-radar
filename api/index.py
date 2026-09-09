import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Boot the FULL HudhudRadar app. If the import fails on the server, we still
# define a top-level `app` (Vercel's Python entrypoint scan REQUIRES a direct
# module-level `app = ...` assignment) and surface the traceback at /health.
_boot_error = None
try:
    from src.main import app as _hudhud_app  # noqa: F401 — the real application
except Exception as _e:  # pragma: no cover — server-side diagnostics
    import traceback

    _boot_error = traceback.format_exc()
    _hudhud_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @_hudhud_app.get("/health")
    async def _boot_failure():
        safe = (_boot_error or "").replace("<", "&lt;").replace(">", "&gt;")
        return HTMLResponse(
            content=f"<h2>Hudhud boot failure</h2><pre>{safe}</pre>",
            status_code=500,
        )


# Direct top-level assignment — REQUIRED by Vercel's Python entrypoint scan.
app = _hudhud_app
