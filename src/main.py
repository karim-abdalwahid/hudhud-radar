"""
HudhudRadar: Main FastAPI Application.
Exposes Webhooks, Management APIs, Identity Review Queue, Analytics, and Executive Dashboard.
"""
import sys
from pathlib import Path

# Ensure project root is in Python sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import re
import hmac
import httpx
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.core.admin_alerts import collect_alerts
from src.core.auth import (
    create_session_token,
    verify_session_token,
    user_store,
    auth_limiter,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    PUBLIC_EXACT_PATHS,
    PUBLIC_PATH_PREFIXES,
    ADMIN_EXACT_PATHS,
    ADMIN_PAGE_PATHS,
    ADMIN_PATH_PREFIXES,
    ADMIN_MUTATION_PREFIXES,
)
from src.meta_api.webhooks import webhook_handler
from src.automations.service import automations_service
from src.agent.orchestrator import agent_orchestrator
from src.leads.service import lead_service
from src.identity.review_queue import identity_review_queue
from src.analytics.statistics_engine import statistics_engine
from src.reporting.report_generator import report_generator
from src.agent.knowledge_base import knowledge_base
from src.knowledge.meta_crawler import meta_crawler, knowledge_synthesizer
from src.knowledge.document_processor import document_processor
from src.meta_api.feed_sync import meta_feed_sync
from src.meta_api.token_manager import meta_token_manager
from src.meta_api.extended_api import (
    meta_insights_sync,
    threads_publisher,
    marketing_leads_sync,
)
from src.meta_api.threads_oauth import threads_oauth as threads_oauth_manager
from src.modules.compliance import register_compliance_routes  # modular architecture: compliance module (pilot)
from src.ai.provider_manager import ai_provider_manager

from src.content_studio.models import (
    ContentPostCreate,
    ContentPostUpdate,
    ContentPostResponse,
    ContentGenerationRequest,
    ContentGenerationResponse,
    ContentPlatform,
    PostType,
    ContentStatus,
    CreationMode,
)
from src.content_studio.service import ContentStudioService
from src.agent.content_engine import content_engine
from src.agent.scheduler import content_scheduler


content_studio_service = ContentStudioService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown hooks."""
    logger.info("Initializing HudhudRadar system...")
    try:
        knowledge_base.reload()
    except Exception as e:
        logger.warning(f"Could not load local knowledge base markdown files: {e}")

    # In serverless environments (Vercel, Lambda), background infinite loops are disabled
    is_serverless = bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )
    scheduler_task = None
    if not is_serverless:
        # Start background content publishing scheduler loop
        scheduler_task = asyncio.create_task(content_scheduler.start_loop(interval_seconds=30))
        content_scheduler._task = scheduler_task
        logger.info("HudhudRadar AI Engine & Content Scheduler running.")
    else:
        logger.info("Running in Vercel Serverless environment: background cron scheduler managed via Vercel Cron/Webhooks.")

    yield

    if scheduler_task:
        content_scheduler.stop_loop()
    logger.info("Shutting down HudhudRadar...")


app = FastAPI(
    title="HudhudRadar API",
    description="Autonomous AI Social Media Agent for Instagram & Facebook",
    version="1.1.0",
    lifespan=lifespan
)


# --------------------------------------------------------------------
# Authentication Middleware: protects dashboard pages & APIs
# --------------------------------------------------------------------
def _safe_error(e: Exception, meta_detail: str = "") -> str:
    """Client-safe error message: real exception details go to the log;
    clients get a short generic message (no internals, no tokens, no raw
    upstream response bodies). ValueError is intentional user-facing
    validation feedback raised by services — passed through verbatim."""
    logger.error(f"API error [{type(e).__name__}]: {e}{(' | ' + meta_detail) if meta_detail else ''}")
    if isinstance(e, ValueError):
        return str(e)
    return f"{type(e).__name__}: عذراً، فشلت العملية — راجع سجلات الخادم للتفاصيل"


def _is_public(path: str) -> bool:
    # Registry-aware: legacy lists + any module-declared public paths.
    from src.core.auth import is_public_path
    return is_public_path(path)


def _is_admin_route(path: str, method: str) -> bool:
    from src.core.auth import is_admin_page
    if path in ADMIN_EXACT_PATHS or is_admin_page(path):
        return True
    if any(path.startswith(p) for p in ADMIN_PATH_PREFIXES):
        return True
    if method != "GET" and any(path.startswith(p) for p in ADMIN_MUTATION_PREFIXES):
        return True
    return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if _is_public(path):
        return await call_next(request)

    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    request.state.session = session

    if not session:
        if path.startswith("/api/") or path.startswith("/webhooks"):
            return JSONResponse(status_code=401, content={"detail": "غير مصرح — يرجى تسجيل الدخول"})
        return RedirectResponse(url=f"/login?next={path}", status_code=303)

    if _is_admin_route(path, request.method) and session.get("role") != "admin":
        if path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"detail": "هذه العملية تتطلب صلاحيات المدير"})
        return HTMLResponse(
            content="<h1 style='font-family:sans-serif;direction:rtl'>403 — هذه الصفحة للمدير فقط</h1>",
            status_code=403,
        )

    return await call_next(request)


# --------------------------------------------------------------------
# Static assets (auth pages + dashboard pages) — served before module mounts
# --------------------------------------------------------------------
from src.core.http_utils import STATIC_DIR  # noqa: E402
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------
# Feature modules (modular architecture — WS0.3)
# Each module is self-contained: routes + pages + auth declarations.
# Adding a feature = import + register(app). Nothing else.
# --------------------------------------------------------------------
from src.modules.auth_module import register_router as _auth_register_router
from src.modules.pages import register as _pages_register
from src.modules.inbox_onboarding import register as _inbox_register
from src.modules import (  # noqa: E402
    health, webhooks, leads, identity, analytics, meta,
    content, cron_admin, ai, threads_marketing, knowledge, automations,
)
from src.modules import notifications as notifications_module  # noqa: E402
from src.modules import admin_console as admin_console_module  # noqa: E402
from src.modules import admin_users_page  # noqa: E402
from src.modules import templates_manager  # noqa: E402
from src.modules.compliance import register_compliance_routes  # noqa: E402
from src.modules import legal as _legal

_auth_register_router(app)
_pages_register(app)
_inbox_register(app)
health.register(app)
webhooks.register(app)
leads.register(app)
identity.register(app)
analytics.register(app)
meta.register(app)
content.register(app)
cron_admin.register(app)
ai.register(app)
threads_marketing.register(app)
knowledge.register(app)
automations.register(app)
notifications_module.register(app)
admin_console_module.register(app)
admin_users_page.register(app)
templates_manager.register(app)
register_compliance_routes(app)
_legal.register(app)