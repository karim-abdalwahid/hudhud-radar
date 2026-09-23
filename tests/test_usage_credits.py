"""Tests: AI usage metering & the credit gate (completes Phase 9.4/9.5).

Covers, in order:
  1. UsageService itself — balance reads, debits, grants, fail-closed checks.
  2. ConversationEngine's new `used_ai` signal (billable vs free replies).
  3. The orchestrator wiring: blocks + notifies when exhausted, bills exactly
     one credit for a real AI reply, bills nothing for a fallback reply.
  4. The Content Studio route wiring: 402 when exhausted, bills only a real
     Gemini generation.
  5. Grant wiring: trial start tops up credits (through the real service
     call chain); subscription activation is checked at the source level,
     matching this file's established convention for the payment webhook
     (see test_billing.py — no test exercises the raw HTTP webhook path).
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.test_billing import fake_billing  # noqa: F401 — reused fixture, see section 5 below
from src.modules.billing.usage import (
    UsageService,
    KIND_AI_REPLY,
    KIND_AI_GENERATE,
    CREDITS_PER_PLATFORM,
    TRIAL_MINIMUM_CREDITS,
)


# ─────────────────────────────────────────────────────────────────────────
# 1. UsageService — isolated fake DB, no FastAPI/auth machinery needed
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def fake_usage_db():
    """A minimal users/usage_events/notifications store, shaped like
    supabase_client's real select/insert/update contract."""
    users = {}
    events = []
    notifications = []

    class FakeDB:
        def select(self, table, filters=None):
            f = filters or {}
            if table == "users":
                rows = list(users.values())
                if f.get("id"):
                    rows = [r for r in rows if r["id"] == f["id"]]
                return rows
            if table == "usage_events":
                rows = list(events)
                if f.get("user_id"):
                    rows = [r for r in rows if r["user_id"] == f["user_id"]]
                return rows
            if table == "notifications":
                rows = list(notifications)
                if f.get("user_id"):
                    rows = [r for r in rows if r["user_id"] == f["user_id"]]
                return rows
            return []

        def insert(self, table, data):
            now = datetime.now(timezone.utc).isoformat()
            if table == "usage_events":
                row = {"id": len(events) + 1, "created_at": now, **data}
                events.append(row)
                return row
            if table == "notifications":
                row = {"id": f"n{len(notifications)+1}", "created_at": now, **data}
                notifications.append(row)
                return row
            return data

        def update(self, table, rid, data):
            if table == "users" and rid in users:
                users[rid].update(data)
                return users[rid]
            return None

    return FakeDB(), users, events, notifications


@pytest.fixture
def usage(fake_usage_db, monkeypatch):
    db, users, events, notifications = fake_usage_db
    # Patch METHODS on the real shared singleton (not the module-local name):
    # notify_if_exhausted calls notifications/service.py, which holds its own
    # `from ... import supabase_db` binding to the SAME object. Swapping
    # src.modules.billing.usage.supabase_db wholesale would only redirect
    # calls made from within usage.py itself.
    from src.core.supabase_client import supabase_db as real_db
    monkeypatch.setattr(real_db, "select", db.select)
    monkeypatch.setattr(real_db, "insert", db.insert)
    monkeypatch.setattr(real_db, "update", db.update)
    return UsageService(), users, events, notifications


def test_has_credits_true_when_balance_sufficient(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 5}
    assert svc.has_credits("u1", amount=1) is True
    assert svc.has_credits("u1", amount=5) is True


def test_has_credits_false_when_balance_insufficient(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 0}
    assert svc.has_credits("u1") is False


def test_has_credits_false_for_unknown_or_missing_user(usage):
    svc, _, _, _ = usage
    assert svc.has_credits("ghost") is False
    assert svc.has_credits("") is False
    assert svc.has_credits(None) is False


def test_has_credits_fails_closed_on_lookup_error(usage, monkeypatch):
    svc, _, _, _ = usage

    def boom(*_a, **_k):
        raise RuntimeError("db unreachable")

    monkeypatch.setattr("src.core.supabase_client.supabase_db.select", boom)
    assert svc.has_credits("anyone") is False  # never fail open on a billing gate


