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
@router.get("/api/cron/scheduler-tick", tags=["Cron"])
async def cron_scheduler_tick(request: Request):
    """
    Cron-safe GET trigger for the content scheduler (serverless environments
    have no background loop). Publishes all posts whose scheduled_for <= now.
    WS-F: fires a notification when real publishing happened.
    """
    _verify_cron_secret(request)
    results = await content_scheduler.check_and_publish_due_posts()
    if results:
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("📣 نشر محتوى مجدول", f"تم نشر {len(results)} منشور(ات) مجدولة",
                      "success", {"job": "scheduler_tick", "count": len(results)})
    return {"status": "success", "due_posts_processed": len(results), "details": results}


@router.get("/api/cron/insights-sync", tags=["Cron"])
async def cron_insights_sync(request: Request):
    """Cron trigger for daily Meta Insights sync (Facebook + Instagram metrics)."""
    _verify_cron_secret(request)
    result = await meta_insights_sync.sync_recent_metrics(days=7)
    from src.modules.notifications.hooks import notify_sync_result
    notify_sync_result("insights", result)
    return result


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


@router.get("/api/cron/threads-token-refresh", tags=["Cron"])
async def cron_threads_token_refresh(request: Request):
    """Daily (Wave 9.8): refresh Threads tokens — legacy + per-user — that
    expire within 7 days. Failures are logged, never raised."""
    _verify_cron_secret(request)
    result = await threads_oauth_manager.refresh_if_expiring()
    if result.get("refreshed"):
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("🔄 تحديث توكن Threads",
                      f"تم تحديث {len(result['refreshed'])} توكن(ات) قبل انتهائها",
                      "success", {"job": "threads_token_refresh", **result})
    return result
