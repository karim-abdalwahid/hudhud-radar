"""
System Health & Info — migrated verbatim from main.py (WS0.3).

Owned by module 'health'. Registered via src/modules/health/__init__.py.
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
# 1. System Health & Info
# --------------------------------------------------------------------
@router.get("/health", tags=["System"])
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