def test_record_usage_inserts_event_and_debits_balance(usage):
    svc, users, events, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 10}
    svc.record_usage("u1", KIND_AI_REPLY, meta={"lead_id": "L1"})
    assert users["u1"]["ai_credits"] == 9
    assert len(events) == 1
    assert events[0]["kind"] == KIND_AI_REPLY
    assert events[0]["amount"] == 1
    assert events[0]["meta"] == {"lead_id": "L1"}


def test_record_usage_never_lets_balance_go_negative(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 0}
    svc.record_usage("u1", KIND_AI_REPLY)  # already exhausted; gate should have blocked
    assert users["u1"]["ai_credits"] == 0  # floored, not -1


def test_record_usage_never_raises_when_db_is_broken(usage, monkeypatch):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 5}

    def boom(*_a, **_k):
        raise RuntimeError("network blip")

    monkeypatch.setattr("src.core.supabase_client.supabase_db.insert", boom)
    monkeypatch.setattr("src.core.supabase_client.supabase_db.update", boom)
    svc.record_usage("u1", KIND_AI_REPLY)  # must not raise — the reply already went out


def test_ensure_minimum_credits_tops_up_a_lower_balance(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 10}
    svc.ensure_minimum_credits("u1", 100)
    assert users["u1"]["ai_credits"] == 100


def test_ensure_minimum_credits_never_lowers_a_higher_balance(usage):
    """Idempotent by construction — a redelivered webhook or a prior admin
    bonus grant must never be clawed back."""
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 900}
    svc.ensure_minimum_credits("u1", 100)
    assert users["u1"]["ai_credits"] == 900


def test_ensure_minimum_credits_is_safe_to_call_repeatedly(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 0}
    svc.ensure_minimum_credits("u1", TRIAL_MINIMUM_CREDITS)
    svc.ensure_minimum_credits("u1", TRIAL_MINIMUM_CREDITS)
    svc.ensure_minimum_credits("u1", TRIAL_MINIMUM_CREDITS)
    assert users["u1"]["ai_credits"] == TRIAL_MINIMUM_CREDITS  # not 300


def test_grant_platform_credits_scales_with_platform_count(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 0}
    svc.grant_platform_credits("u1", platform_count=3)
    assert users["u1"]["ai_credits"] == CREDITS_PER_PLATFORM * 3


def test_grant_platform_credits_floors_at_one_platform(usage):
    svc, users, _, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 0}
    svc.grant_platform_credits("u1", platform_count=0)
    assert users["u1"]["ai_credits"] == CREDITS_PER_PLATFORM


def test_summary_reports_balance_and_30_day_window(usage):
    svc, users, events, _ = usage
    users["u1"] = {"id": "u1", "ai_credits": 42}
    events.append({"user_id": "u1", "kind": KIND_AI_REPLY, "amount": 3,
                    "created_at": "2026-09-20T00:00:00+00:00"})  # inside window
    events.append({"user_id": "u1", "kind": KIND_AI_GENERATE, "amount": 2,
                    "created_at": "2026-09-21T00:00:00+00:00"})  # inside window
    events.append({"user_id": "u1", "kind": KIND_AI_REPLY, "amount": 99,
                    "created_at": "2025-01-01T00:00:00+00:00"})  # outside window

    out = svc.summary("u1", days=30)
    assert out["ai_credits"] == 42
    assert out["used_last_30d"] == 5
    assert out["by_kind"] == {KIND_AI_REPLY: 3, KIND_AI_GENERATE: 2}


def test_notify_if_exhausted_creates_one_notification(usage):
    svc, _, _, notifications = usage
    svc.notify_if_exhausted("u1")
    assert len(notifications) == 1
    assert notifications[0]["meta"]["job"] == "credits_exhausted"


def test_notify_if_exhausted_is_throttled_within_six_hours(usage):
    svc, _, _, notifications = usage
    svc.notify_if_exhausted("u1")
    svc.notify_if_exhausted("u1")
    svc.notify_if_exhausted("u1")
    assert len(notifications) == 1  # a burst of blocked messages must not spam the bell


