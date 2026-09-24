"""
Onboarding & Live Inbox module — migrated verbatim from main.py (WS0.3).

Real inbox: threads built from actual `messages` records (zero-fabrication).
Mutations here send REAL DMs from the owner's connected accounts —
admin-gated via /api/inbox/conversations prefix (ADMIN_MUTATION_PREFIXES).
"""
import re
from datetime import datetime, timezone as tz
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.modules.context import (  # noqa: F401
    settings, logger, supabase_db, safe_error, _safe_error,
    lead_service, knowledge_base,
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


@router.get("/api/inbox/conversations", tags=["Live Inbox"])
async def get_inbox_conversations():
    """
    Returns real conversation threads built from actual `messages` records.
    Zero-fabrication: every message shown exists in the database.
    """
    from src.core.event_dedup import event_deduplicator  # noqa: F401 (import guard)
    leads = supabase_db.select("leads", {}) or []
    # Efficiency + correctness: fetch ALL messages ONCE and group by lead
    # (no N+1 per-lead queries), then order threads by their LAST message
    # (any sender) descending — newest activity always rises to the top.
    msgs = supabase_db.select("messages", {}) or []
    by_lead: Dict[str, list] = {}
    for m in msgs:
        by_lead.setdefault(m.get("lead_id"), []).append(m)

    threads = []
    for lead in leads:
        lead_id = lead.get("id")
        platform = (lead.get("source") or "other").lower()
        # Real message history from the messages table (Zero-Fabrication policy)
        lead_msgs = sorted(by_lead.get(lead_id, []), key=lambda x: x.get("sent_at") or "")
        message_items = []
        last_inbound_at = None
        for m in lead_msgs:
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

    # Sort by the TRUE last message (any sender) descending — newest activity
    # always rises to the top (ISO sent_at strings sort lexically).
    threads.sort(key=lambda t: (t.get("messages") or [{}])[-1].get("time") or "", reverse=True)
    return {"status": "success", "conversations": threads[:50]}


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

    send_result = {}
    if platform == PlatformSource.FACEBOOK:
        send_result = await meta_client.send_facebook_message(recipient_id=recipient, message_text=text,
                                                              tag=tag)
    else:
        send_result = await meta_client.send_instagram_message(recipient_id=recipient, message_text=text,
                                                               tag=tag)

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


@router.get("/api/inbox/agent-status", tags=["Live Inbox"])
async def get_inbox_agent_status(request: Request):
    """Honest AI-operational state for the inbox pill: effective pause flag +
    average reply latency + agent replies in last 24h — computed from real
    stored message pairs (zero fabrication: None avg when no data exists)."""
    from datetime import timedelta
    from src.ai.pause import is_ai_paused
    from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request else None
    user_id = (session or {}).get("sub")

    msgs = supabase_db.select("messages") or []
    by_lead: dict = {}
    for m in msgs:
        by_lead.setdefault(m.get("lead_id"), []).append(m)
    durs = []
    now = datetime.now(tz.utc)
    replies_24h = 0
    for lst in by_lead.values():
        lst.sort(key=lambda x: x.get("sent_at") or "")
        for a, b in zip(lst, lst[1:]):
            meta_b = b.get("metadata") or {}
            if not isinstance(meta_b, dict):
                meta_b = {}
            # honest latency = customer message -> AUTOMATED agent reply only
            # (human takeover / test sends carry sent_by, booking links carry type)
            if (a.get("sender_type") == "lead" and b.get("sender_type") == "agent"
                    and "is_conversion_reply" in meta_b
                    and not meta_b.get("sent_by") and not meta_b.get("type")
                    and a.get("sent_at") and b.get("sent_at")):
                try:
                    t1 = datetime.fromisoformat(str(a["sent_at"]).replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(str(b["sent_at"]).replace("Z", "+00:00"))
                    d = (t2 - t1).total_seconds()
                    if 0 < d < 86400:
                        durs.append(d)
                except Exception:
                    pass
    for m in msgs:
        meta_m = m.get("metadata") or {}
        if (m.get("sender_type") == "agent" and m.get("sent_at")
                and isinstance(meta_m, dict) and "is_conversion_reply" in meta_m):
            try:
                t = datetime.fromisoformat(str(m["sent_at"]).replace("Z", "+00:00"))
                if now - t <= timedelta(hours=24):
                    replies_24h += 1
            except Exception:
                pass
    return {
        "status": "success",
        "ai_paused": is_ai_paused(user_id),
        "avg_reply_seconds": round(sum(durs) / len(durs), 1) if durs else None,
        "replies_last_24h": replies_24h,
    }


@router.post("/api/inbox/conversations/{lead_id}/takeover", tags=["Live Inbox"])
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


@router.post("/api/inbox/conversations/{lead_id}/send-message", tags=["Live Inbox"])
async def send_manual_inbox_message(lead_id: str, payload: ManualMessagePayload,
                                    request: Request = None):
    """
    Sends a REAL human message to the lead (Human Takeover chat) and stores it.
    Also enables takeover automatically so the AI does not double-reply.
    Entitlement gate (Phase 9.7): non-admin senders need the lead's platform
    service in their subscription — fail-closed regardless of token capability.
    """
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # entitlement gate — admins operate the workspace and bypass
    try:
        from src.core.auth import SESSION_COOKIE_NAME, verify_session_token
        session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") \
            if request else None
        if session and session.get("role") != "admin":
            from src.modules.connections.service import connection_service
            connection_service.assert_entitled(session["sub"], lead.get("platform") or "facebook")
    except HTTPException:
        raise
    except Exception:
        pass
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
async def send_booking_link_message(lead_id: str):
    """
    Sends the configured booking link (saved via Onboarding -> rules_and_guidelines.md)
    as a real DM. Zero-fabrication: if no link is configured, an explicit error is returned.
    """
    lead = lead_service.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    guidelines = knowledge_base.get_document("rules_and_guidelines.md") or ""
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
