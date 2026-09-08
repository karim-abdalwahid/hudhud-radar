import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# TEMP DIAGNOSTIC (bisect step 2): full app import with traceback surfacing.
from fastapi import FastAPI

try:
    from src.main import app  # noqa: F401 — required by Vercel
except Exception as _boot_error:  # pragma: no cover
    import traceback

    _tb = traceback.format_exc()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def _boot_failure():
        safe = _tb.replace("<", "&lt;").replace(">", "&gt;")
        return HTMLResponseSafe(safe)

    from fastapi.responses import HTMLResponse as _HR

    def HTMLResponseSafe(safe):
        return _HR(content=f"<h2>boot failure</h2><pre>{safe}</pre>", status_code=500)
