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

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook JSON body")
    if not isinstance(payload, dict):
        return {"status": "ignored", "reason": "non-object payload"}
    events = webhook_handler.parse_messaging_events(payload)
    comment_events = webhook_handler.parse_comment_events(payload)

    from src.core.event_dedup import event_deduplicator
    from src.modules.connections.service import connection_service

    queued = 0
    for ev in events:
        if not ev.get("is_echo"):
            platform = getattr(ev.get("platform"), "value", ev.get("platform"))
            owner_user_id = connection_service.owner_for_account(platform, ev.get("recipient_id"))
            if not owner_user_id:
                logger.warning("Message webhook ignored before queue: unmapped recipient account")
                continue
            # Idempotency: skip events Meta already delivered (prevents duplicate AI replies)
            if not event_deduplicator.claim(
                f"msg:{ev.get('message_id') or ev.get('sender_id')}:{ev.get('timestamp', '')}",
                "message", scope=owner_user_id):
                continue
            background_tasks.add_task(agent_orchestrator.process_incoming_message_event, ev)
            queued += 1

    for cev in comment_events:
        platform = getattr(cev.get("platform"), "value", cev.get("platform"))
        owner_user_id = connection_service.owner_for_account(platform, cev.get("account_id"))
        if not owner_user_id:
            logger.warning("Comment webhook ignored before queue: unmapped recipient account")
            continue
        if not event_deduplicator.claim(f"comment:{cev.get('comment_id')}", "comment", scope=owner_user_id):
            continue
        # Bridge: every comment becomes (or appends to) a CRM lead — independent
        # of automations so lead capture never depends on workflow config.
        from src.leads.comment_bridge import capture_comment_lead
        background_tasks.add_task(capture_comment_lead, cev)
        background_tasks.add_task(automations_service.process_comment_event, cev)
        queued += 1

    return {"status": "received", "events_queued": queued}


# --------------------------------------------------------------------
# 3. Threads Webhooks (Wave 9.8) — replies → CRM bridge receiver
#    Subscription is configured in the Meta dashboard (Threads → webhooks);
#    this endpoint verifies the handshake + HMAC signature (fail-closed,
#    same policy as the Meta webhook) and captures real replies as leads.
# --------------------------------------------------------------------
@router.get("/api/webhook/threads", tags=["Webhooks"])
async def verify_threads_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """Meta dashboard subscription handshake for Threads webhooks."""
    challenge = webhook_handler.verify_subscription(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/api/webhook/threads", tags=["Webhooks"])
async def receive_threads_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives Threads reply events, verifies the HMAC signature, and
    captures each real reply as (or into) a CRM lead. Self-replies skipped."""
    import hmac as _hmac
    import hashlib as _hashlib

    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not settings.THREADS_APP_SECRET:
        logger.error("THREADS_APP_SECRET not configured — Threads webhook rejected (fail-closed).")
        raise HTTPException(status_code=401, detail="Threads webhook not configured")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")

    expected = _hmac.new(settings.THREADS_APP_SECRET.encode("utf-8"),
                         raw_body, _hashlib.sha256).hexdigest()
    parts = signature.split("sha256=")
    if len(parts) != 2 or not _hmac.compare_digest(parts[1], expected):
        logger.error("Threads webhook HMAC verification failed.")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed webhook JSON body")
    if not isinstance(payload, dict):
        return {"status": "ignored", "reason": "non-object payload"}
    if payload.get("object") != "threads":
        return {"status": "ignored", "reason": "unknown object"}

    from src.meta_api.extended_api import threads_leads_sync
    from src.core.event_dedup import event_deduplicator
    from src.modules.connections.service import connection_service

    queued = 0
    for entry in (payload.get("entry") if isinstance(payload.get("entry"), list) else []):
        if not isinstance(entry, dict):
            continue
        entry_user_id = entry.get("id")
        changes = entry.get("changes")
        for change in (changes if isinstance(changes, list) else []):
            if not isinstance(change, dict):
                continue
            val = change.get("value") or {}
            if not isinstance(val, dict):
                continue
            reply_id = val.get("id")
            if not reply_id:
                continue
            owner_user_id = connection_service.owner_for_account("threads", entry_user_id)
            if not owner_user_id:
                logger.warning("Threads webhook ignored before queue: unmapped recipient account")
                continue
            if not event_deduplicator.claim(f"threads_reply:{reply_id}", "threads_reply", scope=owner_user_id):
                continue
            reply = {
                "id": reply_id,
                "text": val.get("text") or "",
                "timestamp": val.get("timestamp"),
                "username": (val.get("from") or {}).get("username") or val.get("username"),
                "from_user": {"id": (val.get("from") or {}).get("id")},
            }
            background_tasks.add_task(
                _capture_threads_reply_safe, reply, entry_user_id)
            queued += 1

    return {"status": "received", "events_queued": queued}


async def _capture_threads_reply_safe(reply: dict, entry_user_id: Optional[str]):
    """Background wrapper: resolves the owning connection's token and captures."""
    try:
        from src.meta_api.extended_api import threads_leads_sync
        from src.modules.connections.service import connection_service
        owner_user_id = connection_service.owner_for_account("threads", entry_user_id)
        if not owner_user_id:
            logger.warning("Threads webhook: no unique owner — event skipped.")
            return
        token = connection_service.get_active_token_for_account(
            owner_user_id, "threads", entry_user_id)
        if not token:
            logger.warning("Threads webhook: no entitled account token — event skipped.")
            return
        await threads_leads_sync.capture_thread_reply(
            reply, token=token, user_id=owner_user_id)
    except Exception as e:
        logger.error(f"Threads webhook capture failed: {e}")
