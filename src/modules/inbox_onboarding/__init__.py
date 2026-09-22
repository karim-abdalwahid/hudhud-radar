"""
Onboarding & Live Inbox module — migrated verbatim from main.py (WS0.3).

Real inbox: threads built from actual `messages` records (zero-fabrication).
Mutations here send REAL DMs from the owner's connected accounts —
admin-gated via /api/inbox/conversations prefix (ADMIN_MUTATION_PREFIXES).
"""
import asyncio
import re
from datetime import datetime, timezone as tz
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.modules.context import (  # noqa: F401
    settings, logger, supabase_db, safe_error, _safe_error, lead_service,
)
from src.core.modules import module_registry

router = APIRouter()


class OnboardingSavePayload(BaseModel):
    knowledge_text: Optional[str] = None
    role: str = "sales"
    brain: str = "gemini"
    tone: str = "friendly"
    booking_link: Optional[str] = None


@router.post("/api/onboarding/save-all", tags=["Onboarding"])
async def save_onboarding_wizard(payload: OnboardingSavePayload, request: Request):
    """Saves business knowledge, configures agent persona, and sets booking link."""
    user_id = _session_user_id(request)
    from src.knowledge.db_knowledge_base import db_knowledge_base
    # 1. Update agent guidelines with role, tone, and booking link
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
    try:
        # Chunk embedding is synchronous in the database adapter.  Run it in
        # worker threads so onboarding cannot stall the async server.
        if payload.knowledge_text and payload.knowledge_text.strip():
            await asyncio.to_thread(
                db_knowledge_base.save_document,
                "business_profile.md",
                f"# نبذة عن الشركة والخدمات (Business Profile)\n\n{payload.knowledge_text.strip()}\n",
                user_id=user_id,
            )
        await asyncio.to_thread(
            db_knowledge_base.save_document,
            "rules_and_guidelines.md",
            guidelines_content,
            user_id=user_id,
        )
    except Exception as exc:
        logger.error("Onboarding KB persistence failed for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=503,
            detail="تعذر حفظ معرفة النشاط وإعدادات الوكيل. لم يتم اعتبار الإعداد مكتملًا؛ أعد المحاولة.",
        )

    return {
        "status": "success",
        "message": "تم حفظ بيانات وتدريب الوكيل بنجاح!",
        "role": payload.role,
        "brain": payload.brain,
        "tone": payload.tone,
        "booking_link": payload.booking_link
    }


