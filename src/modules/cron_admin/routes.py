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
    try:
        results = await content_scheduler.check_and_publish_due_posts()
        status = "success"
        err = None
    except Exception as e:
        # cron-job.org disables jobs after repeated non-2xx answers. The tick
        # always returns 200 with an honest status; failures land in logs +
        # admin alerts instead of HTTP failures.
        logger.error(f"scheduler tick failed (reported 200): {e}")
        results, status, err = [], "partial", str(e)[:200]
    published = [r for r in results if r.get("status") == "published"]
    if published:
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("📣 نشر محتوى مجدول", f"تم نشر {len(published)} منشور(ات) مجدولة",
                      "success", {"job": "scheduler_tick", "count": len(published)})
    body = {"status": status, "due_posts_processed": len(results), "details": results}
    if err:
        body["error"] = err
    return body


@router.get("/api/cron/insights-sync", tags=["Cron"])
async def cron_insights_sync(request: Request):
    """Cron trigger for each customer's daily Meta Insights sync."""
    _verify_cron_secret(request)
    try:
        rows = supabase_db.select("platform_connections", {"status": "active"}) or []
        owner_ids = sorted({str(row.get("user_id")) for row in rows if row.get("user_id")})
        outcomes = []
        for owner_id in owner_ids:
            outcomes.append({"user_id": owner_id,
                             "result": await meta_insights_sync.sync_recent_metrics(owner_id, days=7)})
        result = {"status": "success", "tenants_checked": len(owner_ids), "outcomes": outcomes}
    except Exception as e:
        logger.error(f"insights sync cron failed (reported 200): {e}")
        return {"status": "partial", "error": str(e)[:200]}
    from src.modules.notifications.hooks import notify_sync_result
    try:
        notify_sync_result("insights", result)
    except Exception as e:
        logger.warning(f"insights notify failed: {e}")
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
    try:
        result = await threads_oauth_manager.refresh_if_expiring()
    except Exception as e:
        logger.error(f"threads token-refresh cron failed (reported 200): {e}")
        return {"status": "partial", "error": str(e)[:200]}
    if result.get("refreshed"):
        from src.modules.notifications.hooks import _notify_admin
        _notify_admin("🔄 تحديث توكن Threads",
                      f"تم تحديث {len(result['refreshed'])} توكن(ات) قبل انتهائها",
                      "success", {"job": "threads_token_refresh", **result})
    # Run daily billing reconciliation alongside token maintenance
    try:
        from src.modules.billing.services import entitlement_service
        result["billing_reconciliation"] = entitlement_service.reconcile_active_subscriptions()
    except Exception as e:
        logger.warning(f"daily billing reconciliation inline error: {e}")
    return result


@router.get("/api/cron/billing-reconciliation", tags=["Cron"])
async def cron_billing_reconciliation(request: Request):
    """Daily safety net: reconciles active subscriptions against payment gateway
    to ensure renewals grant monthly credits even if webhooks failed."""
    _verify_cron_secret(request)
    try:
        from src.modules.billing.services import entitlement_service
        return entitlement_service.reconcile_active_subscriptions()
    except Exception as e:
        logger.error(f"billing reconciliation cron failed: {e}")
        return {"status": "error", "error": str(e)[:200]}
