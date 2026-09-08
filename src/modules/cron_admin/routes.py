"""
Cron Endpoints + Admin Alerts + Debug Diagnostics — migrated verbatim from main.py (WS0.3).

Owned by module 'cron_admin'. Registered via src/modules/cron_admin/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File
import hmac
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from src.modules.context import *  # noqa: F401,F403 — shared kernel (services, settings, caches)
from src.modules.context import (  # explicit for readability
    settings, logger, supabase_db, httpx, safe_error, _safe_error,
    content_studio_service, knowledge_base, webhook_handler,
    automations_service, agent_orchestrator, lead_service,
    identity_review_queue, statistics_engine, report_generator,
    meta_feed_sync, meta_token_manager, meta_insights_sync,
    threads_publisher, marketing_leads_sync, threads_oauth_manager,
    ai_provider_manager, content_scheduler, _verify_cron_secret,
    _meta_status_cache, META_STATUS_CACHE_TTL, _llm_status_probe,
    collect_alerts, TEMPLATES_DIR,
)

router = APIRouter()

# --------------------------------------------------------------------
# Cron Endpoints (Vercel Cron / external cron-job.org)
# Protected by CRON_SECRET (Vercel sends 'Authorization: Bearer $CRON_SECRET').
# --------------------------------------------------------------------
def _verify_cron_secret(request: Request):
    """Validates the cron caller secret. FAIL-CLOSED in production: if
    CRON_SECRET is unset there, the request is rejected (never public).
    Accepts either:
    - Authorization: Bearer <secret> header (Vercel Cron), or
    - ?key=<secret> / ?secret=<secret> query param (cron-job.org free plan
      does not support custom headers).
    Comparison is constant-time (hmac.compare_digest).
    """
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
    if not provided or not hmac.compare_digest(provided.encode("utf-8"), secret.encode("utf-8")):
        logger.warning(f"Cron auth rejected from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@router.get("/api/cron/scheduler-tick", tags=["Cron"])
async def cron_scheduler_tick(request: Request):
    """
    Cron-safe GET trigger for the content scheduler (serverless environments
    have no background loop). Publishes all posts whose scheduled_for <= now.
    """
    _verify_cron_secret(request)
    results = await content_scheduler.check_and_publish_due_posts()
    return {"status": "success", "due_posts_processed": len(results), "details": results}


@router.get("/api/cron/insights-sync", tags=["Cron"])
async def cron_insights_sync(request: Request):
    """Cron trigger for daily Meta Insights sync (Facebook + Instagram metrics)."""
    _verify_cron_secret(request)
    return await meta_insights_sync.sync_recent_metrics(days=7)


@router.get("/api/admin/alerts", tags=["System"])
async def admin_system_alerts(request: Request, force: bool = False):
    """
    Admin-only system health alerts: Meta token validity, Threads expiry,
    Gemini quota, webhook subscription, scheduler freshness, Supabase.
    Returns items sorted by severity (critical → ok).
    """
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request.cookies.get(SESSION_COOKIE_NAME) else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    return {"status": "success", "alerts": collect_alerts(force=force)}