def test_notify_if_exhausted_never_raises(usage, monkeypatch):
    svc, _, _, _ = usage

    def boom(*_a, **_k):
        raise RuntimeError("notifications table down")

    monkeypatch.setattr("src.core.supabase_client.supabase_db.select", boom)
    svc.notify_if_exhausted("u1")  # must not raise


# ─────────────────────────────────────────────────────────────────────────
# 2. ConversationEngine — the used_ai (billable) signal
# ─────────────────────────────────────────────────────────────────────────
class _StubKB:
    def get_sales_closing_context(self, user_id=None):
        return "SCRIPT"

    def search_relevant_chunks(self, query, top_k=3, user_id=None):
        return "CONTEXT"


@pytest.mark.asyncio
async def test_used_ai_true_only_on_a_real_gemini_reply(monkeypatch):
    from src.agent.conversation_engine import ConversationEngine
    from src.config import settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "real-test-key")
    engine = ConversationEngine(kb=_StubKB())
    monkeypatch.setattr(engine, "_call_gemini_api", AsyncMock(return_value="مرحباً، إزاي أقدر أساعدك؟"))

    reply, converted, used_ai = await engine.generate_response({"user_id": "u1"}, "أهلاً")
    assert used_ai is True
    assert converted is False
    assert reply == "مرحباً، إزاي أقدر أساعدك؟"


@pytest.mark.asyncio
async def test_used_ai_false_when_gemini_raises_and_falls_back(monkeypatch):
    from src.agent.conversation_engine import ConversationEngine
    from src.config import settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "real-test-key")
    engine = ConversationEngine(kb=_StubKB())
    monkeypatch.setattr(engine, "_call_gemini_api", AsyncMock(side_effect=RuntimeError("503")))

    reply, converted, used_ai = await engine.generate_response({"user_id": "u1"}, "بكام السعر؟")
    assert used_ai is False  # the outage must not be billed
    assert converted is False


@pytest.mark.asyncio
async def test_used_ai_false_when_gemini_not_configured(monkeypatch):
    from src.agent.conversation_engine import ConversationEngine
    from src.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    engine = ConversationEngine(kb=_StubKB())
    reply, converted, used_ai = await engine.generate_response({"user_id": "u1"}, "ابدأ")
    assert used_ai is False


@pytest.mark.asyncio
async def test_used_ai_false_for_the_canned_conversion_reply(monkeypatch):
    from src.agent.conversation_engine import ConversationEngine
    from src.config import settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "real-test-key")
    engine = ConversationEngine(kb=_StubKB())
    spy = AsyncMock(return_value="should never be called")
    monkeypatch.setattr(engine, "_call_gemini_api", spy)

    reply, converted, used_ai = await engine.generate_response(
        {"user_id": "u1"}, "تمام رقمي 01012345678"
    )
    assert converted is True
    assert used_ai is False
    spy.assert_not_called()  # contact-info branch short-circuits before any LLM call


# ─────────────────────────────────────────────────────────────────────────
# 3. Orchestrator wiring — gate + billing, mirroring test_ai_pause.py's
#    established structure for this exact function.
# ─────────────────────────────────────────────────────────────────────────
def _wire_common_orchestrator_mocks(orch, monkeypatch, lead_row):
    monkeypatch.setattr(orch.client, "get_profile", AsyncMock(return_value={}))
    monkeypatch.setattr(orch.resolver, "resolve_and_save_lead",
                        MagicMock(return_value=(lead_row, True, None)))
    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.owner_for_account",
        lambda *_: "owner_1",
    )
    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.get_active_token_for_account",
        lambda *_: "tenant-page-token",
    )
    monkeypatch.setattr("src.ai.pause.is_ai_paused", lambda uid: False)
    stored = []
    monkeypatch.setattr(orch.lead_svc, "add_message",
                        MagicMock(side_effect=lambda m: stored.append(m)))
    monkeypatch.setattr(orch.lead_svc, "get_messages_for_lead", MagicMock(return_value=[]))
    return stored


