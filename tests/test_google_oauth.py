"""
Direct Google OAuth flow tests (Entry 028).
The consent screen must show OUR domain (redirect_uri = APP_BASE_URL),
state must be single-use CSRF, unverified emails must never create accounts,
and the legacy Supabase-hosted flow must be gone.
"""
import pytest
from starlette.testclient import TestClient

from src.config import settings


class _FakeResp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = str(body)
    def json(self):
        return self._body


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = responses
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def post(self, url, **kw):
        return self._responses["post"](url, kw)
    async def get(self, url, **kw):
        return self._responses["get"](url, kw)


@pytest.fixture
def google_creds(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")


def test_google_start_redirects_to_google_with_our_domain(client: TestClient, google_creds, monkeypatch):
    stored = {}
    monkeypatch.setattr(
        "src.main.supabase_db.set_setting",
        lambda k, v: stored.update({k: v}) or True,
    )
    r = client.get("/auth/google", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test-client-id" in loc
    # THE FIX: redirect_uri must be OUR canonical domain — never Supabase
    from src.config import settings as _settings
    expected_ru = f"redirect_uri={_settings.APP_BASE_URL.rstrip('/').replace('/', '%2F').replace(':', '%3A')}%2Fauth%2Fgoogle%2Fcallback"
    assert expected_ru in loc, f"expected {expected_ru} in {loc}"
    assert "state=" in loc
    assert "supabase" not in loc.lower()


def test_google_start_without_creds_returns_503(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", None)
    r = client.get("/auth/google", follow_redirects=False)
    assert r.status_code == 503


def test_google_callback_rejects_invalid_state(client: TestClient, google_creds):
    r = client.get("/auth/google/callback?code=x&state=invalid-state", follow_redirects=False)
    assert r.status_code == 303
    assert "/login?google=error" in r.headers["location"]


def test_google_callback_full_success_creates_user(client: TestClient, google_creds, monkeypatch):
    # Seed a valid state through the start endpoint
    monkeypatch.setattr("src.main.supabase_db.set_setting", lambda k, v: True)
    r = client.get("/auth/google", follow_redirects=False)
    loc = r.headers["location"]
    state = loc.split("state=")[1].split("&")[0]

    created = {}
    class _US:
        def get_by_email(self, email):
            return None
    import src.core.auth as auth_mod
    monkeypatch.setattr(auth_mod, "user_store", _US())
    monkeypatch.setattr(
        "src.core.supabase_client.supabase_db.insert",
        lambda table, data: {**data, "id": "guser-1"} if table == "users" else {},
    )

    def fake_post(url, kw):
        assert "oauth2.googleapis.com/token" in url
        assert kw["data"]["grant_type"] == "authorization_code"
        return _FakeResp(200, {"access_token": "gtok"})
    def fake_get(url, kw):
        assert "openidconnect.googleapis.com" in url
        return _FakeResp(200, {
            "email": "newuser@gmail.com", "email_verified": True,
            "name": "New Google User",
        })

    import httpx as _httpx
    monkeypatch.setattr(_httpx, "AsyncClient", lambda **kw: _FakeAsyncClient({
        "post": fake_post, "get": fake_get,
    }))

    r = client.get(f"/auth/google/callback?code=good&state={state}", follow_redirects=False)
    assert r.status_code == 303
    assert "/dashboard" in r.headers["location"]
    # session cookie issued
    assert any(c.name == "hudhud_session" or "session" in c.name for c in client.cookies.jar)


def test_google_callback_rejects_unverified_email(client: TestClient, google_creds, monkeypatch):
    monkeypatch.setattr("src.main.supabase_db.set_setting", lambda k, v: True)
    r = client.get("/auth/google", follow_redirects=False)
    state = r.headers["location"].split("state=")[1].split("&")[0]

    def fake_post(url, kw):
        return _FakeResp(200, {"access_token": "gtok"})
    def fake_get(url, kw):
        return _FakeResp(200, {"email": "unverified@gmail.com", "email_verified": False})

    import httpx as _httpx
    monkeypatch.setattr(_httpx, "AsyncClient", lambda **kw: _FakeAsyncClient({
        "post": fake_post, "get": fake_get,
    }))
    r = client.get(f"/auth/google/callback?code=x&state={state}", follow_redirects=False)
    assert "/login?google=error" in r.headers["location"]


def test_legacy_supabase_exchange_flow_removed():
    import inspect
    from src import main as main_mod
    src = inspect.getsource(main_mod)
    assert "/auth/google/exchange" not in src
    assert "auth/v1/authorize" not in src
