"""
Meta Platform & Social Connection Management — migrated verbatim from main.py (WS0.3).

Owned by module 'meta'. Registered via src/modules/meta/__init__.py.
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
# 5.1 Meta Platform & Social Connection Management
# --------------------------------------------------------------------
class MetaConfigPayload(BaseModel):
    page_access_token: Optional[str] = None
    page_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    ad_account_id: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None




import time


def _require_session_user(request: Request) -> str:
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    user_id = (session or {}).get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    return str(user_id)


@router.get("/api/meta/status", tags=["Meta Integration"])
async def get_meta_status(request: Request):
    """
    Returns the signed-in customer's own Meta connection status. It does not
    inspect a process-wide page token or another customer's connection.
    """
    from src.modules.connections.service import connection_service
    connections = connection_service.list_connections(_require_session_user(request))
    facebook = next((c for c in connections if c.get("platform") == "facebook"), None)
    instagram = next((c for c in connections if c.get("platform") == "instagram"), None)
    linked_ig = (facebook or {}).get("metadata", {}).get("linked_ig_id")
    is_connected = bool(facebook or instagram)
    return {
        "configured": bool(settings.META_APP_ID and settings.META_APP_SECRET),
        "token_valid": is_connected,
        "connected": is_connected,
        "token_status": "valid" if is_connected else "not_connected",
        "page_name": (facebook or {}).get("account_name"),
        "page_id": (facebook or {}).get("account_id"),
        "pages": [facebook] if facebook else [],
        "instagram_business_account": (instagram or {}).get("account_id") or linked_ig or None,
        "instagram_account_id": (instagram or {}).get("account_id") or linked_ig or None,
        "app_id": settings.META_APP_ID or None,
        "supabase_connected": supabase_db.is_connected,
    }


@router.get("/api/meta/posts", tags=["Meta Integration"])
async def get_live_meta_posts(
    request: Request,
    platform: Optional[str] = Query("all"),
    post_type: Optional[str] = Query("all"),
    limit: Optional[int] = Query(50, ge=1, le=500),
):
    """Fetches real published posts across connected platforms for the authenticated user."""
    from datetime import datetime, timezone
    from src.modules.meta.tenant_feed_service import tenant_feed_service

    user_id = _require_session_user(request)
    posts = await tenant_feed_service.get_tenant_posts(
        user_id=user_id,
        platform=platform or "all",
        limit=limit or 50,
    )
    if post_type and post_type != "all":
        posts = [p for p in posts if p.get("post_type") == post_type]
    return {
        "status": "success",
        "count": len(posts),
        "posts": posts,
        "cache_updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/meta/sync-posts", tags=["Meta Integration"])
async def sync_live_meta_posts(request: Request):
    """Refreshes live posts across connected platforms for the authenticated user."""
    from datetime import datetime, timezone
    from src.modules.meta.tenant_feed_service import tenant_feed_service

    user_id = _require_session_user(request)
    posts = await tenant_feed_service.get_tenant_posts(
        user_id=user_id,
        platform="all",
        limit=50,
    )
    return {
        "status": "success",
        "synced": len(posts),
        "posts": posts,
        "cache_updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/meta/configure", tags=["Meta Integration"])
async def configure_meta_credentials(payload: MetaConfigPayload, request: Request = None):
    """Stores a manually supplied Page token only in this user's encrypted connection.

    App credentials stay deployment configuration; accepting or writing them
    at runtime would make one customer's request alter every tenant.
    """
    user_id = _require_session_user(request)
    if payload.app_id or payload.app_secret:
        raise HTTPException(status_code=400, detail="Meta app credentials must be configured by the deployment, not this endpoint")
    if not payload.page_access_token:
        raise HTTPException(status_code=400, detail="page_access_token is required; or connect using Facebook OAuth")
    page_name = None
    try:
        from src.modules.connections.service import connection_service
        resp = httpx.get(
            f"{settings.META_GRAPH_API_BASE_URL}/me?fields=id,name&access_token={payload.page_access_token}",
            timeout=5.0,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Meta Graph API rejected the page token")
        data = resp.json()
        page_name = data.get("name")
        page_id = str(payload.page_id or data.get("id") or "")
        if not page_id:
            raise HTTPException(status_code=400, detail="Meta did not provide a Page ID")
        saved = connection_service.store(
            user_id=user_id, platform="facebook", access_token=payload.page_access_token,
            account_id=page_id, account_name=page_name, scopes=[],
            metadata={
                **({"linked_ig_id": payload.instagram_account_id} if payload.instagram_account_id else {}),
                **({"ad_account_id": payload.ad_account_id} if payload.ad_account_id else {}),
            },
        )
        if not saved:
            raise HTTPException(status_code=503, detail="Could not persist the encrypted connection")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.warning(f"per-user connection store failed: {e}")
        raise HTTPException(status_code=400, detail="Unable to validate or save the Meta connection")

    return {
        "status": "success",
        "message": f"تم ربط والتحقق من حساب فيسبوك بنجاح! صفحة: {page_name or page_id}",
        "page_name": page_name,
        "page_id": page_id,
    }




@router.post("/api/meta/subscribe-page", tags=["Meta Integration"])
async def subscribe_page_to_app(request: Request):
    """
    Subscribes the Facebook Page and/or Instagram account to the App for real-time Webhook delivery.
    Works for Facebook-only, Instagram-only, or both connections.
    """
    from src.modules.connections.service import connection_service
    user_id = _require_session_user(request)
    facebook = connection_service.get_publish_credentials(user_id, "facebook")
    instagram = connection_service.get_publish_credentials(user_id, "instagram")
    if not facebook and not instagram:
        raise HTTPException(status_code=403, detail="An active entitled Facebook or Instagram connection is required")
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Subscribe Facebook Page (if connected)
        if facebook:
            try:
                fb_resp = await client.post(
                    f"{settings.META_GRAPH_API_BASE_URL}/{facebook['account_id']}/subscribed_apps",
                    data={
                        "subscribed_fields": "feed,messages,conversations",
                        "access_token": facebook["access_token"]
                    }
                )
                results["facebook_page"] = fb_resp.json()
            except Exception as e:
                results["facebook_page"] = {"error": str(e)}

        # 2. Subscribe Instagram account (if connected — independent of Facebook)
        if instagram:
            try:
                ig_resp = await client.post(
                    f"{settings.META_GRAPH_API_BASE_URL}/{instagram['account_id']}/subscribed_apps",
                    data={
                        "subscribed_fields": "comments,messages,messaging_postbacks",
                        "access_token": instagram["access_token"]
                    }
                )
                results["instagram_account"] = ig_resp.json()
            except Exception as e:
                results["instagram_account"] = {"error": str(e)}

    return {"status": "success", "subscriptions": results}
