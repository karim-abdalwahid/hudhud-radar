"""
Phase 9.7 tests — per-user platform_connections: crypto at rest, entitlement
gate (fail-closed), store/upsert/revoke, wizard overview (golden upsell),
OAuth state signing. FULLY isolated (fake tables — no live Supabase writes).
"""
import uuid

import pytest
from fastapi import HTTPException

from src.core import supabase_client as sb_mod
from src.core.crypto import decrypt_token, encrypt_token
from src.modules.connections.service import connection_service
from src.modules.connections import routes as conn_routes

UID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def fake_tables(monkeypatch):
    conns, ents = {}, {}

    def pick(table):
        return conns if table == "platform_connections" else ents

    def select(table, filters=None):
        if table not in ("platform_connections", "user_entitlements"):
            return []
        rows = list(pick(table).values())
        f = filters or {}
        for k, v in f.items():
            rows = [r for r in rows if r.get(k) == v]
        return rows

    def insert(table, row):
        if table not in ("platform_connections", "user_entitlements"):
            return None
        rid = str(uuid.uuid4())
        pick(table)[rid] = {**row, "id": rid}
        return pick(table)[rid]

    def update(table, rid, fields):
        store = pick(table)
        if table not in ("platform_connections", "user_entitlements") or rid not in store:
            return None
        store[rid].update(fields)
        return store[rid]

    monkeypatch.setattr(sb_mod.supabase_db, "select", select)
    monkeypatch.setattr(sb_mod.supabase_db, "insert", insert)
    monkeypatch.setattr(sb_mod.supabase_db, "update", update)
    return {"conns": conns, "ents": ents}


def _grant(user_id: str, entitlement: str):
    from src.modules.billing.services import entitlement_service
    entitlement_service.grant(user_id, entitlement, source="test")


# ---- crypto at rest -------------------------------------------------------
def test_crypto_roundtrip():
    secret = "EAAx9-payment-token-value-42"
    assert decrypt_token(encrypt_token(secret)) == secret


def test_crypto_tamper_raises():
    ct = encrypt_token("secret-value")
    tampered = ct[:-6] + ("AAAAAA" if ct[-6:] != "AAAAAA" else "BBBBBB")
    with pytest.raises(ValueError):
        decrypt_token(tampered)


# ---- storage --------------------------------------------------------------
def test_store_encrypts_at_rest(fake_tables):
    row = connection_service.store(UID, "facebook", "EAA-plaintext-token",
                                   account_id="p1", account_name="My Page",
                                   scopes=["pages_show_list"])
    assert row is not None
    stored = fake_tables["conns"][row["id"]]
    assert stored["access_token_encrypted"] != "EAA-plaintext-token"
    assert "EAA-plaintext-token" not in str(stored)
    assert decrypt_token(stored["access_token_encrypted"]) == "EAA-plaintext-token"


def test_store_upsert_updates_not_duplicates(fake_tables):
    connection_service.store(UID, "threads", "tok-A", account_id="th1")
    connection_service.store(UID, "threads", "tok-B", account_id="th1")
    rows = [r for r in fake_tables["conns"].values()
            if r["user_id"] == UID and r["platform"] == "threads"]
    assert len(rows) == 1
    assert decrypt_token(rows[0]["access_token_encrypted"]) == "tok-B"


def test_revoke_sets_status(fake_tables):
    connection_service.store(UID, "threads", "tok-A", account_id="th1")
    assert connection_service.revoke(UID, "threads") is True
    rows = [r for r in fake_tables["conns"].values() if r["user_id"] == UID]
    assert rows and rows[0]["status"] == "revoked"


# ---- entitlement gate (fail-closed) ---------------------------------------
def test_get_active_token_denied_without_entitlement(fake_tables):
    connection_service.store(UID, "threads", "tok-A", account_id="th1")
    # connection exists, entitlement absent → None (fail-closed)
    assert connection_service.get_active_token(UID, "threads") is None


def test_get_active_token_with_entitlement(fake_tables):
    connection_service.store(UID, "threads", "tok-A", account_id="th1")
    _grant(UID, "platform:threads")
    assert connection_service.get_active_token(UID, "threads") == "tok-A"


def test_assert_entitled_raises_403(fake_tables):
    with pytest.raises(HTTPException) as ei:
        connection_service.assert_entitled(UID, "instagram")
    assert ei.value.status_code == 403


def test_assert_entitled_passes(fake_tables):
    _grant(UID, "platform:instagram")
    assert connection_service.assert_entitled(UID, "instagram") is True


def test_gate_blocks_even_with_connection(fake_tables):
    """The golden rule: capability never grants — connection + no payment = 403."""
    connection_service.store(UID, "facebook", "EAA-page-token", account_id="p1")
    with pytest.raises(HTTPException) as ei:
        connection_service.assert_entitled(UID, "facebook")
    assert ei.value.status_code == 403
    assert connection_service.get_active_token(UID, "facebook") is None


# ---- wizard overview: golden upsell ---------------------------------------
def test_overview_upsell_on_discovery(fake_tables):
    connection_service.store(UID, "facebook", "EAA-tok", account_id="p1",
                             metadata={"linked_ig_username": "client_shop",
                                       "linked_ig_id": "1784"})
    ov = connection_service.overview(UID)
    assert "platform:instagram" not in ov["entitlements"]
    assert len(ov["upsell"]) == 1
    u = ov["upsell"][0]
    assert u["platform"] == "instagram" and u["account"] == "@client_shop"
    assert "checkout" in u["checkout_url"]


def test_overview_no_upsell_when_entitled(fake_tables):
    connection_service.store(UID, "facebook", "EAA-tok", account_id="p1",
                             metadata={"linked_ig_username": "client_shop"})
    _grant(UID, "platform:instagram")
    assert connection_service.overview(UID)["upsell"] == []


