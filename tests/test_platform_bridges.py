"""
Tests: Platform Bridges — Instagram comments & Threads replies → CRM leads.
Every captured lead/message carries ONLY data returned by the webhook/API
(zero-fabrication). Deterministic identity matching per platform.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.supabase_client import InMemoryDatabase
from src.identity.resolver import IdentityResolver
from src.identity.extractor import ProfileDataExtractor
from src.leads.models import PlatformSource, LeadCreate
from src.leads.comment_bridge import capture_comment_lead


@pytest.fixture
def mock_db():
    return InMemoryDatabase()


@pytest.fixture
def bridged_db(monkeypatch, mock_db):
    """Bridge + resolver + lead_service all share the same InMemoryDatabase."""
    import src.leads.comment_bridge as bridge_mod
    import src.leads.service as leads_service_mod
    monkeypatch.setattr(bridge_mod, "supabase_db", mock_db)
    monkeypatch.setattr(bridge_mod, "identity_resolver", IdentityResolver(db=mock_db))
    monkeypatch.setattr(leads_service_mod.lead_service, "db", mock_db)
    from src.modules.connections.service import connection_service
    monkeypatch.setattr(connection_service, "owner_for_account", lambda *_: "tenant-bridge")
    return mock_db


# --------------------------------------------------------------------
# 1. Instagram comment → lead
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_instagram_comment_creates_lead_with_username(bridged_db):
    event = {
        "platform": PlatformSource.INSTAGRAM,
        "account_id": "17841400000000",
        "sender_id": "ig_commenter_42",
        "username": "customer_sara",
        "comment_id": "ig_cmt_001",
        "text": "كم السعر؟",
        "media_id": "ig_media_9",
    }
    result = await capture_comment_lead(event)

    assert result is not None
    leads = bridged_db.select("leads", {"instagram_account_id": "ig_commenter_42"})
    assert len(leads) == 1
    assert leads[0]["username"] == "customer_sara"
    assert leads[0]["source"] == "instagram"
    # Zero-fabrication: no name known from a bare comment webhook
    assert leads[0]["full_name"] is None

    msgs = bridged_db.select("messages", {"lead_id": leads[0]["id"]})
    assert len(msgs) == 1
    assert msgs[0]["platform_message_id"] == "ig_cmt_001"
    assert msgs[0]["content"] == "كم السعر؟"
    assert msgs[0]["sender_type"] == "lead"


@pytest.mark.asyncio
async def test_facebook_comment_creates_lead_with_webhook_name(bridged_db):
    """FB feed webhook carries from.name — the lead gets the real name."""
    event = {
        "platform": PlatformSource.FACEBOOK,
        "account_id": "1108892288983475",
        "sender_id": "fb_commenter_7",
        "sender_name": "Mahmoud Ali",
        "comment_id": "fb_cmt_002",
        "text": "interested",
        "post_id": "fb_post_5",
    }
    await capture_comment_lead(event)

    leads = bridged_db.select("leads", {"facebook_account_id": "fb_commenter_7"})
    assert len(leads) == 1
    assert leads[0]["full_name"] == "Mahmoud Ali"


@pytest.mark.asyncio
async def test_comment_capture_is_idempotent(bridged_db):
    """Same comment delivered twice → ONE lead, ONE message."""
    event = {
        "platform": PlatformSource.INSTAGRAM,
        "account_id": "acc",
        "sender_id": "ig_samer",
        "username": "same_guy",
        "comment_id": "cmt_dup_1",
        "text": "hi",
    }
    await capture_comment_lead(event)
    await capture_comment_lead(event)

    leads = bridged_db.select("leads", {"instagram_account_id": "ig_samer"})
    assert len(leads) == 1
    msgs = bridged_db.select("messages", {"lead_id": leads[0]["id"]})
    assert len(msgs) == 1


@pytest.mark.asyncio
async def test_repeat_commenter_appends_to_existing_lead(bridged_db):
    """Second comment from the same person → deterministic match, new message."""
    base = {
        "platform": PlatformSource.INSTAGRAM, "account_id": "acc",
        "sender_id": "ig_repeat", "username": "repeat_user",
    }
    await capture_comment_lead({**base, "comment_id": "c1", "text": "first"})
    await capture_comment_lead({**base, "comment_id": "c2", "text": "second"})

    leads = bridged_db.select("leads", {"instagram_account_id": "ig_repeat"})
    assert len(leads) == 1
    msgs = bridged_db.select("messages", {"lead_id": leads[0]["id"]})
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_comment_without_required_fields_is_ignored(bridged_db):
    result = await capture_comment_lead({"platform": PlatformSource.INSTAGRAM, "text": "orphan"})
    assert result is None
    assert bridged_db.select("leads") == []


# --------------------------------------------------------------------
# 2. Threads extractor + deterministic resolution
# --------------------------------------------------------------------
def test_threads_extractor_maps_profile():
    lead = ProfileDataExtractor.extract_from_threads({
        "id": "th_user_9",
        "username": "threads_customer",
        "name": "Nour Hassan",
        "thread_profile_picture_url": "https://example.com/nour.jpg",
    })
    assert lead.source == PlatformSource.THREADS
    assert lead.threads_account_id == "th_user_9"
    assert lead.username == "threads_customer"
    assert lead.full_name == "Nour Hassan"
    assert lead.avatar_url == "https://example.com/nour.jpg"
    assert lead.profile_url == "https://www.threads.net/@threads_customer"
    assert lead.data_provenance.source_platform == PlatformSource.THREADS


def test_threads_extractor_zero_fabrication():
    lead = ProfileDataExtractor.extract_from_threads({"username": "only_username"})
    assert lead.full_name is None
    assert lead.avatar_url is None
    assert lead.threads_account_id is None


def test_resolver_deterministic_threads_match(mock_db):
    """Same threads_account_id → deterministic match, not a new lead."""
    resolver = IdentityResolver(db=mock_db)
    first, is_new, _ = resolver.resolve_and_save_lead(
        ProfileDataExtractor.extract_from_threads({"id": "th_77", "username": "same_th"}))
    assert is_new is True

    second, is_new2, queue_id = resolver.resolve_and_save_lead(
        ProfileDataExtractor.extract_from_threads({"id": "th_77", "username": "same_th"}))
    assert is_new2 is False
    assert second["id"] == first["id"]
    assert queue_id is None


# --------------------------------------------------------------------
# 3. Threads replies sync (pull-based bridge)
# --------------------------------------------------------------------
def _threads_sync_with(monkeypatch, mock_db, profile_fetch):
    import src.meta_api.extended_api as ext
    from src.leads import service as leads_service_mod
    sync = ext.ThreadsLeadsSync(
        db=mock_db,
        resolver=IdentityResolver(db=mock_db),
        lead_svc=leads_service_mod.lead_service,
    )
    monkeypatch.setattr(leads_service_mod.lead_service, "db", mock_db)
    monkeypatch.setattr(sync, "_resolve_token", MagicMock(return_value="tok"))
    sync._fetch_threads_profile = profile_fetch
    return sync


@pytest.mark.asyncio
async def test_threads_reply_capture_creates_lead(monkeypatch):
    mock_db = InMemoryDatabase()
    sync = _threads_sync_with(
        monkeypatch, mock_db,
        AsyncMock(return_value={"username": "th_reply_guy", "name": "Omar Sami",
                                "thread_profile_picture_url": "https://x/omar.jpg"}))
    reply = {"id": "reply_1", "text": "مهتم بالخدمة", "timestamp": "2026-09-10T10:00:00+00:00",
             "username": "th_reply_guy", "from_user": {"id": "th_author_5"}}

    result = await sync.capture_thread_reply(reply, token="tok", user_id="tenant-bridge")

    assert result["lead_id"]
    leads = mock_db.select("leads", {"threads_account_id": "th_author_5"})
    assert len(leads) == 1
    assert leads[0]["full_name"] == "Omar Sami"
    assert leads[0]["avatar_url"] == "https://x/omar.jpg"
    msgs = mock_db.select("messages", {"lead_id": leads[0]["id"]})
    assert len(msgs) == 1
    assert msgs[0]["platform"] == "threads"
    assert msgs[0]["content"] == "مهتم بالخدمة"


@pytest.mark.asyncio
async def test_threads_reply_without_author_id_still_captures_by_username(monkeypatch):
    """If the API gives no author id: username-keyed capture, no fabricated profile."""
    mock_db = InMemoryDatabase()
    sync = _threads_sync_with(monkeypatch, mock_db, AsyncMock(return_value={}))
    reply = {"id": "reply_2", "text": "good", "timestamp": "2026-09-10T10:00:00+00:00",
             "username": "no_id_user"}

    result = await sync.capture_thread_reply(reply, token="tok", user_id="tenant-bridge")

    assert result["lead_id"]
    leads = [l for l in mock_db.select("leads")
             if l.get("source") == "threads" and l.get("username") == "no_id_user"]
    assert len(leads) == 1
    assert leads[0]["threads_account_id"] is None
    assert leads[0]["full_name"] is None


@pytest.mark.asyncio
async def test_threads_reply_idempotent(monkeypatch):
    mock_db = InMemoryDatabase()
    sync = _threads_sync_with(monkeypatch, mock_db, AsyncMock(return_value={}))
    reply = {"id": "reply_dup", "text": "again", "timestamp": "2026-09-10T10:00:00+00:00",
             "username": "dup_user", "from_user": {"id": "th_dup"}}

    await sync.capture_thread_reply(reply, token="tok", user_id="tenant-bridge")
    await sync.capture_thread_reply(reply, token="tok", user_id="tenant-bridge")

    leads = mock_db.select("leads", {"threads_account_id": "th_dup"})
    assert len(leads) == 1
    assert len(mock_db.select("messages", {"lead_id": leads[0]["id"]})) == 1


# --------------------------------------------------------------------
# 4. Inbox exposes Threads channel
# --------------------------------------------------------------------
def test_inbox_thread_channel_threads(monkeypatch):
    from starlette.requests import Request
    from src.core.auth import SESSION_COOKIE_NAME, create_session_token
    from src.core.supabase_client import InMemoryDatabase
    import src.modules.inbox_onboarding as inbox_mod

    db = InMemoryDatabase()
    lead = db.insert("leads", {"source": "threads", "full_name": "Omar Sami",
                               "username": "th_reply_guy",
                               "threads_account_id": "th_author_5", "user_id": "tenant-bridge"})
    db.insert("messages", {"lead_id": lead["id"], "user_id": "tenant-bridge", "sender_type": "lead",
                               "platform": "threads", "content": "hi",
                               "sent_at": "2026-09-10T10:00:00+00:00"})

    monkeypatch.setattr(inbox_mod, "supabase_db", db)
    monkeypatch.setattr(inbox_mod.lead_service, "get_messages_for_lead",
                        lambda lead_id, user_id=None: db.select(
                            "messages", {"lead_id": lead["id"], "user_id": user_id}))
    token = create_session_token("tenant-bridge", "user", "bridge@example.test")
    request = Request({"type": "http", "headers": [
        (b"cookie", f"{SESSION_COOKIE_NAME}={token}".encode())
    ]})
    resp = asyncio.run(inbox_mod.get_inbox_conversations(request))

    conv = next(c for c in resp["conversations"] if c["lead_id"] == lead["id"])
    assert conv["channel"] == "threads"
    assert conv["platformText"] == "🧵 Threads"
