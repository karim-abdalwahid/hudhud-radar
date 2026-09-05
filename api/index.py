import sys
from pathlib import Path

# Add project root to sys.path so src.* modules resolve properly in Vercel Serverless environment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.main import app
except Exception as e:
    import traceback
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="Hudhud Radar Diagnostic")
    err_msg = traceback.format_exc()

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def fallback_diagnostic(full_path: str):
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;padding:32px;background:#0f172a;color:#f8fafc;'>"
            f"<h2 style='color:#ef4444;'>Hudhud Radar Serverless Startup Error</h2>"
            f"<pre style='background:#1e293b;padding:16px;border-radius:8px;overflow-x:auto;'>{err_msg}</pre>"
            f"</body></html>",
            status_code=500
        )

