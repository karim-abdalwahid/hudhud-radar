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
    app_id: Optional[str] = None
    app_secret: Optional[str] = None


class MetaExchangeTokenPayload(BaseModel):
    user_token: str
    target_page_id: Optional[str] = None


class MetaUserPagesPayload(BaseModel):
    user_token: str


import time

_meta_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}
META_STATUS_CACHE_TTL = 60.0


@router.get("/api/meta/status", tags=["Meta Integration"])
async def get_meta_status():
    """
    Checks the live connection status of Meta Facebook Page and Instagram Account.
    Results are cached server-side for 60s to avoid burning Meta Graph API rate
    limits when multiple browser tabs poll this endpoint.
    """
    now = time.time()
    if _meta_status_cache["data"] is not None and (now - _meta_status_cache["ts"]) < META_STATUS_CACHE_TTL:
        return _meta_status_cache["data"]

    # Check Supabase app_settings first for dynamic cloud persistence
    cached_creds = supabase_db.get_setting("meta_credentials")
    active_token = (cached_creds and cached_creds.get("page_access_token")) or settings.META_PAGE_ACCESS_TOKEN
    active_page_id = (cached_creds and cached_creds.get("page_id")) or settings.META_PAGE_ID
    active_ig_id = (cached_creds and cached_creds.get("instagram_account_id")) or settings.META_INSTAGRAM_ACCOUNT_ID

    has_token = bool(active_token)
    token_valid = False
    page_name = (cached_creds and cached_creds.get("page_name")) or None
    page_id = active_page_id or None

    if has_token:
        try:
            resp = httpx.get(
                f"{settings.META_GRAPH_API_BASE_URL}/me?fields=id,name&access_token={active_token}",
                timeout=5.0
            )
            if resp.status_code == 200:
                token_valid = True
                data = resp.json()
                page_name = data.get("name")
                page_id = data.get("id")
        except Exception:
            token_valid = False

    result = {
        "configured": has_token,
        "token_valid": token_valid,
        "page_name": page_name,
        "page_id": page_id,
        "instagram_account_id": active_ig_id or None,
        "app_id": settings.META_APP_ID or None,
        "supabase_connected": supabase_db.is_connected,
    }
    _meta_status_cache["ts"] = now
    _meta_status_cache["data"] = result
    return result


@router.get("/api/meta/posts", tags=["Meta Integration"])
async def get_live_meta_posts(
    platform: Optional[str] = Query("all"),
    post_type: Optional[str] = Query("all"),
    limit: Optional[int] = Query(None, ge=1, le=5000)
):
    """Returns currently cached real published posts and reels from Facebook & Instagram."""
    posts = meta_feed_sync.get_synced_posts(platform=platform, post_type=post_type, limit=limit)
    meta = meta_feed_sync.get_cache_metadata()
    return {
        "status": "success",
        "count": len(posts),
        "posts": posts,
        "cache_updated_at": meta["cache_updated_at"],
        "facebook_count": meta["facebook_count"],
        "instagram_count": meta["instagram_count"],
        "reels_count": meta.get("reels_count", 0),
        "posts_count": meta.get("posts_count", 0),
        "total_cached": meta["total"]
    }


@router.post("/api/meta/sync-posts", tags=["Meta Integration"])
async def sync_live_meta_posts():
    """Triggers live synchronization with Meta Graph API for Facebook posts and Instagram reels."""
    result = await meta_feed_sync.sync_all_live_content(limit_per_platform=100)
    return result


