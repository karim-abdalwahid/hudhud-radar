"""Tests for the tenant-bound Threads OAuth and publisher flow.

No test may rely on the removed global app_settings/env token fallback.
"""
import pytest

from src.core.supabase_client import InMemoryDatabase
from src.meta_api import threads_oauth as mod
from src.meta_api.threads_oauth import ThreadsOAuthManager, get_active_threads_token
from src.meta_api.extended_api import threads_publisher


@pytest.fixture
def oauth():
    return ThreadsOAuthManager()


def test_authorize_url_builds_tenant_bound_state(oauth):
    from src.config import settings
    if not settings.THREADS_APP_ID:
        pytest.skip("THREADS_APP_ID not configured in test env")
    res = oauth.build_authorize_url("tenant-a")
    assert res["status"] == "success"
    assert "threads.net/oauth/authorize" in res["authorize_url"]
    assert oauth._pending_states[res["state"]]["user_id"] == "tenant-a"


def test_state_validation_is_single_use_and_owner_bound(oauth):
    oauth._pending_states["test-state-1"] = {
        "created_at": 9999999999, "user_id": "tenant-a"}
    assert oauth.validate_state("test-state-1", "tenant-b") is False
    # The rejected state was consumed deliberately, so it cannot be replayed.
    assert oauth.validate_state("test-state-1", "tenant-a") is False
    oauth._pending_states["test-state-2"] = {
        "created_at": 9999999999, "user_id": "tenant-a"}
    assert oauth.validate_state("test-state-2", "tenant-a") is True
    assert oauth.validate_state("test-state-2", "tenant-a") is False
    assert oauth.validate_state(None, "tenant-a") is False


def test_state_expired_rejected(oauth):
    oauth._pending_states["old-state"] = {"created_at": 0, "user_id": "tenant-a"}
    assert oauth.validate_state("old-state", "tenant-a") is False


@pytest.mark.asyncio
async def test_exchange_code_writes_to_given_tenant(oauth, monkeypatch):
    from src.config import settings
    if not settings.THREADS_APP_ID:
        pytest.skip("THREADS_APP_ID not configured in test env")

    class FakeResp:
        status_code = 200
        def json(self):
            return {"access_token": "long-token", "expires_in": 5184000}
        @property
        def text(self):
            return "{}"

    class ExchangeCtx:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **kw): return FakeResp()
        async def get(self, *a, **kw): return FakeResp()

    captured = {}
    async def finalize(token, expires_in, user_id):
        captured.update(token=token, expires_in=expires_in, user_id=user_id)
        return {"status": "success", "username": "karim_test"}

    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: ExchangeCtx())
    monkeypatch.setattr(oauth, "_finalize_credentials", finalize)
    result = await oauth.exchange_code("auth-code-123", user_id="tenant-a")
    assert result["status"] == "success"
    assert captured == {"token": "long-token", "expires_in": 5184000, "user_id": "tenant-a"}


@pytest.mark.asyncio
async def test_publish_skips_without_tenant_token(monkeypatch):
    monkeypatch.setattr(threads_publisher, "_resolve_token", lambda user_id: None)
    result = await threads_publisher.publish_thread("مرحبا", user_id="tenant-a")
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_publish_flow_uses_tenant_token(monkeypatch):
    monkeypatch.setattr(threads_publisher, "_resolve_token", lambda user_id: "tok-123")
    monkeypatch.setattr("src.meta_api.extended_api.supabase_db.insert", lambda *a, **kw: None)

    class FakeResp:
        def __init__(self, body): self.status_code, self._body = 200, body
        def json(self): return self._body
        @property
        def text(self): return str(self._body)

    calls = []
    class Ctx:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, **kw):
            calls.append((url, kw))
            return FakeResp({"id": "container-1" if len(calls) == 1 else "thread-999"})

    monkeypatch.setattr("src.meta_api.extended_api.httpx.AsyncClient", lambda **kw: Ctx())
    result = await threads_publisher.publish_thread("اختبار نشر", user_id="tenant-a")
    assert result["status"] == "success"
    assert result["thread_id"] == "thread-999"
    assert len(calls) == 2


def test_get_active_token_delegates_to_same_tenant(monkeypatch):
    from src.modules.connections.service import connection_service
    monkeypatch.setattr(connection_service, "get_active_token", lambda user_id, platform: "t1")
    assert get_active_threads_token("tenant-a") == "t1"


def test_status_and_disconnect_are_tenant_scoped(oauth, monkeypatch):
    db = InMemoryDatabase()
    db.is_connected = True
    db.insert("platform_connections", {
        "user_id": "tenant-a", "platform": "threads", "account_id": "th-1",
        "account_name": "@karim", "status": "active",
    })
    monkeypatch.setattr(mod, "supabase_db", db)
    assert oauth.get_status("tenant-b")["connected"] is False
    assert oauth.get_status("tenant-a")["username"] == "karim"
    from src.modules.connections.service import connection_service
    monkeypatch.setattr(connection_service, "revoke", lambda user_id, platform: user_id == "tenant-a")
    assert oauth.disconnect("tenant-a")["disconnected"] is True
