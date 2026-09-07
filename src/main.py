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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.core.admin_alerts import collect_alerts
from src.core.auth import (
    create_session_token,
    verify_session_token,
    user_store,
    auth_limiter,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    PUBLIC_EXACT_PATHS,
    PUBLIC_PATH_PREFIXES,
    ADMIN_EXACT_PATHS,
    ADMIN_PAGE_PATHS,
    ADMIN_PATH_PREFIXES,
    ADMIN_MUTATION_PREFIXES,
)
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
from src.meta_api.extended_api import (
    meta_insights_sync,
    threads_publisher,
    marketing_leads_sync,
)
from src.meta_api.threads_oauth import threads_oauth as threads_oauth_manager
from src.meta_api.compliance_pages import register_compliance_routes
from src.ai.provider_manager import ai_provider_manager

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
    try:
        knowledge_base.reload()
    except Exception as e:
        logger.warning(f"Could not load local knowledge base markdown files: {e}")

    # In serverless environments (Vercel, Lambda), background infinite loops are disabled
    is_serverless = bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("LAMBDA_TASK_ROOT")
    )
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
    version="1.1.0",
    lifespan=lifespan
)


# --------------------------------------------------------------------
# Authentication Middleware: protects dashboard pages & APIs
# --------------------------------------------------------------------
def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PATH_PREFIXES)


def _is_admin_route(path: str, method: str) -> bool:
    if path in ADMIN_EXACT_PATHS or path in ADMIN_PAGE_PATHS:
        return True
    if any(path.startswith(p) for p in ADMIN_PATH_PREFIXES):
        return True
    if method != "GET" and any(path.startswith(p) for p in ADMIN_MUTATION_PREFIXES):
        return True
    return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if _is_public(path):
        return await call_next(request)

    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    request.state.session = session

    if not session:
        if path.startswith("/api/") or path.startswith("/webhooks"):
            return JSONResponse(status_code=401, content={"detail": "غير مصرح — يرجى تسجيل الدخول"})
        return RedirectResponse(url=f"/login?next={path}", status_code=303)

    if _is_admin_route(path, request.method) and session.get("role") != "admin":
        if path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"detail": "هذه العملية تتطلب صلاحيات المدير"})
        return HTMLResponse(
            content="<h1 style='font-family:sans-serif;direction:rtl'>403 — هذه الصفحة للمدير فقط</h1>",
            status_code=403,
        )

    return await call_next(request)


# --------------------------------------------------------------------
# Auth Pages & API
# --------------------------------------------------------------------
class RegisterPayload(BaseModel):
    email: str
    password: str
    phone: Optional[str] = None
    full_name: Optional[str] = None


class LoginPayload(BaseModel):
    email: str
    password: str


class AuthErrorResponse(BaseModel):
    detail: str


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
@app.get("/register", response_class=HTMLResponse, include_in_schema=False)
async def auth_page(request: Request):
    """SendRad-style login/register page with phone field (owner requirement)."""
    return HTMLResponse((TEMPLATES_DIR / "auth.html").read_text(encoding="utf-8"))