@router.post("/api/meta/configure", tags=["Meta Integration"])
async def configure_meta_credentials(payload: MetaConfigPayload, request: Request = None):
    """Updates and validates Meta Facebook & Instagram credentials in runtime and .env."""
    page_name = None
    if payload.page_access_token:
        try:
            resp = httpx.get(
                f"{settings.META_GRAPH_API_BASE_URL}/me?fields=id,name&access_token={payload.page_access_token}",
                timeout=5.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=_safe_error(Exception("Meta Graph API rejected the request"), meta_detail=resp.text[:200]))
            data = resp.json()
            page_name = data.get("name")
            if not payload.page_id:
                payload.page_id = data.get("id")
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=_safe_error(e))

    # Update runtime settings
    if payload.page_access_token:
        settings.META_PAGE_ACCESS_TOKEN = payload.page_access_token
        agent_orchestrator.client.access_token = payload.page_access_token
    if payload.page_id:
        settings.META_PAGE_ID = payload.page_id
    if payload.instagram_account_id:
        settings.META_INSTAGRAM_ACCOUNT_ID = payload.instagram_account_id
    if payload.app_id:
        settings.META_APP_ID = payload.app_id
    if payload.app_secret:
        settings.META_APP_SECRET = payload.app_secret

    # Persist in .env
    env_path = Path(PROJECT_ROOT) / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        if payload.page_access_token:
            content = re.sub(r"META_PAGE_ACCESS_TOKEN=.*", f"META_PAGE_ACCESS_TOKEN={payload.page_access_token}", content)
        if payload.page_id:
            content = re.sub(r"META_PAGE_ID=.*", f"META_PAGE_ID={payload.page_id}", content)
        if payload.instagram_account_id:
            content = re.sub(r"META_INSTAGRAM_ACCOUNT_ID=.*", f"META_INSTAGRAM_ACCOUNT_ID={payload.instagram_account_id}", content)
        if payload.app_id:
            content = re.sub(r"META_APP_ID=.*", f"META_APP_ID={payload.app_id}", content)
        if payload.app_secret:
            content = re.sub(r"META_APP_SECRET=.*", f"META_APP_SECRET={payload.app_secret}", content)
        env_path.write_text(content, encoding="utf-8")

    # Persist in Supabase app_settings for cloud/serverless persistence
    supabase_db.set_setting("meta_credentials", {
        "page_access_token": settings.META_PAGE_ACCESS_TOKEN,
        "page_id": settings.META_PAGE_ID,
        "page_name": page_name or "",
        "instagram_account_id": settings.META_INSTAGRAM_ACCOUNT_ID or "",
        "app_id": settings.META_APP_ID or ""
    })

    # Invalidate status cache so the next poll reflects new credentials immediately
    _meta_status_cache["ts"] = 0.0
    _meta_status_cache["data"] = None

    # Phase 9.7: ALSO store as the calling user's per-user connection
    # (encrypted at rest in platform_connections). Session user when present.
    try:
        from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
        from src.modules.connections.service import connection_service
        session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") \
            if request else None
        if session:
            ig_meta = None
            if payload.instagram_account_id:
                ig_meta = {"linked_ig_id": payload.instagram_account_id}
            connection_service.store(
                user_id=session["sub"], platform="facebook",
                access_token=payload.page_access_token,
                account_id=payload.page_id, account_name=page_name,
                scopes=[], metadata=ig_meta or {})
    except Exception as e:
        logger.warning(f"per-user connection store skipped: {e}")

    return {
        "status": "success",
        "message": f"تم ربط والتحقق من حساب فيسبوك بنجاح! صفحة: {page_name or payload.page_id}",
        "page_name": page_name,
        "page_id": payload.page_id
    }


@router.post("/api/meta/exchange-token", tags=["Meta Integration"])
async def exchange_permanent_meta_token(payload: MetaExchangeTokenPayload):
    """
    Exchanges a user access token into a permanent Never-Expiring Page Access Token
    using the dual-stage exchange architecture proven in Hudhud.
    """
    try:
        result = await meta_token_manager.generate_and_save_permanent_token(
            any_user_token=payload.user_token,
            target_page_id=payload.target_page_id
        )
        # Invalidate status cache so the next poll reflects the new token immediately
        _meta_status_cache["ts"] = 0.0
        _meta_status_cache["data"] = None
        return result
    except Exception as e:
        logger.error(f"Failed to generate permanent token: {e}")
        raise HTTPException(status_code=400, detail=_safe_error(e))


@router.post("/api/meta/user-pages", tags=["Meta Integration"])
async def get_user_meta_pages(payload: MetaUserPagesPayload):
    """
    Lists all Facebook pages and linked Instagram accounts for a given user token,
    allowing the user to visually pick their target page and Instagram account.
    """
    try:
        long_lived = await meta_token_manager.get_long_lived_user_token(payload.user_token)
        pages = await meta_token_manager.get_permanent_page_tokens(long_lived["access_token"])
        return {
            "status": "success",
            "count": len(pages),
            "pages": [
                {
                    "page_id": p["page_id"],
                    "page_name": p["page_name"],
                    "instagram_business_account": p.get("instagram_business_account"),
                    "has_instagram": bool(p.get("instagram_business_account")),
                    "never_expires": True
                }
                for p in pages
            ]
        }
    except Exception as e:
        logger.error(f"Failed to fetch user pages: {e}")
        raise HTTPException(status_code=400, detail=_safe_error(e))


@router.post("/api/meta/subscribe-page", tags=["Meta Integration"])
async def subscribe_page_to_app():
    """
    Subscribes the Facebook Page and/or Instagram account to the App for real-time Webhook delivery.
    Calls POST /{page_id}/subscribed_apps?subscribed_fields=feed,messages
    """
    if not settings.META_PAGE_ACCESS_TOKEN:
        raise HTTPException(status_code=400, detail="META_PAGE_ACCESS_TOKEN is required.")

    page_id = settings.META_PAGE_ID or "me"
    results = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Subscribe Facebook Page
        try:
            fb_resp = await client.post(
                f"{settings.META_GRAPH_API_BASE_URL}/{page_id}/subscribed_apps",
                data={
                    "subscribed_fields": "feed,messages,conversations",
                    "access_token": settings.META_PAGE_ACCESS_TOKEN
                }
            )
            results["facebook_page"] = fb_resp.json()
        except Exception as e:
            results["facebook_page"] = {"error": str(e)}

        # 2. Subscribe Instagram account if configured
        if settings.META_INSTAGRAM_ACCOUNT_ID:
            try:
                ig_resp = await client.post(
                    f"{settings.META_GRAPH_API_BASE_URL}/{settings.META_INSTAGRAM_ACCOUNT_ID}/subscribed_apps",
                    data={
                        "subscribed_fields": "comments,messages,messaging_postbacks",
                        "access_token": settings.META_PAGE_ACCESS_TOKEN
                    }
                )
                results["instagram_account"] = ig_resp.json()
            except Exception as e:
                results["instagram_account"] = {"error": str(e)}

    return {"status": "success", "subscriptions": results}
