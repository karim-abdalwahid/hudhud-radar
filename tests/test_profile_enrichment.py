"""
Tests: Real customer profile enrichment (name + avatar) from Meta Graph API.
Verifies webhook leads get real names/photos instead of generic 'Lead'.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.identity.extractor import ProfileDataExtractor
from src.leads.models import PlatformSource


def test_facebook_profile_pic_maps_to_avatar_url():
    """Messenger Profile API payload (first_name/last_name/profile_pic) → lead with real name + avatar."""
    raw = {
        "id": "psid_123",
        "first_name": "Karim",
        "last_name": "Abdalwahid",
        "profile_pic": "https://platform-lookaside.fbsbx.com/pic.jpg",
    }
    lead = ProfileDataExtractor.extract_from_facebook(raw)

    assert lead.full_name == "Karim Abdalwahid"
    assert lead.avatar_url == "https://platform-lookaside.fbsbx.com/pic.jpg"
    assert lead.facebook_account_id == "psid_123"


def test_instagram_profile_pic_maps_to_avatar_url():
    """Instagram profile payload → avatar_url mapped (zero-fabrication otherwise)."""
    raw = {
        "id": "ig_sid_999",
        "username": "customer_ig",
        "name": "Sara Ali",
        "profile_pic": "https://example.com/sara.jpg",
    }
    lead = ProfileDataExtractor.extract_from_instagram(raw)

    assert lead.full_name == "Sara Ali"
    assert lead.username == "customer_ig"
    assert lead.avatar_url == "https://example.com/sara.jpg"


def test_missing_profile_pic_stays_none():
    """Zero-fabrication: no profile_pic in payload → avatar_url must be None."""
    lead = ProfileDataExtractor.extract_from_facebook({"id": "psid_777"})
    assert lead.avatar_url is None


@pytest.mark.asyncio
async def test_orchestrator_fetches_real_profile_before_extraction(monkeypatch):
    """
    Incoming webhook must enrich the sender payload via MetaGraphClient.get_profile()
    so the stored lead carries the customer's REAL name and photo.
    """
    from src.agent.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()

    fake_profile = {
        "id": "psid_real",
        "first_name": "Mohamed",
        "last_name": "Hassan",
        "profile_pic": "https://platform-lookaside.fbsbx.com/mohamed.jpg",
    }

    # monkeypatch (auto-restored) — direct assignment on singletons leaks mocks
    monkeypatch.setattr(orch.client, "get_profile", AsyncMock(return_value=fake_profile))
    monkeypatch.setattr(orch.resolver, "resolve_and_save_lead", MagicMock(
        return_value=({"id": "lead_1", "human_takeover": True}, True, None)
    ))
    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.owner_for_account",
        lambda *_: "owner_1",
    )

    event = {
        "platform": PlatformSource.FACEBOOK,
        "sender_id": "psid_real",
        "recipient_id": "page_1",
        "message_id": "mid_x",
        "text": "hello",
        "raw_event": {},
    }
    result = await orch.process_incoming_message_event(event)

    # get_profile was called with the sender PSID and Messenger fields
    orch.client.get_profile.assert_awaited_once()
    args, kwargs = orch.client.get_profile.await_args
    assert args[0] == "psid_real"
    assert "first_name" in kwargs.get("fields", args[1] if len(args) > 1 else "")

    # The lead stored carries the real name + avatar (not a fabricated placeholder)
    saved_lead = orch.resolver.resolve_and_save_lead.call_args[0][0]
    assert saved_lead.full_name == "Mohamed Hassan"
    assert saved_lead.avatar_url == "https://platform-lookaside.fbsbx.com/mohamed.jpg"
    assert result["human_takeover"] is True


@pytest.mark.asyncio
async def test_orchestrator_survives_profile_fetch_failure(monkeypatch):
    """If the Graph API profile call fails, processing must continue (zero-assumption fallback)."""
    from src.agent.orchestrator import AgentOrchestrator

    orch = AgentOrchestrator()
    monkeypatch.setattr(orch.client, "get_profile",
                        AsyncMock(side_effect=Exception("network down")))
    monkeypatch.setattr(orch.resolver, "resolve_and_save_lead", MagicMock(
        return_value=({"id": "lead_2", "human_takeover": True}, True, None)
    ))
    monkeypatch.setattr(
        "src.modules.connections.service.connection_service.owner_for_account",
        lambda *_: "owner_1",
    )

    event = {
        "platform": PlatformSource.FACEBOOK,
        "sender_id": "psid_offline",
        "recipient_id": "page_1",
        "message_id": "mid_y",
        "text": "hi",
        "raw_event": {},
    }
    result = await orch.process_incoming_message_event(event)

    saved_lead = orch.resolver.resolve_and_save_lead.call_args[0][0]
    assert saved_lead.full_name is None      # nothing fabricated
    assert saved_lead.avatar_url is None
    assert result["lead_id"] == "lead_2"


def test_inbox_thread_includes_avatar():
    """/api/inbox/conversations must expose the lead's avatar for UI rendering."""
    from unittest.mock import patch
    from src.core.supabase_client import InMemoryDatabase
    import src.modules.inbox_onboarding as inbox_mod

    db = InMemoryDatabase()
    lead = db.insert("leads", {
        "source": "facebook",
        "full_name": "Mohamed Hassan",
        "avatar_url": "https://platform-lookaside.fbsbx.com/mohamed.jpg",
        "facebook_account_id": "psid_real",
    })
    db.insert("messages", {
        "lead_id": lead["id"],
        "sender_type": "lead",
        "content": "hello",
        "sent_at": "2026-09-10T22:00:00+00:00",
    })

    with patch.object(inbox_mod, "supabase_db", db), \
         patch.object(inbox_mod.lead_service, "get_messages_for_lead",
                      return_value=db.select("messages", {"lead_id": lead["id"]})):
        import asyncio
        resp = asyncio.run(inbox_mod.get_inbox_conversations())

    convs = resp["conversations"]
    assert len(convs) == 1
    assert convs[0]["name"] == "Mohamed Hassan"
    assert convs[0]["avatar"] == "https://platform-lookaside.fbsbx.com/mohamed.jpg"
