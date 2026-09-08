"""
Analytics & Performance Reports — migrated verbatim from main.py (WS0.3).

Owned by module 'analytics'. Registered via src/modules/analytics/__init__.py.
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
# 5. Analytics & Performance Reports
# --------------------------------------------------------------------
@router.get("/api/analytics/summary", tags=["Analytics"])
async def get_analytics_summary():
    """Returns granular analytics on operations, success/failure rate, and root causes."""
    return {
        "operations": statistics_engine.get_operations_summary(),
        "leads_and_conversions": statistics_engine.get_lead_conversion_metrics()
    }


@router.get("/api/reports/page-performance", tags=["Reports"])
async def get_page_performance_report():
    """Returns rendered page performance report in Markdown."""
    md = report_generator.generate_page_performance_report_md()
    return {"report_markdown": md}


@router.get("/api/reports/activity-execution", tags=["Reports"])
async def get_activity_execution_report():
    """Returns rendered activity execution and failure root-cause report in Markdown."""
    md = report_generator.generate_activity_execution_report_md()
    return {"report_markdown": md}
