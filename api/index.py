import os
import sys
import traceback
from pathlib import Path

# Ensure project root is in Python sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Catch any initialization error to provide diagnostic feedback
startup_error = None
try:
    from src.main import app as _real_app
    app = _real_app
except Exception:
    startup_error = traceback.format_exc()

    async def app(scope, receive, send):
        if scope["type"] == "http":
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HudhudRadar Startup Diagnostic</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 40px; margin: 0; }}
        .card {{ max-width: 900px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #ef4444; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #ef4444; margin-top: 0; font-size: 24px; }}
        p {{ color: #94a3b8; font-size: 15px; }}
        pre {{ background: #0f172a; color: #fca5a5; padding: 20px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; border: 1px solid #334155; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Server Startup Error on Vercel</h1>
        <p>The Python application encountered an exception during initialization:</p>
        <pre>{startup_error}</pre>
    </div>
</body>
</html>"""
            body = html.encode("utf-8")
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [
                    (b"content-type", b"text/html; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