def _event():
    from src.leads.models import PlatformSource
    return {"platform": PlatformSource.FACEBOOK, "sender_id": "psid_1",
            "recipient_id": "page_1", "message_id": "m_credits", "text": "hi", "raw_event": {}}


@pytest.mark.asyncio
async def test_orchestrator_skips_reply_and_notifies_when_credits_exhausted(monkeypatch):
    from src.agent.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    lead_row = {"id": "lead_credits", "human_takeover": False, "user_id": "owner_1",
                "facebook_account_id": "psid_1"}
    stored = _wire_common_orchestrator_mocks(orch, monkeypatch, lead_row)

    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: False)
    notified = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.notify_if_exhausted",
                        lambda uid: notified.append(uid))
    billed = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.record_usage",
                        lambda *a, **k: billed.append((a, k)))

    result = await orch.process_incoming_message_event(_event())

    assert result.get("credits_exhausted") is True
    assert result.get("reply_sent") is None
    assert len(stored) == 1                     # inbound still stored for manual reply
    assert notified == ["owner_1"]
    assert billed == []                          # nothing to bill — nothing was generated


@pytest.mark.asyncio
async def test_orchestrator_bills_one_credit_for_a_real_ai_reply(monkeypatch):
    """The happy path: credits available, Gemini succeeds, reply goes out,
    exactly one ai_reply credit is billed."""
    from src.agent.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    lead_row = {"id": "lead_happy", "human_takeover": False, "user_id": "owner_1",
                "facebook_account_id": "psid_1"}
    stored = _wire_common_orchestrator_mocks(orch, monkeypatch, lead_row)
    monkeypatch.setattr(orch.client, "send_facebook_message",
                        AsyncMock(return_value={"message_id": "wamid_1"}))

    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: True)
    billed = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.record_usage",
                        lambda *a, **k: billed.append((a, k)))
    monkeypatch.setattr(orch.engine, "generate_response",
                        AsyncMock(return_value=("رد ذكي حقيقي", False, True)))

    result = await orch.process_incoming_message_event(_event())

    assert result["reply_sent"] == "رد ذكي حقيقي"
    assert "credits_exhausted" not in result
    assert len(billed) == 1
    args, kwargs = billed[0]
    assert args[0] == "owner_1"
    from src.modules.billing.usage import KIND_AI_REPLY
    assert args[1] == KIND_AI_REPLY
    assert kwargs["meta"]["lead_id"] == "lead_happy"


@pytest.mark.asyncio
async def test_orchestrator_does_not_bill_a_fallback_reply(monkeypatch):
    """Credits ARE available, but the engine used the free heuristic path
    (used_ai=False) — must not be billed even though a reply still went out."""
    from src.agent.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    lead_row = {"id": "lead_fb", "human_takeover": False, "user_id": "owner_1",
                "facebook_account_id": "psid_1"}
    stored = _wire_common_orchestrator_mocks(orch, monkeypatch, lead_row)
    monkeypatch.setattr(orch.client, "send_facebook_message",
                        AsyncMock(return_value={"message_id": "wamid_2"}))

    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: True)
    billed = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.record_usage",
                        lambda *a, **k: billed.append((a, k)))
    monkeypatch.setattr(orch.engine, "generate_response",
                        AsyncMock(return_value=("رد احتياطي جاهز", False, False)))

    result = await orch.process_incoming_message_event(_event())

    assert result["reply_sent"] == "رد احتياطي جاهز"
    assert billed == []


# ─────────────────────────────────────────────────────────────────────────
# 4. Content Studio route — 402 gate + bill-only-real-Gemini
# ─────────────────────────────────────────────────────────────────────────
def test_content_generate_returns_402_when_out_of_credits(client: "TestClient", monkeypatch):
    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: False)
    res = client.post("/api/content/generate", json={
        "topic": "test topic", "post_type": "post", "platform": "both", "cta_keyword": "ابدأ",
    })
    assert res.status_code == 402


