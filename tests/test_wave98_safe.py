"""Wave 9.8 safe-batch tests: per-page token resolution, send override,
Threads proactive refresh, and the Threads webhook receiver."""
import hashlib
import hmac as _hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.core.supabase_client import InMemoryDatabase


# ----------------------------------------------------------------------
# 1. resolve_page_token (per-user connection -> decrypted token; else None)
# ----------------------------------------------------------------------
class FakeDB(InMemoryDatabase):
    is_connected = True


def test_resolve_page_token_from_connection(monkeypatch):
    from src.core.crypto import encrypt_token
    import src.core.supabase_client as sc
    db = FakeDB()
    db.insert("platform_connections", {
        "user_id": "u1", "platform": "facebook", "account_id": "1234",
        "access_token_encrypted": encrypt_token("PAGE_TOKEN_1"),
        "status": "active",
    })
    monkeypatch.setattr(sc, "supabase_db", db)
    from src.meta_api.client import resolve_page_token
    assert resolve_page_token("1234") == "PAGE_TOKEN_1"


def test_resolve_page_token_misses_and_guards(monkeypatch):
    import src.core.supabase_client as sc
    db = FakeDB()
    db.insert("platform_connections", {
        "user_id": "u1", "platform": "threads", "account_id": "9",
        "access_token_encrypted": "x", "status": "active"})
    monkeypatch.setattr(sc, "supabase_db", db)
    from src.meta_api.client import resolve_page_token
    assert resolve_page_token(None) is None            # no id -> None (legacy)
    assert resolve_page_token("your-xxx") is None      # placeholder -> None
    assert resolve_page_token("does-not-exist") is None  # miss -> None


# ----------------------------------------------------------------------
# 2. Send paths honor the access_token override
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_send_facebook_uses_override_token():
    from src.meta_api.client import meta_client
    captured = {}

    async def fake_post(url, params, payload, *a, **k):
        captured["params"] = params
        resp = type("R", (), {"status_code": 200, "json": lambda self: {"mid": "m1"},
                              "text": "{}"})()
        return resp

    import src.core.exceptions  # noqa
    meta_client._post_with_retry = fake_post
    await meta_client.send_facebook_message("psid_1", "hi",
                                            last_interaction_time=datetime.now(timezone.utc),
                                            access_token="PER_PAGE_TOKEN")
    assert captured["params"]["access_token"] == "PER_PAGE_TOKEN"


@pytest.mark.asyncio
async def test_send_facebook_falls_back_to_global():
    from src.meta_api.client import meta_client
    captured = {}

    async def fake_post(url, params, payload, *a, **k):
        captured["params"] = params
        return type("R", (), {"status_code": 200, "json": lambda self: {"mid": "m2"},
                              "text": "{}"})()

    meta_client._post_with_retry = fake_post
    await meta_client.send_facebook_message("psid_2", "hi",
                                            last_interaction_time=datetime.now(timezone.utc),
                                            access_token=None)
    assert captured["params"]["access_token"] == meta_client.access_token


# ----------------------------------------------------------------------
# 3. Threads proactive refresh (decision logic)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_refresh_if_expiring_legacy_only_when_close(monkeypatch):
    import src.meta_api.threads_oauth as to
    calls = []

    async def fake_refresh():
        calls.append(1)
        return {"status": "success"}

    async def fake_refresh_fail():
        calls.append(1)
        return {"status": "error", "detail": "x"}

    monkeypatch.setattr(to.threads_oauth, "refresh_token",
                        fake_refresh)
    soon = (datetime.now(timezone.utc) + timedelta(days=3)).timestamp()
    monkeypatch.setattr(to, "_get_stored_creds",
                        lambda: {"access_token": "t", "expires_at": int(soon)})
    monkeypatch.setattr(to, "supabase_db", FakeDB())
    r = await to.threads_oauth.refresh_if_expiring()
    assert calls == [1] and "legacy" in r["refreshed"]

    # far expiry -> no refresh
    calls.clear()
    far = (datetime.now(timezone.utc) + timedelta(days=40)).timestamp()
    monkeypatch.setattr(to, "_get_stored_creds",
                        lambda: {"access_token": "t", "expires_at": int(far)})
    r2 = await to.threads_oauth.refresh_if_expiring()
    assert calls == [] and r2["refreshed"] == []


@pytest.mark.asyncio
async def test_refresh_if_expiring_per_user(monkeypatch):
    import src.meta_api.threads_oauth as to
    from src.core.crypto import encrypt_token
    db = FakeDB()
    near = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    row = db.insert("platform_connections", {
        "user_id": "u1", "platform": "threads", "account_id": "7",
        "access_token_encrypted": encrypt_token("TKN"),
        "token_expires_at": near, "status": "active"})

    class FakeResp:
        status_code = 200
        def json(self): return {"access_token": "NEWTOKEN", "expires_in": 5184000}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None): return FakeResp()

    monkeypatch.setattr(to, "httpx", type("X", (), {"AsyncClient": FakeClient}))
    monkeypatch.setattr(to, "_get_stored_creds", lambda: {})
    monkeypatch.setattr(to, "supabase_db", db)
    r = await to.threads_oauth.refresh_if_expiring()
    assert "u1"[: len("u1")] in r["refreshed"]
    updated = db.select("platform_connections", {"id": row["id"]})[0]
    assert updated["token_expires_at"] != near  # new expiry written


# ----------------------------------------------------------------------
# 4. Threads webhook receiver (handshake + fail-closed HMAC + event parse)
# ----------------------------------------------------------------------
def test_threads_webhook_handshake(client):
    from src.config import settings
    r = client.get("/api/webhook/threads?hub.mode=subscribe"
                   "&hub.challenge=th_42&hub.verify_token=" + settings.EFFECTIVE_WEBHOOK_VERIFY_TOKEN)
    assert r.status_code == 200 and r.text == "th_42"
    bad = client.get("/api/webhook/threads?hub.mode=subscribe"
                     "&hub.challenge=th_42&hub.verify_token=wrong")
    assert bad.status_code == 403


def test_threads_webhook_rejects_unsigned(client):
    r = client.post("/api/webhook/threads", json={"object": "threads", "entry": []})
    assert r.status_code == 401


def test_threads_webhook_accepts_signed_reply(client):
    from src.config import settings
    payload = {"object": "threads",
               "entry": [{"id": "thread_1",
                          "changes": [{"field": "replies",
                                       "value": {"id": "rep_1", "text": "interested!",
                                                 "username": "customer_x",
                                                 "timestamp": "2026-09-11T10:00:00+0000"}}]}]}
    raw = json.dumps(payload).encode()
    sig = "sha256=" + _hmac.new((settings.THREADS_APP_SECRET or "x").encode(),
                                raw, hashlib.sha256).hexdigest()
    r = client.post("/api/webhook/threads", content=raw,
                    headers={"Content-Type": "application/json",
                             "X-Hub-Signature-256": sig})
    assert r.status_code == 200
    assert r.json()["status"] == "received"
