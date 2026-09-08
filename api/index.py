import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# MINIMAL BOOT PROBE (bisect step 1): fastapi-only, no src imports.
# If this serves 200 on Vercel, the crash is inside the src.main import chain.
from fastapi import FastAPI

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def _probe():
    return {"probe": "minimal-ok"}
