"""
Meta Webhooks (Verification & Intake) — migrated verbatim from main.py (WS0.3).

Owned by module 'webhooks'. Registered via src/modules/webhooks/__init__.py.
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
# 2. Meta Webhooks (Verification & Intake)
# Supports multiple common paths: /webhooks/meta, /api/webhook/meta, /api/webhook/instagram
# --------------------------------------------------------------------
@router.get("/webhooks/meta", tags=["Webhooks"])
@router.get("/api/webhook/meta", tags=["Webhooks"])
@router.get("/api/webhook/instagram", tags=["Webhooks"])
@router.get("/api/webhooks/meta", tags=["Webhooks"])
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


@router.post("/webhooks/meta", tags=["Webhooks"])
@router.post("/api/webhook/meta", tags=["Webhooks"])
@router.post("/api/webhook/instagram", tags=["Webhooks"])
@router.post("/api/webhooks/meta", tags=["Webhooks"])
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
        # Bridge: every comment becomes (or appends to) a CRM lead — independent
        # of automations so lead capture never depends on workflow config.
        from src.leads.comment_bridge import capture_comment_lead
        background_tasks.add_task(capture_comment_lead, cev)
        background_tasks.add_task(automations_service.process_comment_event, cev)
        queued += 1

    return {"status": "received", "events_queued": queued}
