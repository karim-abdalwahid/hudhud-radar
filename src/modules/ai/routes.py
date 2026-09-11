"""
AI Providers & Models (Phase 8) — migrated verbatim from main.py (WS0.3).

Owned by module 'ai'. Registered via src/modules/ai/__init__.py.
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


@router.get("/api/ai/providers", tags=["AI Providers"])
async def list_ai_providers(request: Request):
    """Admin: lists all providers (keys masked) with model counts."""
    return {"status": "success", "providers": ai_provider_manager.list_providers()}


@router.post("/api/ai/providers", tags=["AI Providers"])
async def create_ai_provider(payload: ProviderCreatePayload):
    """Admin: connects a provider (official registry key or custom OpenAI-compatible)."""
    try:
        res = ai_provider_manager.create_provider(payload.model_dump())
        # Auto-discover immediately
        sync = ai_provider_manager.sync_provider_models(res["provider_id"])
        return {"status": "success", **res, "sync": {k: v for k, v in sync.items() if k != "models"}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))


@router.put("/api/ai/providers/{provider_id}", tags=["AI Providers"])
async def update_ai_provider(provider_id: str, payload: ProviderUpdatePayload):
    ai_provider_manager.update_provider(provider_id, payload.model_dump(exclude_none=True))
    return {"status": "success"}


@router.delete("/api/ai/providers/{provider_id}", tags=["AI Providers"])
async def delete_ai_provider(provider_id: str):
    if not ai_provider_manager.delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"status": "success"}


@router.post("/api/ai/providers/{provider_id}/sync", tags=["AI Providers"])
async def sync_ai_provider_models(provider_id: str):
    """Admin: refresh connection — re-discovers models with current credentials."""
    result = ai_provider_manager.sync_provider_models(provider_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result["detail"])
    return result


@router.get("/api/ai/models", tags=["AI Providers"])
async def list_ai_models(provider_id: Optional[str] = None):
    """Admin: all models with toggles; Client usage: pass ?enabled_only=true."""
    models = ai_provider_manager.list_models(provider_id)
    return {"status": "success", "models": models}


@router.get("/api/ai/brains", tags=["AI Providers"])
async def list_client_brains():
    """Client-facing: enabled+available models for the Brain selector."""
    return {"status": "success", "brains": ai_provider_manager.enabled_brain_options()}


@router.post("/api/ai/models/{model_id}/toggle", tags=["AI Providers"])
async def toggle_ai_model(model_id: str, payload: ModelTogglePayload):
    return ai_provider_manager.set_model_toggle(model_id, payload.enabled)


@router.post("/api/ai/providers/{provider_id}/models", tags=["AI Providers"])
async def add_manual_ai_model(provider_id: str, payload: ModelAddPayload):
    try:
        return ai_provider_manager.add_manual_model(provider_id, payload.model_id, payload.display_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=_safe_error(e))


@router.get("/api/debug/secrets-check", tags=["System"])
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


@router.get("/api/debug/llm-status", tags=["System"])
async def debug_llm_status(request: Request):
    """
    Admin-only diagnostic: performs a tiny live Gemini call and reports the
    exact result (model, HTTP status, error) so LLM issues can be diagnosed
    remotely. Never exposes any part of the API key.
    """
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request.cookies.get(SESSION_COOKIE_NAME) else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    import httpx as _httpx
    key = settings.GEMINI_API_KEY
    info: Dict[str, Any] = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "key_set": bool(key),
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
# AI Pause (Wave 9.8 - owner request): per-user master switch silencing
# the autonomous AI across all conversations and automations.
# --------------------------------------------------------------------
class AIPausePayload(BaseModel):
    paused: bool


def _session(request: Request):
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    if not session or not session.get("sub"):
        raise HTTPException(status_code=401, detail="غير مصرح - يرجى تسجيل الدخول")
    return session


@router.get("/api/ai/pause", tags=["AI Control"])
async def get_ai_pause(request: Request):
    """Returns the session user's AI pause state (user + global + effective)."""
    session = _session(request)
    from src.ai.pause import pause_status
    return {"status": "success", **pause_status(session["sub"], session.get("role") == "admin")}


@router.post("/api/ai/pause", tags=["AI Control"])
async def set_ai_pause(payload: AIPausePayload, request: Request):
    """
    Toggles the user's AI master switch. Admins also control the global
    legacy-operation switch (the env-connected pages have no per-lead owner).
    Effective semantics: global OR user flag silences ALL autonomous AI
    (messages + comment automations). Human Takeover stays per-conversation.
    """
    session = _session(request)
    from src.ai.pause import set_ai_pause as _set, pause_status
    res = _set(payload.paused, session["sub"], session.get("role") == "admin")
    return {"status": "success", **res, **pause_status(session["sub"], session.get("role") == "admin")}
