"""Tests: AI Master Pause (Wave 9.8) — global + per-user suppression semantics."""
import pytest
from unittest.mock import MagicMock, patch

from src.ai.pause import is_ai_paused, set_ai_pause, pause_status, GLOBAL_PAUSE_KEY


@pytest.fixture
def fake_db():
    """In-memory settings + users backing the pause helpers."""
    settings_store = {}
    users = {}

    class FakeDB:
        def get_setting(self, key):
            return settings_store.get(key)

        def set_setting(self, key, value):
            settings_store[key] = value
            return True

        def select(self, table, filters=None):
            if table == "users":
                rows = list(users.values())
                if filters:
                    for k, v in filters.items():
                        rows = [r for r in rows if r.get(k) == v]
                return rows
            return []

        def update(self, table, rid, updates):
            if table == "users" and rid in users:
                users[rid].update(updates)
                return users[rid]
            return None

    return FakeDB(), settings_store, users


def test_default_ai_active(fake_db, monkeypatch):
    db, _, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    assert is_ai_paused("u1") is False
    assert is_ai_paused(None) is False


def test_global_pause_suppresses_everyone(fake_db, monkeypatch):
    db, store, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    store[GLOBAL_PAUSE_KEY] = True
    assert is_ai_paused(None) is True
    assert is_ai_paused("any_user") is True  # global wins over per-user state


def test_user_pause_without_global(fake_db, monkeypatch):
    db, _, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    users["u_owner"] = {"id": "u_owner", "ai_paused": True}
    users["u_other"] = {"id": "u_other", "ai_paused": False}
    assert is_ai_paused("u_owner") is True
    assert is_ai_paused("u_other") is False


def test_set_ai_pause_user_scope(fake_db, monkeypatch):
    db, store, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    users["u1"] = {"id": "u1", "ai_paused": False}

    res = set_ai_pause(True, "u1", is_admin=False)
    assert res["user_paused"] is True
    assert res["global_set"] is False
    assert store.get(GLOBAL_PAUSE_KEY) is None  # non-admin cannot touch global
    assert is_ai_paused("u1") is True


def test_set_ai_pause_admin_sets_global(fake_db, monkeypatch):
    db, store, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    users["admin1"] = {"id": "admin1", "ai_paused": False}

    res = set_ai_pause(True, "admin1", is_admin=True)
    assert res["global_set"] is True
    assert store.get(GLOBAL_PAUSE_KEY) is True
    assert is_ai_paused(None) is True  # legacy path suppressed


def test_pause_status_shape(fake_db, monkeypatch):
    db, _, users = fake_db
    monkeypatch.setattr("src.ai.pause.supabase_db", db)
    users["u1"] = {"id": "u1", "ai_paused": False}
    st = pause_status("u1", is_admin=False)
    assert set(st.keys()) == {"user_paused", "global_paused", "effective_paused"}


@pytest.mark.asyncio
async def test_orchestrator_stores_message_but_skips_reply_when_paused(monkeypatch):
    """Global pause: inbound message stored, NO AI reply, ai_paused flag returned."""
    from src.agent.orchestrator import AgentOrchestrator
    from src.leads.models import PlatformSource

    orch = AgentOrchestrator()

    # NOTE: use monkeypatch (auto-restored) for SINGLETON attributes — direct
    # assignment leaks mocks into later tests (full-suite pollution bug).
    from unittest.mock import AsyncMock, MagicMock
    monkeypatch.setattr(orch.client, "get_profile", AsyncMock(return_value={}))

    lead_row = {"id": "lead_p", "human_takeover": False, "user_id": "owner_1",
                "facebook_account_id": "psid_1"}
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
    stored = []
    monkeypatch.setattr(orch.lead_svc, "add_message",
                        MagicMock(side_effect=lambda m: stored.append(m)))

    monkeypatch.setattr("src.ai.pause.is_ai_paused", lambda uid: True)

    event = {"platform": PlatformSource.FACEBOOK, "sender_id": "psid_1",
             "recipient_id": "page_1", "message_id": "m_pause", "text": "hi", "raw_event": {}}
    result = await orch.process_incoming_message_event(event)

    assert result.get("ai_paused") is True
    assert result.get("reply_sent") is None
    assert len(stored) == 1  # inbound message still stored for manual reply
