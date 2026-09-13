"""
Shared kernel — the single import point every module's routes.py uses.

Contains ONLY things that were module-agnostic globals in main.py:
services, settings, caches, small helpers. This is the "kernel" the
modular architecture is built around; keep it minimal and stable.
"""
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, Query, Request, Response, BackgroundTasks
from pydantic import BaseModel

from src.config import settings
from src.core.logger import logger
from src.core.http_utils import safe_error, TEMPLATES_DIR
from src.core.supabase_client import supabase_db
from src.core.admin_alerts import collect_alerts
from src.core.auth import verify_session_token, SESSION_COOKIE_NAME

# Services (singletons from their own packages — re-exported for modules)
from src.meta_api.webhooks import webhook_handler
from src.automations.service import automations_service
from src.agent.orchestrator import agent_orchestrator
from src.leads.service import lead_service
from src.identity.review_queue import identity_review_queue
from src.analytics.statistics_engine import statistics_engine
from src.reporting.report_generator import report_generator
from src.agent.knowledge_base import knowledge_base
from src.meta_api.feed_sync import meta_feed_sync
from src.meta_api.token_manager import meta_token_manager
from src.meta_api.extended_api import (
    meta_insights_sync,
    threads_publisher,
    marketing_leads_sync,
)
from src.meta_api.threads_oauth import threads_oauth as threads_oauth_manager
from src.ai.provider_manager import ai_provider_manager
from src.agent.content_engine import content_engine
from src.agent.scheduler import content_scheduler
from src.content_studio.service import ContentStudioService
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
from src.knowledge.meta_crawler import meta_crawler, knowledge_synthesizer
from src.knowledge.document_processor import document_processor
from src.core.admin_alerts import collect_alerts as _collect_alerts

content_studio_service = ContentStudioService()

# _safe_error legacy alias (existing tests use safe messages through this name)
_safe_error = safe_error

# Meta status cache (used by the meta module; lives here so tests can patch it)
_meta_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}
META_STATUS_CACHE_TTL = 60.0


def _verify_cron_secret(request: Request):
    """Validates the cron caller secret. FAIL-CLOSED in production: if
    CRON_SECRET is unset there, the request is rejected (never public).
    Accepts Authorization: Bearer <secret> or ?key=/secret= query params.
    Constant-time comparison."""

    secret = settings.CRON_SECRET
    if not secret:
        if settings.APP_ENV.lower() == "production":
            logger.error("CRON_SECRET is not configured in production — cron endpoints fail CLOSED")
            raise HTTPException(status_code=503, detail="Cron endpoints disabled: CRON_SECRET not configured")
        return  # Local dev convenience only
    auth_header = request.headers.get("authorization") or ""
    provided = ""
    if auth_header.startswith("Bearer "):
        provided = auth_header[7:].strip()
    if not provided:
        provided = (request.query_params.get("key") or request.query_params.get("secret") or "").strip()
    import hmac as _hmac
    if not provided or not _hmac.compare_digest(provided.encode("utf-8"), secret.encode("utf-8")):
        logger.warning(f"Cron auth rejected from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Invalid cron secret")


def _llm_status_probe() -> Dict[str, Any]:
    """Tiny live Gemini probe used by /api/debug/llm-status (admin-only)."""
    key = settings.GEMINI_API_KEY
    info: Dict[str, Any] = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "key_set": bool(key),
    }
    if not key:
        info["ok"] = False
        info["error"] = "GEMINI_API_KEY not set in environment"
        return info
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": key},
            json={"contents": [{"parts": [{"text": "OK"}]}],
                  "generationConfig": {"maxOutputTokens": 5, "thinkingConfig": {"thinkingBudget": 0}}},
            timeout=15,
        )
        info["http_status"] = resp.status_code
        if resp.status_code == 200:
            info["ok"] = True
            try:
                cands = resp.json().get("candidates") or []
                parts = (cands[0].get("content") or {}).get("parts") if cands else None
                info["sample_text"] = "".join(p.get("text", "") for p in (parts or []))[:40]
            except Exception as pe:
                info["parse_error"] = str(pe)
        else:
            info["ok"] = False
            info["error"] = resp.text[:400]
    except Exception as e:
        info["ok"] = False
        info["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return info
