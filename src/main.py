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
import httpx
import asyncio
from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, HTTPException, Query, BackgroundTasks, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db
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
    knowledge_base.reload()

    # In serverless environments (Vercel, Lambda), background infinite loops are disabled
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
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
    version="1.0.0",
    lifespan=lifespan
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = TEMPLATES_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --------------------------------------------------------------------
# 1. System Health & Info
# --------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "online",
        "app_env": settings.APP_ENV,
        "supabase_connected": supabase_db.is_connected,
        "database_backend": "Supabase Cloud" if supabase_db.is_connected else "In-Memory Store (Dev)",
        "kb_documents_loaded": len(knowledge_base.knowledge_cache),
        "enforce_24h_window": settings.ENFORCE_24H_WINDOW,
        "max_messages_per_minute": settings.MAX_MESSAGES_PER_MINUTE
    }


# --------------------------------------------------------------------
# 2. Meta Webhooks (Verification & Intake)
# Supports multiple common paths: /webhooks/meta, /api/webhook/meta, /api/webhook/instagram
# --------------------------------------------------------------------
@app.get("/webhooks/meta", tags=["Webhooks"])
@app.get("/api/webhook/meta", tags=["Webhooks"])
@app.get("/api/webhook/instagram", tags=["Webhooks"])
@app.get("/api/webhooks/meta", tags=["Webhooks"])
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """Verifies Webhook subscription challenge sent by Meta."""
    challenge = webhook_handler.verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/webhooks/meta", tags=["Webhooks"])
@app.post("/api/webhook/meta", tags=["Webhooks"])
@app.post("/api/webhook/instagram", tags=["Webhooks"])
@app.post("/api/webhooks/meta", tags=["Webhooks"])
async def receive_meta_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives incoming webhook events from Facebook and Instagram.
    Validates HMAC signature and processes messaging and comment events asynchronously.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Validate HMAC signature
    if not webhook_handler.verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid HMAC SHA-256 signature")

    payload = await request.json()
    events = webhook_handler.parse_messaging_events(payload)
    comment_events = webhook_handler.parse_comment_events(payload)

    for ev in events:
        if not ev.get("is_echo"):
            background_tasks.add_task(agent_orchestrator.process_incoming_message_event, ev)

    for cev in comment_events:
        background_tasks.add_task(automations_service.process_comment_event, cev)

    return {"status": "received", "events_queued": len(events) + len(comment_events)}



# --------------------------------------------------------------------
# 3. Leads and Conversations APIs
# --------------------------------------------------------------------
@app.get("/api/leads", tags=["Leads"])
async def list_leads(limit: int = 100):
    return {"leads": lead_service.get_all_leads(limit)}


@app.get("/api/leads/{lead_id}", tags=["Leads"])
async def get_lead(lead_id: str):
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    messages = lead_service.get_messages_for_lead(lead_id)
    return {"lead": lead, "messages": messages}


# --------------------------------------------------------------------
# 4. Identity Resolution Manual Review Queue
# --------------------------------------------------------------------
@app.get("/api/identity/queue", tags=["Identity Resolution"])
async def get_verification_queue():
    """Lists pending ambiguous matches awaiting human supervisor decision."""
    return {"pending_reviews": identity_review_queue.get_pending_reviews()}


