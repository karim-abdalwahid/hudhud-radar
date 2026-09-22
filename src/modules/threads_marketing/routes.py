"""
Threads & Marketing Extended APIs — migrated verbatim from main.py (WS0.3).

Owned by module 'threads_marketing'. Registered via src/modules/threads_marketing/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File
from fastapi.responses import RedirectResponse
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


def _session_user_id(request: Request) -> Optional[str]:
    """Session user id (Phase 9.7 per-user connections) — None for legacy paths."""
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    return (session or {}).get("sub")


def _require_session_user_id(request: Request) -> str:
    user_id = _session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return user_id

# --------------------------------------------------------------------
# Extended Meta APIs: Threads & Marketing (spec v2.1 scopes)
# --------------------------------------------------------------------
class ThreadsPublishPayload(BaseModel):
    text: str
    link: Optional[str] = None


@router.get("/api/threads/status", tags=["Threads"])
async def threads_connection_status(request: Request):
    """Returns Threads OAuth connection status (app configured + token state)."""
    return threads_oauth_manager.get_status(_require_session_user_id(request))


@router.get("/api/threads/oauth/authorize", tags=["Threads"])
async def threads_oauth_authorize(request: Request):
    """Build the signed-in, entitled customer's Threads OAuth URL."""
    user_id = _require_session_user_id(request)
    from src.modules.connections.service import connection_service
    connection_service.assert_entitled(user_id, "threads")
    result = threads_oauth_manager.build_authorize_url(user_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


@router.get("/api/threads/oauth/callback", tags=["Threads"])
async def threads_oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """
    OAuth redirect target. Validates the CSRF state, exchanges the code for a
    60-day token, persists it (per-user when a session rides along — the
    normal path; legacy global for the admin flow), then redirects to
    /account with a result flag.
    """
    user_id = _session_user_id(request)
    if not user_id:
        return RedirectResponse(url="/login?threads=expired_session", status_code=303)
    if not code or not threads_oauth_manager.validate_state(state, user_id):
        return RedirectResponse(url="/account?threads=error", status_code=303)
    result = await threads_oauth_manager.exchange_code(code, user_id=user_id)
    if result.get("status") != "success":
        return RedirectResponse(url="/account?threads=error", status_code=303)
    return RedirectResponse(url="/account?threads=connected", status_code=303)


@router.post("/api/threads/oauth/refresh", tags=["Threads"])
async def threads_oauth_refresh(request: Request):
    """Refreshes the 60-day Threads token (safe to call periodically)."""
    result = await threads_oauth_manager.refresh_token(user_id=_session_user_id(request))
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


@router.post("/api/threads/disconnect", tags=["Threads"])
async def threads_disconnect(request: Request):
    """Removes stored Threads credentials."""
    from src.modules.connections.service import connection_service
    if not connection_service.revoke(_require_session_user_id(request), "threads"):
        raise HTTPException(status_code=500, detail="disconnect failed")
    return {"status": "success", "platform": "threads", "connected": False}


@router.post("/api/threads/publish", tags=["Threads"])
async def publish_threads_post(payload: ThreadsPublishPayload, request: Request = None):
    """Publishes a text thread via the official Threads API (own OAuth app)."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="نص الثريد فارغ")
    result = await threads_publisher.publish_thread(
        payload.text, payload.link, user_id=_session_user_id(request) if request else None)
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("detail", "Threads publish failed"))
    return result


@router.get("/api/threads/{thread_id}/replies", tags=["Threads"])
async def get_threads_replies(thread_id: str, limit: int = Query(20, ge=1, le=100),
                              request: Request = None):
    """Reads replies of a published thread."""
    return await threads_publisher.get_thread_replies(
        thread_id, limit, user_id=_session_user_id(request) if request else None)


@router.delete("/api/threads/{thread_id}", tags=["Threads"])
async def delete_threads_post(thread_id: str, request: Request = None):
    """Deletes a published Threads post (threads_delete scope)."""
    result = await threads_publisher.delete_thread(
        thread_id, user_id=_session_user_id(request) if request else None)
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("detail", "Threads delete failed"))
    return result


@router.get("/api/threads/insights", tags=["Threads"])
async def get_threads_insights(request: Request = None,
                               metric: str = Query("views,likes,replies")):
    """Account-level Threads insights (threads_manage_insights scope)."""
    return await threads_publisher.get_account_insights(
        metric, user_id=_session_user_id(request) if request else None)


@router.post("/api/threads/{thread_id}/reply", tags=["Threads"])
async def reply_to_threads_post(thread_id: str, payload: ThreadsPublishPayload,
                                request: Request = None):
    """Replies to a Threads post/reply on behalf of the connected account
    (threads_manage_replies write path) for the session user's connected account."""
    session_user = _session_user_id(request) if request else None
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="نص الرد فارغ")

    token = threads_publisher._resolve_token(session_user)
    if not token:
        raise HTTPException(status_code=400, detail="Threads غير مربوط")

    # Official Threads reply flow: container with reply_to_id -> threads_publish
    # (POST /{id}/replies is not a valid publish endpoint — THApiException 100/33)
    from src.meta_api.extended_api import threads_publisher
    result = await threads_publisher.publish_thread(
        payload.text, reply_to_id=thread_id, user_id=session_user)
    if result.get("status") != "success":
        raise HTTPException(status_code=502, detail=f"Threads reply failed: {result.get('detail', '')[:250]}")
    return {"status": "success", "reply": result}

@router.get("/api/threads/my-posts", tags=["Threads"])
async def my_threads_posts(request: Request = None, limit: int = Query(10, ge=1, le=50)):
    """Lists the account's recent published threads (studio Threads manager)."""
    from src.meta_api.extended_api import threads_leads_sync
    return await threads_leads_sync.get_my_posts(
        limit=limit, user_id=_session_user_id(request) if request else None)


@router.post("/api/threads/sync-replies", tags=["Threads"])
async def sync_threads_replies(request: Request = None,
                               limit_threads: int = Query(10, ge=1, le=50),
                               limit_replies: int = Query(20, ge=1, le=100)):
    """
    Threads Replies → CRM bridge (pull-based): fetches recent replies to the
    account's published threads and captures each author as a lead with
    official profile data (threads_basic). Idempotent per reply id.
    """
    from src.meta_api.extended_api import threads_leads_sync
    return await threads_leads_sync.sync_account_replies(
        limit_threads=limit_threads, limit_replies=limit_replies,
        user_id=_session_user_id(request) if request else None)


@router.post("/api/marketing/sync-leads", tags=["Marketing API"])
async def sync_marketing_leads(request: Request, form_id: Optional[str] = None):
    """Imports Meta Lead Ads leads into the CRM with full provenance."""
    return await marketing_leads_sync.sync_lead_forms(_session_user_id(request), form_id)


@router.post("/api/marketing/sync-campaigns", tags=["Marketing API"])
async def sync_marketing_campaigns(request: Request):
    """Pulls ad campaign performance metrics into the campaigns table."""
    return await marketing_leads_sync.sync_campaign_insights(_session_user_id(request))
