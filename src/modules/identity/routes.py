"""
Identity Resolution Review Queue — migrated verbatim from main.py (WS0.3).

Owned by module 'identity'. Registered via src/modules/identity/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File
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
# 4. Identity Resolution Manual Review Queue
# --------------------------------------------------------------------
@router.get("/api/identity/queue", tags=["Identity Resolution"])
async def get_verification_queue():
    """Lists pending ambiguous matches awaiting human supervisor decision.
    Also returns the REAL configured thresholds so the UI never displays
    hardcoded policy numbers that drift from actual settings."""
    reviews = identity_review_queue.get_pending_reviews()
    return {
        "status": "success",
        "pending_reviews": reviews,
        "queue": reviews,
        "count": len(reviews),
        "policy": {
            "manual_confirmation_required": settings.REQUIRE_MANUAL_IDENTITY_CONFIRMATION,
            "auto_link_threshold_percent": round(settings.CONFIDENCE_THRESHOLD_AUTO_LINK * 100),
            "queue_review_threshold_percent": round(settings.CONFIDENCE_THRESHOLD_QUEUE_REVIEW * 100),
        },
    }


@router.post("/api/identity/queue/{queue_id}/approve", tags=["Identity Resolution"])
async def approve_identity_link(queue_id: str, reviewer: str = "Admin", notes: Optional[str] = None):
    """Explicitly confirms linking two accounts as belonging to the same human identity."""
    try:
        updated = identity_review_queue.approve_match(queue_id, reviewer, notes)
        return {"status": "approved", "queue_item": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))


@router.post("/api/identity/queue/{queue_id}/reject", tags=["Identity Resolution"])
async def reject_identity_link(queue_id: str, reviewer: str = "Admin", notes: Optional[str] = None):
    """Explicitly rejects candidate match, keeping both records distinct."""
    try:
        updated = identity_review_queue.reject_match(queue_id, reviewer, notes)
        return {"status": "rejected", "queue_item": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))