@app.post("/auth/register", tags=["Auth"])
async def register_user(payload: RegisterPayload, request: Request):
    """Creates a new account. First-ever user becomes admin (owner)."""
    client_ip = request.client.host if request.client else "unknown"
    if auth_limiter.is_blocked(f"reg:{client_ip}"):
        raise HTTPException(status_code=429, detail="محاولات كثيرة — انتظر 5 دقائق")

    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 8 أحرف على الأقل")
    if "@" not in payload.email or "." not in payload.email:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني غير صالح")
    if user_store.count() >= 50:
        raise HTTPException(status_code=403, detail="التسجيل مغلق حالياً")

    auth_limiter.record(f"reg:{client_ip}")
    try:
        user = user_store.create_user(
            email=payload.email,
            password=payload.password,
            phone=payload.phone,
            full_name=payload.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    token = create_session_token(user["id"], user.get("role", "user"), user["email"])
    resp = JSONResponse({"status": "success", "role": user.get("role", "user")})
    resp.set_cookie(
        SESSION_COOKIE_NAME, token,
        max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax",
        secure=(settings.APP_ENV.lower() == "production"),
    )
    return resp


@app.post("/auth/login", tags=["Auth"])
async def login_user(payload: LoginPayload, request: Request):
    """Authenticates a user and issues a signed session cookie."""
    client_ip = request.client.host if request.client else "unknown"
    if auth_limiter.is_blocked(f"login:{client_ip}"):
        raise HTTPException(status_code=429, detail="محاولات كثيرة — انتظر 5 دقائق")

    user = user_store.authenticate(payload.email, payload.password)
    if not user:
        auth_limiter.record(f"login:{client_ip}")
        raise HTTPException(status_code=401, detail="البريد الإلكتروني أو كلمة المرور غير صحيحة")

    token = create_session_token(user["id"], user.get("role", "user"), user["email"])
    resp = JSONResponse({"status": "success", "role": user.get("role", "user")})
    resp.set_cookie(
        SESSION_COOKIE_NAME, token,
        max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax",
        secure=(settings.APP_ENV.lower() == "production"),
    )
    return resp


@app.post("/auth/logout", tags=["Auth"])
async def logout_user():
    """Clears the session cookie."""
    resp = JSONResponse({"status": "success"})
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


# --------------------------------------------------------------------
# Google OAuth via Supabase Auth
# --------------------------------------------------------------------
@app.get("/auth/google", tags=["Auth"])
async def google_oauth_start(request: Request):
    """
    Redirects the browser to Supabase Auth's Google OAuth flow.
    redirectTo brings the user back to our session-exchange endpoint.
    """
    from urllib.parse import quote
    if not settings.SUPABASE_URL:
        raise HTTPException(status_code=500, detail="Supabase غير مضبوط")
    redirect_to = f"{request.base_url.scheme}://{request.base_url.netloc}/auth/google/callback" if hasattr(request.base_url, "scheme") else "/auth/google/callback"
    url = (
        f"{settings.SUPABASE_URL}/auth/v1/authorize?provider=google"
        f"&redirect_to={quote(str(request.url).rsplit('/auth/google', 1)[0] + '/auth/google/callback')}"
    )
    return RedirectResponse(url=url, status_code=303)


@app.get("/auth/google/callback", tags=["Auth"])
async def google_oauth_callback(request: Request):
    """
    Receives the Supabase redirect with the access token in the URL fragment.
    Since fragments never reach the server, this page runs a small script that
    posts the tokens to /auth/google/exchange, then we set our signed session.
    """
    html = """<!DOCTYPE html><html><body><script>
    const h = {};
    location.hash.slice(1).split('&').forEach(p => { const [k,v] = p.split('='); if(k) h[k] = decodeURIComponent(v); });
    fetch('/auth/google/exchange', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ access_token: h['access_token'], refresh_token: h['refresh_token'] })
    }).then(r => r.json()).then(d => {
        if (d.status === 'success') window.location.href = '/dashboard';
        else window.location.href = '/login?google=error';
    }).catch(() => window.location.href = '/login?google=error');
    </script></body></html>"""
    return HTMLResponse(content=html)


class GoogleExchangePayload(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None


@app.post("/auth/google/exchange", tags=["Auth"])
async def google_oauth_exchange(payload: GoogleExchangePayload):
    """
    Validates the Supabase access token with Supabase Auth (/auth/v1/user),
    then creates-or-syncs the user in our `users` table and issues a signed
    session cookie (same session as password login).
    """
    from src.core.auth import user_store as us
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase غير مضبوط")
    try:
        r = httpx.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={"apikey": settings.SUPABASE_KEY, "Authorization": f"Bearer {payload.access_token}"},
            timeout=15,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="رمز Google غير صالح")
        gu = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ تحقق: {e}")

    email = (gu.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="حساب Google بلا بريد إلكتروني")

    # Create-or-sync local user
    local = us.get_by_email(email)
    if not local:
        meta = gu.get("user_metadata") or {}
        # Supabase Auth users live separately; our users table has no password for them
        try:
            from src.core.supabase_client import supabase_db
            record = {
                "email": email,
                "full_name": meta.get("full_name") or meta.get("name"),
                "phone": meta.get("phone") or None,
                # No password login for OAuth-only accounts; hash set to unusable marker
                "password_hash": "oauth_google",
                "role": "user",
                "is_active": True,
            }
            created = supabase_db.insert("users", record) or record
            local = created if "id" in created else {**record, "id": "google-user"}
        except Exception as e:
            logger.error(f"Google user sync failed: {e}")
            raise HTTPException(status_code=500, detail="تعذر إنشاء الحساب")

    token = create_session_token(local["id"], local.get("role", "user"), local["email"])
    resp = JSONResponse({"status": "success", "role": local.get("role", "user")})
    resp.set_cookie(
        SESSION_COOKIE_NAME, token,
        max_age=SESSION_TTL_SECONDS, httponly=True, samesite="lax",
        secure=(settings.APP_ENV.lower() == "production"),
    )
    return resp


@app.get("/auth/me", tags=["Auth"])
async def whoami(request: Request):
    """Returns the current session user info (reads cookie directly: /auth is public)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    if not session:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_id": session.get("sub"),
        "email": session.get("email"),
        "role": session.get("role"),
    }

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = TEMPLATES_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Register privacy policy + data deletion routes (Meta App Review readiness)
register_compliance_routes(app)


# --------------------------------------------------------------------
# 1. System Health & Info
# --------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "online",
        "app_env": settings.APP_ENV,
        "deploy_marker": "v2-threads-setup",
        "threads_app_configured": bool(settings.THREADS_APP_ID and settings.THREADS_APP_SECRET),
        "cron_configured": bool(settings.CRON_SECRET),
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

    from src.core.event_dedup import event_deduplicator

    queued = 0
    for ev in events:
        if not ev.get("is_echo"):
            # Idempotency: skip events Meta already delivered (prevents duplicate AI replies)
            if not event_deduplicator.claim(f"msg:{ev.get('message_id') or ev.get('sender_id')}:{ev.get('timestamp', '')}", "message"):
                continue
            background_tasks.add_task(agent_orchestrator.process_incoming_message_event, ev)
            queued += 1

    for cev in comment_events:
        if not event_deduplicator.claim(f"comment:{cev.get('comment_id')}", "comment"):
            continue
        background_tasks.add_task(automations_service.process_comment_event, cev)
        queued += 1

    return {"status": "received", "events_queued": queued}



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


import time

_meta_status_cache: Dict[str, Any] = {"ts": 0.0, "data": None}
META_STATUS_CACHE_TTL = 60.0


@app.get("/api/meta/status", tags=["Meta Integration"])
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
        "supabase_url": settings.SUPABASE_URL
    }
    _meta_status_cache["ts"] = now
    _meta_status_cache["data"] = result
    return result


@app.get("/api/meta/posts", tags=["Meta Integration"])
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


@app.post("/api/meta/sync-posts", tags=["Meta Integration"])
async def sync_live_meta_posts():
    """Triggers live synchronization with Meta Graph API for Facebook posts and Instagram reels."""
    result = await meta_feed_sync.sync_all_live_content(limit_per_platform=100)
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

    # Invalidate status cache so the next poll reflects new credentials immediately
    _meta_status_cache["ts"] = 0.0
    _meta_status_cache["data"] = None

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
        # Invalidate status cache so the next poll reflects the new token immediately
        _meta_status_cache["ts"] = 0.0
        _meta_status_cache["data"] = None
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
# Cron Endpoints (Vercel Cron / external cron-job.org)
# Protected by CRON_SECRET (Vercel sends 'Authorization: Bearer $CRON_SECRET').
# --------------------------------------------------------------------
def _verify_cron_secret(request: Request):
    """Validates the cron caller secret when CRON_SECRET is configured.

    Accepts either:
    - Authorization: Bearer <secret> header (Vercel Cron), or
    - ?key=<secret> / ?secret=<secret> query param (cron-job.org free plan
      does not support custom headers).
    """
    secret = settings.CRON_SECRET
    if not secret:
        return  # Not configured (local dev) — allow
    auth_header = request.headers.get("authorization") or ""
    provided = ""
    if auth_header.startswith("Bearer "):
        provided = auth_header[7:].strip()
    if not provided:
        provided = (request.query_params.get("key") or request.query_params.get("secret") or "").strip()
    if not provided or provided != secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


@app.get("/api/cron/scheduler-tick", tags=["Cron"])
async def cron_scheduler_tick(request: Request):
    """
    Cron-safe GET trigger for the content scheduler (serverless environments
    have no background loop). Publishes all posts whose scheduled_for <= now.
    """
    _verify_cron_secret(request)
    results = await content_scheduler.check_and_publish_due_posts()
    return {"status": "success", "due_posts_processed": len(results), "details": results}


@app.get("/api/cron/insights-sync", tags=["Cron"])
async def cron_insights_sync(request: Request):
    """Cron trigger for daily Meta Insights sync (Facebook + Instagram metrics)."""
    _verify_cron_secret(request)
    return await meta_insights_sync.sync_recent_metrics(days=7)


@app.get("/api/admin/alerts", tags=["System"])
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


# --------------------------------------------------------------------
# AI Providers & Models (Phase 8 — opencode-style, admin-managed)
# --------------------------------------------------------------------
class ProviderCreatePayload(BaseModel):
    kind: str = "official"                       # official | custom
    provider_key: str                            # google|anthropic|openai|openrouter|custom-*
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    custom_headers: Optional[List[Dict[str, str]]] = None


class ProviderUpdatePayload(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    custom_headers: Optional[List[Dict[str, str]]] = None
    status: Optional[str] = None                 # active | disabled


class ModelTogglePayload(BaseModel):
    enabled: bool


class ModelAddPayload(BaseModel):
    model_id: str
    display_name: Optional[str] = None


@app.get("/api/ai/providers", tags=["AI Providers"])
async def list_ai_providers(request: Request):
    """Admin: lists all providers (keys masked) with model counts."""
    return {"status": "success", "providers": ai_provider_manager.list_providers()}


@app.post("/api/ai/providers", tags=["AI Providers"])
async def create_ai_provider(payload: ProviderCreatePayload):
    """Admin: connects a provider (official registry key or custom OpenAI-compatible)."""
    try:
        res = ai_provider_manager.create_provider(payload.model_dump())
        # Auto-discover immediately
        sync = ai_provider_manager.sync_provider_models(res["provider_id"])
        return {"status": "success", **res, "sync": {k: v for k, v in sync.items() if k != "models"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/ai/providers/{provider_id}", tags=["AI Providers"])
async def update_ai_provider(provider_id: str, payload: ProviderUpdatePayload):
    ai_provider_manager.update_provider(provider_id, payload.model_dump(exclude_none=True))
    return {"status": "success"}


@app.delete("/api/ai/providers/{provider_id}", tags=["AI Providers"])
async def delete_ai_provider(provider_id: str):
    if not ai_provider_manager.delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "success"}


@app.post("/api/ai/providers/{provider_id}/sync", tags=["AI Providers"])
async def sync_ai_provider_models(provider_id: str):
    """Admin: refresh connection — re-discovers models with current credentials."""
    result = ai_provider_manager.sync_provider_models(provider_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    return result


@app.get("/api/ai/models", tags=["AI Providers"])
async def list_ai_models(provider_id: Optional[str] = None):
    """Admin: all models with toggles; Client usage: pass ?enabled_only=true."""
    models = ai_provider_manager.list_models(provider_id)
    return {"status": "success", "models": models}


@app.get("/api/ai/brains", tags=["AI Providers"])
async def list_client_brains():
    """Client-facing: enabled+available models for the Brain selector."""
    return {"status": "success", "brains": ai_provider_manager.enabled_brain_options()}


@app.post("/api/ai/models/{model_id}/toggle", tags=["AI Providers"])
async def toggle_ai_model(model_id: str, payload: ModelTogglePayload):
    return ai_provider_manager.set_model_toggle(model_id, payload.enabled)


@app.post("/api/ai/providers/{provider_id}/models", tags=["AI Providers"])
async def add_manual_ai_model(provider_id: str, payload: ModelAddPayload):
    try:
        return ai_provider_manager.add_manual_model(provider_id, payload.model_id, payload.display_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/debug/secrets-check", tags=["System"])
async def debug_secrets_check(request: Request):
    """
    Admin-only diagnostic: reports whether each secret is set + its length +
    last 4 chars (safe for display — never returns the secret itself).
    Used to verify deployed environment values match the source of truth.
    """
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request.cookies.get(SESSION_COOKIE_NAME) else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")

    def _info(v: Optional[str]):
        if not v:
            return {"set": False, "length": 0}
        return {"set": True, "length": len(v), "last4": v[-4:]}

    return {
        "status": "success",
        "THREADS_APP_SECRET": _info(settings.THREADS_APP_SECRET),
        "META_APP_SECRET": _info(settings.META_APP_SECRET),
        "GEMINI_API_KEY": _info(settings.GEMINI_API_KEY),
        "CRON_SECRET": _info(settings.CRON_SECRET),
        "META_PAGE_ACCESS_TOKEN": _info(settings.META_PAGE_ACCESS_TOKEN),
        "SUPABASE_URL": _info(settings.SUPABASE_URL),
    }


@app.get("/api/debug/llm-status", tags=["System"])
async def debug_llm_status():
    """
    Admin diagnostic: performs a tiny live Gemini call and reports the exact
    result (model, key prefix, error) so LLM issues can be diagnosed remotely.
    """
    import httpx as _httpx
    key = settings.GEMINI_API_KEY
    info: Dict[str, Any] = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "key_set": bool(key),
        "key_prefix": (key or "")[:8],
    }
    if not key:
        info["ok"] = False
        info["error"] = "GEMINI_API_KEY not set in environment"
        return info
    try:
        async with _httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent",
                headers={"Content-Type": "application/json", "X-goog-api-key": key},
                json={"contents": [{"parts": [{"text": "Reply with exactly: OK"}]}],
                      "generationConfig": {"maxOutputTokens": 10, "thinkingConfig": {"thinkingBudget": 0}}},
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


# --------------------------------------------------------------------
# Extended Meta APIs: Threads & Marketing (spec v2.1 scopes)
# --------------------------------------------------------------------
class ThreadsPublishPayload(BaseModel):
    text: str
    link: Optional[str] = None


@app.get("/api/threads/status", tags=["Threads"])
async def threads_connection_status():
    """Returns Threads OAuth connection status (app configured + token state)."""
    return threads_oauth_manager.get_status()


@app.get("/api/threads/oauth/authorize", tags=["Threads"])
async def threads_oauth_authorize():
    """Builds the Threads OAuth authorization URL (admin clicks it to connect)."""
    result = threads_oauth_manager.build_authorize_url()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


@app.get("/api/threads/oauth/callback", tags=["Threads"])
async def threads_oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """
    OAuth redirect target. Validates the CSRF state, exchanges the code for a
    60-day token, persists it, then redirects to /settings with a result flag.
    """
    if not code or not threads_oauth_manager.validate_state(state):
        return RedirectResponse(url="/settings?threads=error", status_code=303)
    result = await threads_oauth_manager.exchange_code(code)
    if result.get("status") != "success":
        return RedirectResponse(url="/settings?threads=error", status_code=303)
    return RedirectResponse(url=f"/settings?threads=connected&username={result.get('username', '')}", status_code=303)


@app.post("/api/threads/oauth/refresh", tags=["Threads"])
async def threads_oauth_refresh():
    """Refreshes the 60-day Threads token (safe to call periodically)."""
    result = await threads_oauth_manager.refresh_token()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["detail"])
    return result


@app.post("/api/threads/disconnect", tags=["Threads"])
async def threads_disconnect():
    """Removes stored Threads credentials."""
    return threads_oauth_manager.disconnect()


@app.post("/api/threads/publish", tags=["Threads"])
async def publish_threads_post(payload: ThreadsPublishPayload):
    """Publishes a text thread via the official Threads API (own OAuth app)."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="نص الثريد فارغ")
    result = await threads_publisher.publish_thread(payload.text, payload.link)
    if result.get("status") == "error":
        raise HTTPException(status_code=502, detail=result.get("detail", "Threads publish failed"))
    return result


@app.get("/api/threads/{thread_id}/replies", tags=["Threads"])
async def get_threads_replies(thread_id: str, limit: int = Query(20, ge=1, le=100)):
    """Reads replies of a published thread."""
    return await threads_publisher.get_thread_replies(thread_id, limit)


@app.post("/api/marketing/sync-leads", tags=["Marketing API"])
async def sync_marketing_leads(form_id: Optional[str] = None):
    """Imports Meta Lead Ads leads into the CRM with full provenance."""
    return await marketing_leads_sync.sync_lead_forms(form_id)


@app.post("/api/marketing/sync-campaigns", tags=["Marketing API"])
async def sync_marketing_campaigns():
    """Pulls ad campaign performance metrics into the campaigns table."""
    return await marketing_leads_sync.sync_campaign_insights()


# --------------------------------------------------------------------
# 6.5 Knowledge Base, Meta Scraping & RAG Management
# --------------------------------------------------------------------
class SaveDocumentRequest(BaseModel):
    content: str


class CreateDocumentRequest(BaseModel):
    filename: str
    content: str


@app.post("/api/knowledge/analyze-meta", tags=["Knowledge Base & RAG"])
async def analyze_meta_posts(limit: int = Query(10, ge=1, le=40)):
    """
    Admin: runs the approved structural analyzer (Entry 021 Phase 5):
    fetches recent posts + their real comments, classifies every comment
    (CTA-response vs real-question vs complaint/spam), and saves REAL
    knowledge documents with mandatory citations. Zero guessing.
    """
    from src.knowledge.meta_analyzer import meta_posts_analyzer
    result = await meta_posts_analyzer.analyze_recent(limit=limit)
    if result.get("status") == "skipped":
        raise HTTPException(status_code=400, detail=result.get("reason", "skipped"))
    return result


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
    """
    Returns real conversation threads built from actual `messages` records.
    Zero-fabrication: every message shown exists in the database.
    """
    from src.core.event_dedup import event_deduplicator  # noqa: F401 (import guard)
    leads = supabase_db.select("leads", {}) or []
    threads = []
    for lead in leads[:50]:
        lead_id = lead.get("id")
        platform = (lead.get("source") or "other").lower()
        # Real message history from the messages table (Zero-Fabrication policy)
        msgs = lead_service.get_messages_for_lead(lead_id) or []
        message_items = []
        last_inbound_at = None
        for m in msgs:
            sender = m.get("sender_type") or "lead"
            if sender == "lead" and m.get("sent_at"):
                last_inbound_at = m.get("sent_at")
            message_items.append({
                "sender": "agent" if sender == "agent" else "customer",
                "text": m.get("content") or "",
                "time": m.get("sent_at") or "",
                "mid": m.get("platform_message_id") or "",
            })
        if not message_items:
            # Lead exists but no conversation yet — show as empty thread (no fabricated chat)
            continue
        display_name = lead.get("full_name") or (lead.get("username") or "Lead")
        threads.append({
            "id": f"conv_{lead_id}",
            "lead_id": lead_id,
            "name": display_name,
            "handle": f"@{lead.get('username')}" if lead.get("username") else "",
            "channel": platform if platform in ("instagram", "facebook") else "instagram",
            "platformText": "📸 Instagram Direct" if platform == "instagram" else ("💬 Messenger" if platform == "facebook" else "💬 Direct"),
            "lastTime": (message_items[-1]["time"] or "Active"),
            "leadStage": "new",
            "contactCaptured": bool(lead.get("contact_phone") or lead.get("contact_email")),
            "isHumanTakeover": bool(lead.get("human_takeover", False)),
            "lastInboundAt": last_inbound_at,
            "messages": message_items
        })
    return {"status": "success", "conversations": threads}


class TakeoverPayload(BaseModel):
    takeover: bool


class ManualMessagePayload(BaseModel):
    text: str


def _get_lead_recipient(lead: Dict[str, Any]) -> Optional[str]:
    """Resolves the platform recipient id for direct messaging a lead."""
    source = (lead.get("source") or "").lower()
    if source == "facebook" and lead.get("facebook_account_id"):
        return lead["facebook_account_id"]
    if source == "instagram" and lead.get("instagram_account_id"):
        return lead["instagram_account_id"]
    return lead.get("facebook_account_id") or lead.get("instagram_account_id")


async def _send_and_store_agent_message(lead: Dict[str, Any], text: str, extra_meta: Optional[Dict[str, Any]] = None):
    """Sends a real DM to the lead via Meta Send API and stores it in messages."""
    from src.meta_api.client import meta_client
    from src.leads.models import MessageCreate, PlatformSource, SenderType
    from datetime import datetime, timezone as tz

    recipient = _get_lead_recipient(lead)
    if not recipient:
        raise HTTPException(status_code=400, detail="لا يوجد معرّف حساب مرتبط بهذا العميل لإرسال رسالة")
    source = (lead.get("source") or "").lower()
    platform = PlatformSource.FACEBOOK if source == "facebook" else PlatformSource.INSTAGRAM

    send_result = {}
    if platform == PlatformSource.FACEBOOK:
        send_result = await meta_client.send_facebook_message(recipient_id=recipient, message_text=text)
    else:
        send_result = await meta_client.send_instagram_message(recipient_id=recipient, message_text=text)

    stored = lead_service.add_message(MessageCreate(
        lead_id=lead["id"],
        platform=platform,
        platform_message_id=send_result.get("message_id"),
        sender_type=SenderType.AGENT,
        content=text,
        sent_at=datetime.now(tz.utc),
        metadata=extra_meta or {},
    ))
    return {"message_id": send_result.get("message_id"), "stored": stored is not None}


@app.post("/api/inbox/conversations/{lead_id}/takeover", tags=["Live Inbox"])
async def set_human_takeover(lead_id: str, payload: TakeoverPayload):
    """
    Human Takeover: pauses/resumes the AI agent for this lead.
    The orchestrator checks this flag before generating auto-replies.
    """
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    updated = lead_service.update_lead(lead_id, {"human_takeover": bool(payload.takeover)})
    return {
        "status": "success",
        "lead_id": lead_id,
        "human_takeover": bool((updated or {}).get("human_takeover", False)),
        "message": "تم إيقاف الردود الآلية لهذه المحادثة" if payload.takeover else "تم استئناف الردود الآلية"
    }


@app.post("/api/inbox/conversations/{lead_id}/send-message", tags=["Live Inbox"])
async def send_manual_inbox_message(lead_id: str, payload: ManualMessagePayload):
    """
    Sends a REAL human message to the lead (Human Takeover chat) and stores it.
    Also enables takeover automatically so the AI does not double-reply.
    """
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="نص الرسالة فارغ")
    result = await _send_and_store_agent_message(lead, text, extra_meta={"sent_by": "human"})
    if not lead.get("human_takeover"):
        lead_service.update_lead(lead_id, {"human_takeover": True})
    return {"status": "success", **result}


@app.post("/api/inbox/conversations/{lead_id}/send-booking-link", tags=["Live Inbox"])
async def send_booking_link_message(lead_id: str):
    """
    Sends the configured booking link (saved via Onboarding -> rules_and_guidelines.md)
    as a real DM. Zero-fabrication: if no link is configured, an explicit error is returned.
    """
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    import re as _re
    guidelines = knowledge_base.get_document("rules_and_guidelines.md") or ""
    match = _re.search(r"https?://[^\s\)\]]+", guidelines)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="لم يتم تحديد رابط حجز المواعيد بعد — أضفه من صفحة الإعدادات (Onboarding) أولاً"
        )
    booking_link = match.group(0)
    text = f"يسعدنا تواصلك! تقدر تحجز مكالمة استشارية مجانية مع فريقنا من هنا: {booking_link}"
    result = await _send_and_store_agent_message(lead, text, extra_meta={"sent_by": "human", "type": "booking_link"})
    return {"status": "success", **result}

