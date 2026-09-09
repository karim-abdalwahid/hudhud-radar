"""
Leads & Conversations API — migrated verbatim from main.py (WS0.3).

Owned by module 'leads'. Registered via src/modules/leads/__init__.py.
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
# 3. Leads and Conversations APIs
# --------------------------------------------------------------------
@router.get("/api/leads", tags=["Leads"])
async def list_leads(limit: int = 100, request: Request = None):
    """Per-user isolation (Phase 9.5): non-admin users see ONLY their own
    leads; admins see the workspace (until Phase 9 assign-scoping lands)."""
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    from fastapi import Request as _R
    session = None
    if request:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="غير مصرح")
    uid = None if session.get("role") == "admin" else session.get("sub")
    return {"leads": lead_service.get_all_leads(limit, user_id=uid)}


@router.get("/api/leads/{lead_id}", tags=["Leads"])
async def get_lead(lead_id: str, request: Request = None):
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = None
    if request:
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="غير مصرح")
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # isolation: regular users cannot read other users' leads
    if session.get("role") != "admin" and lead.get("user_id") not in (None, session.get("sub")):
        raise HTTPException(status_code=403, detail="غير مصرح — هذا العميل ليس ضمن حسابك")
    messages = lead_service.get_messages_for_lead(lead_id)
    return {"lead": lead, "messages": messages}