def test_content_generate_bills_real_gemini_output(client: "TestClient", monkeypatch):
    from src.content_studio.models import ContentGenerationResponse, PostType, ContentPlatform

    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: True)
    billed = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.record_usage",
                        lambda *a, **k: billed.append((a, k)))

    async def fake_generate(req, user_id):
        return ContentGenerationResponse(
            topic=req.topic, post_type=req.post_type, platform=req.platform,
            generated_text="نص حقيقي من Gemini", cta="ابدأ", model_used="Gemini (test-model)",
        )
    monkeypatch.setattr("src.modules.content.routes.content_engine.generate_content", fake_generate)

    res = client.post("/api/content/generate", json={
        "topic": "test topic", "post_type": "post", "platform": "both", "cta_keyword": "ابدأ",
    })
    assert res.status_code == 200
    assert len(billed) == 1
    from src.modules.billing.usage import KIND_AI_GENERATE
    assert billed[0][0][1] == KIND_AI_GENERATE


def test_content_generate_does_not_bill_the_offline_fallback(client: "TestClient", monkeypatch):
    from src.content_studio.models import ContentGenerationResponse

    monkeypatch.setattr("src.modules.billing.usage.usage_service.has_credits", lambda *_a, **_k: True)
    billed = []
    monkeypatch.setattr("src.modules.billing.usage.usage_service.record_usage",
                        lambda *a, **k: billed.append((a, k)))

    async def fake_generate(req, user_id):
        return ContentGenerationResponse(
            topic=req.topic, post_type=req.post_type, platform=req.platform,
            generated_text="قالب احتياطي", cta="ابدأ",
            model_used="HudhudRadar Post Copywriter Pro",
        )
    monkeypatch.setattr("src.modules.content.routes.content_engine.generate_content", fake_generate)

    res = client.post("/api/content/generate", json={
        "topic": "test topic", "post_type": "post", "platform": "both", "cta_keyword": "ابدأ",
    })
    assert res.status_code == 200
    assert billed == []


# ─────────────────────────────────────────────────────────────────────────
# 5. Grant wiring
# ─────────────────────────────────────────────────────────────────────────
def test_trial_start_tops_up_credits_through_the_real_call_chain(fake_billing):
    """End-to-end through EntitlementService.start_trial itself (not a
    reimplementation) — proves the grant is actually wired in, not just that
    UsageService.ensure_minimum_credits works in isolation (already covered
    above)."""
    from src.modules.billing.services import EntitlementService
    from src.modules.billing.usage import usage_service, TRIAL_MINIMUM_CREDITS

    user = fake_billing["register_and_track"]("trial-credits@hudhud.test")
    fake_billing["users"][user["id"]]["ai_credits"] = 0

    svc = EntitlementService()
    assert svc.start_trial(user["id"]) is True
    assert usage_service.balance(user["id"]) == TRIAL_MINIMUM_CREDITS


def test_trial_start_does_not_lower_an_existing_higher_balance(fake_billing):
    from src.modules.billing.services import EntitlementService
    from src.modules.billing.usage import usage_service

    user = fake_billing["register_and_track"]("trial-credits-2@hudhud.test")
    fake_billing["users"][user["id"]]["ai_credits"] = 900

    EntitlementService().start_trial(user["id"])
    assert usage_service.balance(user["id"]) == 900


def test_subscription_activation_webhook_grants_platform_credits_at_source():
    """No test in this file exercises the raw signed webhook HTTP path (see
    the module docstring in test_billing.py) — this matches that convention
    with a source-level check that the paid-activation branch actually calls
    the grant, in the right (non-trial) branch, scaled by platform count."""
    import inspect
    import src.modules.billing as billing_module

    source = inspect.getsource(billing_module)
    paid_branch = source.split('if is_trial and upstream_status not in')[1]
    paid_branch = paid_branch.split("elif kind ==")[0]  # stop before the cancel branch
    assert "usage_service.grant_platform_credits" in paid_branch
    assert "len(platforms)" in paid_branch