# ---- OAuth state signing (CSRF) -------------------------------------------
def test_state_roundtrip():
    st = conn_routes._sign_state(UID, "facebook")
    assert conn_routes._verify_state(st, "facebook") == UID


def test_state_wrong_platform_rejected():
    st = conn_routes._sign_state(UID, "facebook")
    assert conn_routes._verify_state(st, "instagram") is None


def test_state_tampered_rejected():
    st = conn_routes._sign_state(UID, "facebook")
    assert conn_routes._verify_state(st[:-4] + "AAAA", "facebook") is None


def test_state_expired_rejected(monkeypatch):
    import src.modules.connections.routes as r
    st = r._sign_state(UID, "facebook")
    real_time = r.time.time
    monkeypatch.setattr(r.time, "time", lambda: real_time() + 3600)
    assert r._verify_state(st, "facebook") is None


# ---- HTTP surface ----------------------------------------------------------
def test_overview_requires_auth(anon_client):
    assert anon_client.get("/api/connections").status_code == 401


def test_authorize_requires_entitlement(client_as_user, fake_tables):
    """Paid gate on the door itself: no facebook entitlement → 403."""
    res = client_as_user.get("/api/connections/facebook/authorize")
    assert res.status_code == 403


def test_authorize_returns_url_when_entitled(client, fake_tables):
    """Admin session (conftest client) + granted entitlement → authorize URL."""
    me = client.get("/auth/me").json()
    _grant(me["user_id"], "platform:facebook")
    res = client.get("/api/connections/facebook/authorize")
    assert res.status_code == 200
    assert res.json()["authorize_url"].startswith("https://www.facebook.com/v26.0/dialog/oauth")
    assert "state=" in res.json()["authorize_url"]


def test_instagram_authorize_url_includes_state(client, fake_tables, monkeypatch):
    """AUDIT-2026-09-15 Fix: IG authorize must sign `state` — the callback REJECTS
    state-less doors (invalid_state), which left the IG door permanently broken."""
    me = client.get("/auth/me").json()
    _grant(me["user_id"], "platform:instagram")
    from src.config import settings as _s
    monkeypatch.setattr(_s, "IG_APP_ID", "123456789012345")
    res = client.get("/api/connections/instagram/authorize")
    assert res.status_code == 200
    url = res.json()["authorize_url"]
    assert url.startswith("https://www.instagram.com/oauth/authorize?")
    assert "state=" in url
    # callback returns 303 to settings with connect_error on bad state, so a
    # valid door must carry a state that _verify_state accepts
    from urllib.parse import urlparse, parse_qs
    st = parse_qs(urlparse(url).query).get("state", [""])[0]
    assert conn_routes._verify_state(st, "instagram") == me["user_id"]


# ---- IG 60-day token refresh (AUDIT-2026-09-15 Fix) ------------------------
@pytest.mark.asyncio
async def test_refresh_instagram_skips_far_future_tokens(fake_tables):
    """Tokens expiring beyond the threshold must NOT be touched."""
    from datetime import datetime, timedelta, timezone
    future = datetime.now(timezone.utc) + timedelta(days=45)
    connection_service.store(UID, "instagram", "tok-healthy", account_id="ig1")
    for r in fake_tables["conns"].values():
        if r["platform"] == "instagram":
            r["token_expires_at"] = future.isoformat()
    res = await connection_service.refresh_instagram_if_expiring()
    assert res["status"] == "success"
    assert res["refreshed"] == [] and res["failed"] == []


@pytest.mark.asyncio
async def test_refresh_instagram_refreshes_expiring_token(fake_tables, monkeypatch):
    """Token expiring within threshold is refreshed via ig_refresh_token and
    the row is updated with the new encrypted token + new expiry."""
    from datetime import datetime, timedelta, timezone
    expiring = datetime.now(timezone.utc) + timedelta(days=5)
    connection_service.store(UID, "instagram", "tok-expiring", account_id="ig1", scopes=["basic"])
    for r in fake_tables["conns"].values():
        if r["platform"] == "instagram":
            r["token_expires_at"] = expiring.isoformat()

    class _Resp:
        status_code = 200
        @staticmethod
        def json():
            return {"access_token": "tok-fresh", "expires_in": 5184000}
        text = ""

    import httpx
    async def _fake_get(*a, **k):
        return _Resp()
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    res = await connection_service.refresh_instagram_if_expiring()
    assert res["refreshed"] == [str(UID)[:8]]
    fresh = [r for r in fake_tables["conns"].values() if r["platform"] == "instagram"][0]
    assert decrypt_token(fresh["access_token_encrypted"]) == "tok-fresh"
    new_exp = datetime.fromisoformat(fresh["token_expires_at"].replace("Z", "+00:00"))
    assert new_exp > datetime.now(timezone.utc) + timedelta(days=50)


@pytest.mark.asyncio
async def test_refresh_instagram_reports_failure_not_raise(fake_tables, monkeypatch):
    """A failing IG refresh must never crash the cron — reported, not raised."""
    from datetime import datetime, timedelta, timezone
    expiring = datetime.now(timezone.utc) + timedelta(days=3)
    connection_service.store(UID, "instagram", "tok-bad", account_id="ig1")
    for r in fake_tables["conns"].values():
        if r["platform"] == "instagram":
            r["token_expires_at"] = expiring.isoformat()

    import httpx
    class _FailResp:
        status_code = 400
        text = "OAuthException"
        @staticmethod
        def json():
            return {}
    async def _fake_get(*a, **k):
        return _FailResp()
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    res = await connection_service.refresh_instagram_if_expiring()
    assert res["status"] == "success"
    assert res["refreshed"] == []
    assert str(UID)[:8] in res["failed"]
