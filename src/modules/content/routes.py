"""
Content Studio (AI Generation, Publishing & Scheduling) — migrated verbatim from main.py (WS0.3).

Owned by module 'content'. Registered via src/modules/content/__init__.py.
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
    ContentGenerationRequest, ContentGenerationResponse,
    ContentPostCreate, ContentPostUpdate, ContentPostResponse,
    ContentPlatform, PostType, ContentStatus, CreationMode,
)

router = APIRouter()

# --------------------------------------------------------------------
# 6. Content Studio (AI Generation, Publishing & Scheduling)
# --------------------------------------------------------------------
@router.post("/api/content/generate", response_model=ContentGenerationResponse, tags=["Content Studio"])
async def generate_ai_content(payload: ContentGenerationRequest):
    """Generates viral Facebook/Instagram copy, Reels scripts, or Story sequences using AI."""
    try:
        res = await content_engine.generate_content(payload)
        return res
    except Exception as e:
        logger.error(f"Error in content generation: {e}")
        raise HTTPException(status_code=500, detail=f"Content generation error: {str(e)}")


class ComplianceCheckRequest(BaseModel):
    content_text: str
    platform: str = "facebook"
    post_type: str = "post"
    media_urls: Optional[List[str]] = None


@router.post("/api/content/compliance-check", tags=["Content Studio"])
async def check_content_compliance(payload: ComplianceCheckRequest):
    """Audits content draft using Ruflo-inspired Compliance Gatekeeper Agent."""
    from src.content_studio.compliance_agent import compliance_gatekeeper
    verdict = compliance_gatekeeper.audit_content(
        content_text=payload.content_text,
        platform=payload.platform,
        post_type=payload.post_type,
        media_urls=payload.media_urls
    )
    return verdict.model_dump()


@router.post("/api/content/posts", response_model=ContentPostResponse, tags=["Content Studio"])
async def create_content_post(payload: ContentPostCreate, background_tasks: BackgroundTasks, request: Request):
    """Creates a draft, scheduled, or instant publishing post (owned by the session user — Wave 9.8)."""
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    user_id = (session or {}).get("sub")
    post = content_studio_service.create_post(payload, user_id=user_id)
    if payload.status == ContentStatus.PUBLISHING:
        background_tasks.add_task(content_scheduler.publish_single_post, post)
    return post


@router.get("/api/content/posts", response_model=List[ContentPostResponse], tags=["Content Studio"])
async def list_content_posts(
    request: Request,
    status: Optional[ContentStatus] = None,
    platform: Optional[ContentPlatform] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Lists the session user's saved, scheduled, and published posts."""
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    user_id = (session or {}).get("sub")
    return content_studio_service.list_posts(status=status, platform=platform, limit=limit, user_id=user_id)


@router.get("/api/studio/posts", tags=["Content Studio"])
async def alias_list_studio_posts(
    request: Request,
    status: Optional[ContentStatus] = None,
    platform: Optional[ContentPlatform] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Alias for /api/content/posts for backward compatibility with frontend dashboard."""
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    user_id = (session or {}).get("sub")
    return content_studio_service.list_posts(status=status, platform=platform, limit=limit, user_id=user_id)


@router.get("/api/content/posts/{post_id}", response_model=ContentPostResponse, tags=["Content Studio"])
async def get_content_post(post_id: str):
    """Fetches a specific post by ID."""
    post = content_studio_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/api/content/posts/{post_id}/publish-now", tags=["Content Studio"])
async def publish_post_now(post_id: str):
    """Instantly publishes a drafted or scheduled post."""
    post = content_studio_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    result = await content_scheduler.publish_single_post(post)
    return result


@router.delete("/api/content/posts/{post_id}", tags=["Content Studio"])
async def delete_content_post(post_id: str):
    """Deletes a content post."""
    success = content_studio_service.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
    return {"status": "success", "message": f"Post {post_id} deleted successfully"}


@router.post("/api/content/scheduler/trigger", tags=["Content Studio"])
async def trigger_scheduler_tick():
    """Manually checks and executes all scheduled posts that are due."""
    results = await content_scheduler.check_and_publish_due_posts()
    return {"status": "success", "due_posts_processed": len(results), "details": results}