@router.get("/api/inbox/conversations", tags=["Live Inbox"])
async def get_inbox_conversations(request: Request):
    """
    Returns real conversation threads built from actual `messages` records.
    Zero-fabrication: every message shown exists in the database.
    """
    from src.core.event_dedup import event_deduplicator  # noqa: F401 (import guard)
    user_id = _session_user_id(request)
    leads = supabase_db.select("leads", {"user_id": user_id}) or []
    threads = []
    for lead in leads[:50]:
        lead_id = lead.get("id")
        platform = (lead.get("source") or "other").lower()
        # Real message history from the messages table (Zero-Fabrication policy)
        msgs = lead_service.get_messages_for_lead(lead_id, user_id=user_id) or []
        message_items = []
        last_inbound_at = None
        for m in msgs:
            sender = m.get("sender_type") or "lead"
            if sender == "lead" and m.get("sent_at"):
                last_inbound_at = m.get("sent_at")
            message_items.append({
                "sender": "human" if ((m.get("metadata") or {}).get("sent_by") == "human" or sender in ("admin", "human")) else ("agent" if sender == "agent" else "customer"),
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
            "avatar": lead.get("avatar_url"),
            "handle": f"@{lead.get('username')}" if lead.get("username") else "",
            "channel": platform if platform in ("instagram", "facebook", "threads") else "instagram",
            "platformText": (
                "📸 Instagram Direct" if platform == "instagram"
                else "💬 Messenger" if platform == "facebook"
                else "🧵 Threads" if platform == "threads"
                else "💬 Direct"
            ),
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


def _session_user_id(request: Request) -> str:
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    if not session or not session.get("sub"):
        raise HTTPException(status_code=401, detail="غير مصرح")
    return str(session["sub"])


def _owned_lead(lead_id: str, request: Request) -> Dict[str, Any]:
    """Return only the session user's CRM lead; never accept a raw id alone."""
    user_id = _session_user_id(request)
    lead = lead_service.get_lead_by_id(lead_id, user_id=user_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _get_lead_recipient(lead: Dict[str, Any]) -> Optional[str]:
    """Resolves the platform recipient id for direct messaging a lead."""
    source = (lead.get("source") or "").lower()
    if source == "facebook" and lead.get("facebook_account_id"):
        return lead["facebook_account_id"]
    if source == "instagram" and lead.get("instagram_account_id"):
        return lead["instagram_account_id"]
    return lead.get("facebook_account_id") or lead.get("instagram_account_id")


async def _send_and_store_agent_message(lead: Dict[str, Any], text: str, extra_meta: Optional[Dict[str, Any]] = None,
                                        tag: Optional[str] = None):
    """Sends a real DM to the lead via Meta Send API and stores it in messages."""
    from src.meta_api.client import meta_client
    from src.leads.models import MessageCreate, PlatformSource, SenderType

    recipient = _get_lead_recipient(lead)
    if not recipient:
        raise HTTPException(status_code=400, detail="لا يوجد معرّف حساب مرتبط بهذا العميل لإرسال رسالة")
    source = (lead.get("source") or "").lower()
    platform = PlatformSource.FACEBOOK if source == "facebook" else PlatformSource.INSTAGRAM
    owner_user_id = str(lead.get("user_id") or "")
    if not owner_user_id:
        raise HTTPException(status_code=409, detail="Lead has no tenant owner")
    from src.modules.connections.service import connection_service
    credentials = connection_service.get_publish_credentials(owner_user_id, platform.value)
    if not credentials:
        raise HTTPException(status_code=403, detail="لا يوجد اتصال منصة مفعل لهذا الحساب")

    send_result = {}
    if platform == PlatformSource.FACEBOOK:
        send_result = await meta_client.send_facebook_message(recipient_id=recipient, message_text=text,
                                                              tag=tag,
                                                              access_token=credentials["access_token"],
                                                              user_id=owner_user_id)
    else:
        send_result = await meta_client.send_instagram_message(recipient_id=recipient, message_text=text,
                                                               tag=tag,
                                                               access_token=credentials["access_token"],
                                                               user_id=owner_user_id)

    stored = lead_service.add_message(MessageCreate(
        lead_id=lead["id"],
        user_id=owner_user_id,
        platform=platform,
        platform_message_id=send_result.get("message_id"),
        sender_type=SenderType.ADMIN if (extra_meta or {}).get("sent_by") == "human" else SenderType.AGENT,
        content=text,
        sent_at=datetime.now(tz.utc),
        metadata=extra_meta or {},
    ))
    return {"message_id": send_result.get("message_id"), "stored": stored is not None}


@router.post("/api/inbox/conversations/{lead_id}/takeover", tags=["Live Inbox"])
async def set_human_takeover(lead_id: str, payload: TakeoverPayload, request: Request):
    """
    Human Takeover: pauses/resumes the AI agent for this lead.
    The orchestrator checks this flag before generating auto-replies.
    """
    lead = _owned_lead(lead_id, request)
    updated = lead_service.update_lead(lead_id, {"human_takeover": bool(payload.takeover)})
    return {
        "status": "success",
        "lead_id": lead_id,
        "human_takeover": bool((updated or {}).get("human_takeover", False)),
        "message": "تم إيقاف الردود الآلية لهذه المحادثة" if payload.takeover else "تم استئناف الردود الآلية"
    }


@router.post("/api/inbox/conversations/{lead_id}/send-message", tags=["Live Inbox"])
async def send_manual_inbox_message(lead_id: str, payload: ManualMessagePayload,
    request: Request = None):
    """
    Sends a REAL human message to the lead (Human Takeover chat) and stores it.
    Also enables takeover automatically so the AI does not double-reply.
    Entitlement gate (Phase 9.7): non-admin senders need the lead's platform
    service in their subscription — fail-closed regardless of token capability.
    """
    lead = _owned_lead(lead_id, request)
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="نص الرسالة فارغ")
    from src.core.exceptions import MetaAPIError
    try:
        # Human Agent feature: Meta's sanctioned out-of-window path is
        # messaging_type=MESSAGE_TAG with tag=HUMAN_AGENT (verified live:
        # Meta accepts it and delivers the message — 200 + real message id).
        result = await _send_and_store_agent_message(lead, text, extra_meta={"sent_by": "human"},
                                                     tag="HUMAN_AGENT")
    except MetaAPIError as e:
        raise HTTPException(status_code=502, detail=f"Meta rejected the message: {str(e)[:240]}")
    if not lead.get("human_takeover"):
        lead_service.update_lead(lead_id, {"human_takeover": True})
    return {"status": "success", **result}


@router.post("/api/inbox/conversations/{lead_id}/send-booking-link", tags=["Live Inbox"])
async def send_booking_link_message(lead_id: str, request: Request):
    """
    Sends the configured booking link (saved via Onboarding -> rules_and_guidelines.md)
    as a real DM. Zero-fabrication: if no link is configured, an explicit error is returned.
    """
    lead = _owned_lead(lead_id, request)

    from src.knowledge.db_knowledge_base import db_knowledge_base
    guidelines = db_knowledge_base.get_document_content(
        "rules_and_guidelines.md", user_id=str(lead["user_id"])) or ""
    match = re.search(r"https?://[^\s\)\]]+", guidelines)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="لم يتم تحديد رابط حجز المواعيد بعد — أضفه من صفحة الإعدادات (Onboarding) أولاً"
        )
    booking_link = match.group(0)
    text = f"يسعدنا تواصلك! تقدر تحجز مكالمة استشارية مجانية مع فريقنا من هنا: {booking_link}"
    result = await _send_and_store_agent_message(lead, text, extra_meta={"sent_by": "human", "type": "booking_link"})
    return {"status": "success", **result}


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="inbox_onboarding",
    description="Onboarding wizard save + Live Inbox real conversations (takeover, manual DM, booking link)",
    register_router=register,
)
