"""
Tests for Threads OAuth flow, credential storage, and publisher integration.
All network calls mocked — no real Threads API access in tests.
"""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.meta_api import threads_oauth as mod
from src.meta_api.threads_oauth import ThreadsOAuthManager, get_active_threads_token
from src.meta_api.extended_api import threads_publisher


@pytest.fixture
def oauth(monkeypatch):
    m = ThreadsOAuthManager()
    # Isolate state + storage from real Supabase during tests
    m._pending_states = {}
    monkeypatch.setattr(mod, "_save_stored_creds", lambda creds: True)
    monkeypatch.setattr(mod, "_get_stored_creds", lambda: {})
    return m


# --------------------------------------------------------------------
# Authorize URL
# --------------------------------------------------------------------
def test_authorize_url_builds_with_state(oauth):
    from src.config import settings
    if not settings.THREADS_APP_ID:
        pytest.skip("THREADS_APP_ID not configured in test env")
    res = oauth.build_authorize_url()
    assert res["status"] == "success"
    assert "threads.net/oauth/authorize" in res["authorize_url"]
    assert res["state"] in oauth._pending_states


def test_state_validation_single_use(oauth):
    oauth._pending_states["test-state-1"] = 9999999999  # far future
    assert oauth.validate_state("test-state-1") is True
    # State is consumed after first use (CSRF)
    assert oauth.validate_state("test-state-1") is False
    assert oauth.validate_state("bogus") is False
    assert oauth.validate_state(None) is False


def test_state_expired_rejected(oauth):
    oauth._pending_states["old-state"] = 0  # epoch -> expired
    assert oauth.validate_state("old-state") is False


# --------------------------------------------------------------------
# Token exchange (mocked HTTP)
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_exchange_code_full_flow(oauth, monkeypatch):
    from src.config import settings
    if not settings.THREADS_APP_ID:
        pytest.skip("THREADS_APP_ID not configured in test env")

    class FakeResp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json
        @property
        def text(self):
            return str(self._json)

    saved = {}
    monkeypatch.setattr(mod, "_save_stored_creds", lambda creds: saved.update(creds) or True)

    class ExchangeCtx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, **kw):
            assert "oauth/access_token" in url
            return FakeResp(200, {"access_token": "short-token"})
        async def get(self, url, **kw):
            assert "access_token" in url
            return FakeResp(200, {"access_token": "long-token", "expires_in": 5184000})

    # First AsyncClient context = token exchange; profile fetch inside
    # _finalize_credentials is patched out below.
    monkeypatch.setattr(mod.httpx, "AsyncClient", lambda **kw: ExchangeCtx())

    async def fake_profile(token):
        return {"id": "th-user-1", "username": "karim_test"}
    monkeypatch.setattr(oauth, "_finalize_credentials", oauth._finalize_credentials)
    # Replace the httpx usage inside _finalize_credentials by stubbing profile fetch:
    import src.meta_api.threads_oauth as m2
    # Simplest: temporarily monkeypatch httpx.AsyncClient back to a profile-aware ctx
    class ProfileCtx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, url, **kw):
            return FakeResp(200, {"id": "th-user-1", "username": "karim_test"})

    # Run exchange with a switching client: first call -> ExchangeCtx, later -> ProfileCtx
    original_lambda = mod.httpx.AsyncClient
    state = {"n": 0}
    def switching(**kw):
        state["n"] += 1
        if state["n"] == 1:
            return ExchangeCtx()
        return ProfileCtx()
    monkeypatch.setattr(mod.httpx, "AsyncClient", switching)

    result = await oauth.exchange_code("auth-code-123")
    assert result["status"] == "success"
    assert result.get("username") == "karim_test"
    assert saved.get("access_token") == "long-token"


# --------------------------------------------------------------------
# Publisher integration
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_publish_skips_without_token(monkeypatch):
    monkeypatch.setattr("src.meta_api.threads_oauth.get_active_threads_token", lambda: None)
    result = await threads_publisher.publish_thread("مرحبا")
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_publish_flow_with_mocked_graph(monkeypatch):
    monkeypatch.setattr("src.meta_api.threads_oauth.get_active_threads_token", lambda: "tok-123")
    monkeypatch.setattr(
        "src.meta_api.extended_api.supabase_db.insert", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        threads_publisher, "_threads_user_id", lambda token: "th-user-1"
    )

    class FakeResp:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json = json_data
        def json(self):
            return self._json
        @property
        def text(self):
            return str(self._json)

    calls = []

    class Ctx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, **kw):
            calls.append(url)
            if "threads" in url and "publish" not in url:
                return FakeResp(200, {"id": "container-1"})
            return FakeResp(200, {"id": "thread-999"})

    monkeypatch.setattr(
        "src.meta_api.extended_api.httpx.AsyncClient", lambda **kw: Ctx()
    )

    result = await threads_publisher.publish_thread("اختبار نشر")
    assert result["status"] == "success"
    assert result["thread_id"] == "thread-999"
    assert len(calls) == 2  # create container + publish


# --------------------------------------------------------------------
# Token freshness
# --------------------------------------------------------------------
def test_get_active_token_expiry(monkeypatch):
    import time
    future = int(time.time()) + 86400
    past = int(time.time()) - 100
    monkeypatch.setattr(mod, "_get_stored_creds", lambda: {"access_token": "t1", "expires_at": future})
    assert get_active_threads_token() == "t1"
    monkeypatch.setattr(mod, "_get_stored_creds", lambda: {"access_token": "t2", "expires_at": past})
    assert get_active_threads_token() is None


def test_status_and_disconnect(oauth, monkeypatch):
    assert oauth.get_status()["connected"] is False
    monkeypatch.setattr(
        mod, "_get_stored_creds",
        lambda: {"access_token": "t", "expires_at": 9999999999, "threads_username": "karim"}
    )
    st = oauth.get_status()
    assert st["connected"] is True and st["username"] == "karim"
    disc = oauth.disconnect()
    assert disc["status"] == "success"
