"""
Phase 9.7 tests — per-user platform_connections: crypto at rest, entitlement
gate (fail-closed), store/upsert/revoke, wizard overview (golden upsell),
OAuth state signing. FULLY isolated (fake tables — no live Supabase writes).
"""
import uuid

import pytest
from urllib.parse import parse_qs, urlparse
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


def test_threads_authorize_requires_entitlement(client_as_user, fake_tables):
    """Threads must have the same server-side paid gate as the Meta doors."""
    res = client_as_user.get("/api/threads/oauth/authorize")
    assert res.status_code == 403
    res_conn = client_as_user.get("/api/connections/threads/authorize")
    assert res_conn.status_code == 403



def test_authorize_returns_url_when_entitled(client, fake_tables, monkeypatch):
    """Admin session (conftest client) + granted entitlement → authorize URL."""
    me = client.get("/auth/me").json()
    _grant(me["user_id"], "platform:facebook")
    res = client.get("/api/connections/facebook/authorize")
    assert res.status_code == 200
    assert res.json()["authorize_url"].startswith("https://www.facebook.com/v26.0/dialog/oauth")
    assert "state=" in res.json()["authorize_url"]
    from src.config import settings
    monkeypatch.setattr(settings, "THREADS_APP_ID", "threads-test-app")
    _grant(me["user_id"], "platform:threads")
    res_th = client.get("/api/connections/threads/authorize")
    assert res_th.status_code == 200
    assert "threads.net" in res_th.json()["authorize_url"]
    assert "state=" in res_th.json()["authorize_url"]


def test_instagram_authorize_includes_verifiable_csrf_state(client, fake_tables, monkeypatch):
    """The callback rejects unsigned/missing state, so authorization must send it."""
    from src.config import settings
    monkeypatch.setattr(settings, "IG_APP_ID", "instagram-test-app")
    res = client.get("/api/connections/instagram/authorize")
    assert res.status_code == 200
    query = parse_qs(urlparse(res.json()["authorize_url"]).query)
    assert query["state"]
    assert conn_routes._verify_state(query["state"][0], "instagram")


@pytest.mark.parametrize("platform", ["facebook", "instagram"])
def test_invalid_oauth_callback_returns_to_customer_account(anon_client, platform):
    res = anon_client.get(
        f"/api/connections/{platform}/callback?code=unused&state=invalid",
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/account?connect_error=invalid_state"