@app.post("/api/identity/queue/{queue_id}/approve", tags=["Identity Resolution"])
async def approve_identity_link(queue_id: str, reviewer: str = "Admin", notes: Optional[str] = None):
    """Explicitly confirms linking two accounts as belonging to the same human identity."""
    try:
        updated = identity_review_queue.approve_match(queue_id, reviewer, notes)
        return {"status": "approved", "queue_item": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/identity/queue/{queue_id}/reject", tags=["Identity Resolution"])
async def reject_identity_link(queue_id: str, reviewer: str = "Admin", notes: Optional[str] = None):
    """Explicitly rejects candidate match, keeping both records distinct."""
    try:
        updated = identity_review_queue.reject_match(queue_id, reviewer, notes)
        return {"status": "rejected", "queue_item": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --------------------------------------------------------------------
# 5. Analytics & Performance Reports
# --------------------------------------------------------------------
@app.get("/api/analytics/summary", tags=["Analytics"])
async def get_analytics_summary():
    """Returns granular analytics on operations, success/failure rate, and root causes."""
    return {
        "operations": statistics_engine.get_operations_summary(),
        "leads_and_conversions": statistics_engine.get_lead_conversion_metrics()
    }


@app.get("/api/reports/page-performance", tags=["Reports"])
async def get_page_performance_report():
    """Returns rendered page performance report in Markdown."""
    md = report_generator.generate_page_performance_report_md()
    return {"report_markdown": md}


@app.get("/api/reports/activity-execution", tags=["Reports"])
async def get_activity_execution_report():
    """Returns rendered activity execution and failure root-cause report in Markdown."""
    md = report_generator.generate_activity_execution_report_md()
    return {"report_markdown": md}


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


@app.get("/api/meta/status", tags=["Meta Integration"])
async def get_meta_status():
    """Checks the live connection status of Meta Facebook Page and Instagram Account."""
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

    return {
        "configured": has_token,
        "token_valid": token_valid,
        "page_name": page_name,
        "page_id": page_id,
        "instagram_account_id": active_ig_id or None,
        "app_id": settings.META_APP_ID or None,
        "supabase_connected": supabase_db.is_connected,
        "supabase_url": settings.SUPABASE_URL
    }


@app.get("/api/meta/posts", tags=["Meta Integration"])
async def get_live_meta_posts(
    platform: Optional[str] = Query("all"),
    post_type: Optional[str] = Query("all"),
    limit: int = Query(50, ge=1, le=100)
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


@app.post("/api/meta/sync-posts", tags=["Meta Integration"])
async def sync_live_meta_posts():
    """Triggers live synchronization with Meta Graph API for Facebook posts and Instagram reels."""
    result = await meta_feed_sync.sync_all_live_content()
    return result


@app.post("/api/meta/configure", tags=["Meta Integration"])
async def configure_meta_credentials(payload: MetaConfigPayload):
    """Updates and validates Meta Facebook & Instagram credentials in runtime and .env."""
    page_name = None
    if payload.page_access_token:
        try:
            resp = httpx.get(
                f"{settings.META_GRAPH_API_BASE_URL}/me?fields=id,name&access_token={payload.page_access_token}",
                timeout=5.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"فشل التحقق من التوكن عبر Meta Graph API: {resp.text}")
            data = resp.json()
            page_name = data.get("name")
            if not payload.page_id:
                payload.page_id = data.get("id")
        except httpx.RequestError as e:
            raise HTTPException(status_code=400, detail=f"خطأ في الاتصال بسيرفرات فيسبوك: {e}")

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

    return {
        "status": "success",
        "message": f"تم ربط والتحقق من حساب فيسبوك بنجاح! صفحة: {page_name or payload.page_id}",
        "page_name": page_name,
        "page_id": payload.page_id
    }


@app.post("/api/meta/exchange-token", tags=["Meta Integration"])
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
        return result
    except Exception as e:
        logger.error(f"Failed to generate permanent token: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/meta/user-pages", tags=["Meta Integration"])
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
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/meta/subscribe-page", tags=["Meta Integration"])
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


# --------------------------------------------------------------------
# 6. Content Studio (AI Generation, Publishing & Scheduling)
# --------------------------------------------------------------------
@app.post("/api/content/generate", response_model=ContentGenerationResponse, tags=["Content Studio"])
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


@app.post("/api/content/compliance-check", tags=["Content Studio"])
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


@app.post("/api/content/posts", response_model=ContentPostResponse, tags=["Content Studio"])
async def create_content_post(payload: ContentPostCreate, background_tasks: BackgroundTasks):
    """Creates a draft, scheduled, or instant publishing post."""
    post = content_studio_service.create_post(payload)
    if payload.status == ContentStatus.PUBLISHING:
        background_tasks.add_task(content_scheduler.publish_single_post, post)
    return post


@app.get("/api/content/posts", response_model=List[ContentPostResponse], tags=["Content Studio"])
async def list_content_posts(
    status: Optional[ContentStatus] = None,
    platform: Optional[ContentPlatform] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Lists saved, scheduled, and published posts."""
    return content_studio_service.list_posts(status=status, platform=platform, limit=limit)


@app.get("/api/studio/posts", tags=["Content Studio"])
async def alias_list_studio_posts(
    status: Optional[ContentStatus] = None,
    platform: Optional[ContentPlatform] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Alias for /api/content/posts for backward compatibility with frontend dashboard."""
    return content_studio_service.list_posts(status=status, platform=platform, limit=limit)


@app.get("/api/content/posts/{post_id}", response_model=ContentPostResponse, tags=["Content Studio"])
async def get_content_post(post_id: str):
    """Fetches a specific post by ID."""
    post = content_studio_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.post("/api/content/posts/{post_id}/publish-now", tags=["Content Studio"])
async def publish_post_now(post_id: str):
    """Instantly publishes a drafted or scheduled post."""
    post = content_studio_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    result = await content_scheduler.publish_single_post(post)
    return result


@app.delete("/api/content/posts/{post_id}", tags=["Content Studio"])
async def delete_content_post(post_id: str):
    """Deletes a content post."""
    success = content_studio_service.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
    return {"status": "success", "message": f"Post {post_id} deleted successfully"}


@app.post("/api/content/scheduler/trigger", tags=["Content Studio"])
async def trigger_scheduler_tick():
    """Manually checks and executes all scheduled posts that are due."""
    results = await content_scheduler.check_and_publish_due_posts()
    return {"status": "success", "due_posts_processed": len(results), "details": results}


# --------------------------------------------------------------------
# 6.5 Knowledge Base, Meta Scraping & RAG Management
# --------------------------------------------------------------------
class SaveDocumentRequest(BaseModel):
    content: str


class CreateDocumentRequest(BaseModel):
    filename: str
    content: str


@app.post("/api/knowledge/sync-meta", tags=["Knowledge Base & RAG"])
async def sync_knowledge_from_meta():
    """Scrapes historical Facebook/Instagram posts, reels, and comments and synthesizes business knowledge."""
    raw_data = await meta_crawler.fetch_all_historical_content()
    res = await knowledge_synthesizer.synthesize_and_save(raw_data)
    return res


@app.get("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def list_knowledge_documents():
    """Lists all stored knowledge base documents with word count, size, and status."""
    return {"documents": knowledge_base.list_documents()}


@app.get("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def get_knowledge_document(filename: str):
    """Retrieves raw content of a specific knowledge base document."""
    content = knowledge_base.get_document(filename)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    return {"filename": filename, "content": content}


@app.put("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def update_knowledge_document(filename: str, payload: SaveDocumentRequest):
    """Updates a knowledge document and instantly reloads the AI agent's memory."""
    res = knowledge_base.save_document(filename, payload.content)
    return res


@app.post("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def create_knowledge_document(payload: CreateDocumentRequest):
    """Creates a new knowledge document and hot-reloads the agent's memory."""
    res = knowledge_base.save_document(payload.filename, payload.content)
    return res


@app.delete("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def delete_knowledge_document(filename: str):
    """Deletes a document from the knowledge base and reloads memory."""
    success = knowledge_base.delete_document(filename)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found or could not be deleted")
    return {"status": "success", "message": f"Document '{filename}' deleted successfully"}


@app.post("/api/knowledge/upload", tags=["Knowledge Base & RAG"])
async def upload_knowledge_file(file: UploadFile = File(...)):
    """
    Multi-format file uploader:
    - .md / .txt: Parsed and stored into Knowledge Base.
    - .pdf: Extracted page-by-page and converted to structured Markdown.
    - .png / .jpg / .jpeg / .webp: Analyzed using Gemini Multimodal Vision to extract business facts.
    """
    # Sanitize base filename to eliminate any directory traversal attempt
    safe_base = Path(file.filename or "upload").name
    ext = Path(safe_base).suffix.lower()

    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="الملف المرفوع فارغ.")

        if ext in [".md", ".txt"]:
            text_content = file_bytes.decode("utf-8", errors="replace")
            return document_processor.process_text_or_markdown(safe_base, text_content)
        elif ext == ".pdf":
            return document_processor.process_pdf(safe_base, file_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            mime = file.content_type or "image/jpeg"
            return await document_processor.process_image_vision(safe_base, file_bytes, mime_type=mime)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"صيغة الملف غير مدعومة ({ext}). الصيغ المدعومة هي: .md, .txt, .pdf, .png, .jpg, .webp"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded file {safe_base}: {e}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء معالجة الملف: {str(e)}")


class SearchKnowledgeRequest(BaseModel):
    query: str
    top_k: int = 3


@app.post("/api/knowledge/search", tags=["Knowledge Base & RAG"])
async def search_knowledge(payload: SearchKnowledgeRequest):
    """
    Executes LEANN-inspired lightweight hybrid semantic search:
    Vector cosine similarity + keyword RRF fusion across knowledge base.
    """
    from src.knowledge.semantic_engine import semantic_engine
    if not knowledge_base.knowledge_cache:
        knowledge_base.reload()

    results = semantic_engine.hybrid_search(
        query=payload.query,
        documents=knowledge_base.knowledge_cache,
        top_k=payload.top_k
    )
    return {
        "query": payload.query,
        "results": [
            {
                "score": round(score, 4),
                "filename": filename,
                "chunk": chunk
            }
            for score, filename, chunk in results
        ]
    }


# --------------------------------------------------------------------
# 7. Dedicated Multi-Page SaaS Web Application Routes
# --------------------------------------------------------------------
def render_page_template(filename: str, request: Optional[Request] = None) -> HTMLResponse:
    """Reads and serves dedicated SaaS page template with language-aware initial tags."""
    target = TEMPLATES_DIR / filename
    if target.exists():
        content = target.read_text(encoding="utf-8")
        lang = "en"
        if request:
            lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        if lang == "ar":
            content = content.replace('<html lang="en" dir="ltr">', '<html lang="ar" dir="rtl">')
        else:
            content = content.replace('<html lang="ar" dir="rtl">', '<html lang="en" dir="ltr">')
        return HTMLResponse(content=content)
    return HTMLResponse(content=f"<h1>Page template '{filename}' not found</h1>", status_code=404)


@app.get("/", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_landing(request: Request):
    """SendRad-style World-Class Marketing & Feature Landing Page."""
    return render_page_template("landing.html", request)


@app.get("/dashboard", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_overview(request: Request):
    """Executive Overview Dashboard."""
    return render_page_template("overview.html", request)


@app.get("/leads", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_leads(request: Request):
    """Leads CRM & Contact Management Workspace."""
    return render_page_template("leads.html", request)


@app.get("/studio", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_studio(request: Request):
    """AI Content Studio, Post Composer & Scheduler Workspace."""
    return render_page_template("studio.html", request)


@app.get("/knowledge", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_knowledge(request: Request):
    """Knowledge Base, Markdown Editor & LEANN Semantic Search Studio."""
    return render_page_template("knowledge.html", request)


@app.get("/identity", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_identity(request: Request):
    """Identity Verification & Human-in-the-Loop Review Queue."""
    return render_page_template("identity.html", request)


@app.get("/analytics", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_analytics(request: Request):
    """Analytics, Root Cause Analysis (RCA) & Executive Reports."""
    return render_page_template("analytics.html", request)


@app.get("/onboarding", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_onboarding(request: Request):
    """SendRad-style 3-Step Setup Wizard for Business Knowledge, Agent Persona & Channels."""
    return render_page_template("onboarding.html", request)


@app.get("/inbox", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_inbox(request: Request):
    """Unified Live Messaging Inbox with Human Takeover & Lead Qualification."""
    return render_page_template("inbox.html", request)


@app.get("/settings", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_settings(request: Request):
    """Meta Platforms Connection, Webhooks & System Settings."""
    return render_page_template("settings.html", request)


@app.get("/automations", response_class=HTMLResponse, tags=["SaaS Pages"])
async def page_automations(request: Request):
    """Visual Automation & Workflows Canvas Builder Workspace."""
    return render_page_template("automations.html", request)


# --------------------------------------------------------------------
# 10.5 Visual Automations & Workflows API Endpoints
# --------------------------------------------------------------------
from src.automations.models import WorkflowCreate, WorkflowUpdate


@app.get("/api/automations", tags=["Automations"])
async def list_automations():
    """Lists all configured automation workflows."""
    return {"status": "success", "workflows": [w.model_dump() for w in automations_service.list_workflows()]}


@app.post("/api/automations", tags=["Automations"])
async def create_automation(payload: WorkflowCreate):
    """Creates a new automation workflow."""
    wf = automations_service.create_workflow(payload)
    return {"status": "success", "workflow": wf.model_dump()}


@app.get("/api/automations/{wf_id}", tags=["Automations"])
async def get_automation(wf_id: str):
    """Fetches details of a specific automation workflow."""
    wf = automations_service.get_workflow(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "workflow": wf.model_dump()}


@app.put("/api/automations/{wf_id}", tags=["Automations"])
async def update_automation(wf_id: str, payload: WorkflowUpdate):
    """Updates an automation workflow nodes, connections, and metadata."""
    wf = automations_service.update_workflow(wf_id, payload)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "workflow": wf.model_dump()}


@app.delete("/api/automations/{wf_id}", tags=["Automations"])
async def delete_automation(wf_id: str):
    """Deletes an automation workflow."""
    ok = automations_service.delete_workflow(wf_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "message": "Workflow deleted"}


@app.post("/api/automations/{wf_id}/toggle", tags=["Automations"])
async def toggle_automation_status(wf_id: str):
    """Toggles active/paused status of a workflow."""
    wf = automations_service.toggle_status(wf_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "status_state": wf.status, "workflow": wf.model_dump()}


@app.post("/api/automations/{wf_id}/test", tags=["Automations"])
async def test_automation_workflow(wf_id: str, sample_payload: Optional[Dict[str, Any]] = None):
    """Simulates an execution run across all nodes and connectors in the workflow."""
    result = automations_service.simulate_execution(wf_id, sample_payload)
    return result


# --------------------------------------------------------------------
# 11. SendRad Onboarding & Live Inbox Endpoints
# --------------------------------------------------------------------
class OnboardingSavePayload(BaseModel):
    knowledge_text: Optional[str] = None
    role: str = "sales"
    brain: str = "gemini"
    tone: str = "friendly"
    booking_link: Optional[str] = None


@app.post("/api/onboarding/save-all", tags=["Onboarding"])
async def save_onboarding_wizard(payload: OnboardingSavePayload):
    """Saves business knowledge, configures agent persona, and sets booking link."""
    # 1. Save Knowledge Base text if provided
    if payload.knowledge_text and payload.knowledge_text.strip():
        knowledge_base.save_document(
            "business_profile.md",
            f"# نبذة عن الشركة والخدمات (Business Profile)\n\n{payload.knowledge_text.strip()}\n"
        )

    # 2. Update agent guidelines with role, tone, and booking link
    guidelines_content = f"""# إرشادات وسياسات الوكيل الذكي (Agent Guidelines)

- **الدور المعتمد (Role):** {payload.role}
- **محرك الذكاء (Brain):** {payload.brain}
- **نبرة الحديث (Tone):** {payload.tone}
- **رابط حجز المواعيد (Booking Link):** {payload.booking_link or 'غير محدد بعد'}

## تعليمات الردود:
1. الرد في غضون 5 ثوانٍ بأسلوب احترافي ودود.
2. التركيز على فهم احتياج العميل ومساعدته للوصول للقرار المناسب.
3. مشاركة رابط حجز المواعيد عندما يطلب العميل مقابلة أو استشارة.
"""
    knowledge_base.save_document("rules_and_guidelines.md", guidelines_content)

    # 3. Update LLM Provider in runtime
    if payload.brain in ["gemini", "openai"]:
        settings.LLM_PROVIDER = payload.brain

    return {
        "status": "success",
        "message": "تم حفظ بيانات وتدريب الوكيل بنجاح!",
        "role": payload.role,
        "brain": payload.brain,
        "tone": payload.tone,
        "booking_link": payload.booking_link
    }


@app.get("/api/inbox/conversations", tags=["Live Inbox"])
async def get_inbox_conversations():
    """Returns real-time conversation threads with lead status and takeover state."""
    leads = supabase_db.select("leads", {}) or []
    threads = []
    for lead in leads[:20]:
        platform = (lead.get("platform") or lead.get("source") or "instagram").lower()
        # Retrieve actual interaction messages if stored in lead record
        raw_msgs = lead.get("messages") or []
        if not raw_msgs and (lead.get("intent") or lead.get("last_message")):
            raw_msgs = [
                {"sender": "customer", "text": lead.get("last_message") or lead.get("intent"), "time": "recently"}
            ]
        threads.append({
            "id": f"conv_{lead.get('id', '0')}",
            "name": lead.get("full_name") or lead.get("username") or "Customer Lead",
            "handle": f"@{lead.get('username', 'user')}",
            "channel": platform,
            "platformText": "📸 Instagram Direct" if "instagram" in platform else "💬 Messenger",
            "lastTime": lead.get("last_contact") or "Active",
            "leadStage": lead.get("status", "new"),
            "leadBadge": f"Lead ({lead.get('lead_score', 0)}%)",
            "need": lead.get("intent") or "General Inquiry",
            "isHumanTakeover": bool(lead.get("human_takeover", False)),
            "messages": raw_msgs
        })
    return {"status": "success", "conversations": threads}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=settings.APP_DEBUG)
