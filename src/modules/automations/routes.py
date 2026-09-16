"""
Visual Automations & Workflows API — migrated verbatim from main.py (WS0.3).

Owned by module 'automations'. Registered via src/modules/automations/__init__.py.
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
# 10.5 Visual Automations & Workflows API Endpoints
# --------------------------------------------------------------------
from src.automations.models import WorkflowCreate, WorkflowUpdate


def _session_user_id(request: Request) -> str:
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    if not session or not session.get("sub"):
        raise HTTPException(status_code=401, detail="غير مصرح")
    return str(session["sub"])


@router.get("/api/automations", tags=["Automations"])
async def list_automations(request: Request):
    """Lists only the current tenant's automation workflows."""
    user_id = _session_user_id(request)
    return {"status": "success", "workflows": [
        w.model_dump() for w in automations_service.list_workflows(user_id=user_id)]}


@router.post("/api/automations", tags=["Automations"])
async def create_automation(payload: WorkflowCreate, request: Request):
    """Creates a new automation workflow."""
    try:
        wf = automations_service.create_workflow(payload, user_id=_session_user_id(request))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"status": "success", "workflow": wf.model_dump()}


@router.get("/api/automations/{wf_id}", tags=["Automations"])
async def get_automation(wf_id: str, request: Request):
    """Fetches details of a specific automation workflow."""
    wf = automations_service.get_workflow(wf_id, user_id=_session_user_id(request))
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "workflow": wf.model_dump()}


@router.put("/api/automations/{wf_id}", tags=["Automations"])
async def update_automation(wf_id: str, payload: WorkflowUpdate, request: Request):
    """Updates an automation workflow nodes, connections, and metadata."""
    wf = automations_service.update_workflow(wf_id, payload, user_id=_session_user_id(request))
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "workflow": wf.model_dump()}


@router.delete("/api/automations/{wf_id}", tags=["Automations"])
async def delete_automation(wf_id: str, request: Request):
    """Deletes an automation workflow."""
    ok = automations_service.delete_workflow(wf_id, user_id=_session_user_id(request))
    if not ok:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "message": "Workflow deleted"}


@router.post("/api/automations/{wf_id}/toggle", tags=["Automations"])
async def toggle_automation_status(wf_id: str, request: Request):
    """Toggles active/paused status of a workflow."""
    wf = automations_service.toggle_status(wf_id, user_id=_session_user_id(request))
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"status": "success", "status_state": wf.status, "workflow": wf.model_dump()}


@router.post("/api/automations/{wf_id}/test", tags=["Automations"])
async def test_automation_workflow(wf_id: str, request: Request,
                                   sample_payload: Optional[Dict[str, Any]] = None):
    """Simulates an execution run across all nodes and connectors in the workflow."""
    result = automations_service.simulate_execution(
        wf_id, sample_payload, user_id=_session_user_id(request))
    return result
