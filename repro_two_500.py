"""Reproduce the two 500s in-process to capture tracebacks."""
import logging
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

# surface the app's own error traceback
from src.core.logger import logger
logging.getLogger("HudhudRadar").setLevel(logging.DEBUG)

from starlette.testclient import TestClient
import asyncio
from src.main import app
from src.modules.knowledge.routes import create_knowledge_document, SaveDocumentRequest
from src.modules.meta.routes import configure_meta_credentials, MetaConfigPayload


async def main():
    try:
        await create_knowledge_document(SaveDocumentRequest(filename="", content=""), request=None)
        print("knowledge: no error")
    except Exception as e:
        print("knowledge raises:", type(e).__name__, str(e)[:160])
    try:
        await configure_meta_credentials(MetaConfigPayload(), request=None)
        print("configure: no error")
    except Exception as e:
        print("configure raises:", type(e).__name__, str(e)[:200])

asyncio.run(main())
