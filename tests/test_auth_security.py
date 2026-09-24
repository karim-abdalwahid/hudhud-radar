"""
Security tests for the Authentication & Authorization system (Phase 1 of the
Master Repair Plan 017) and webhook idempotency (dedup).
"""
import pytest
from starlette.testclient import TestClient

from src.core.auth import hash_password, verify_password, create_session_token, verify_session_token
from src.core.event_dedup import EventDeduplicator


# --------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------
def test_password_hash_and_verify():
    h = hash_password("S3curePass!2026")
    assert h.startswith("pbkdf2_sha256$")
    assert verify_password("S3curePass!2026", h) is True
    assert verify_password("wrong-password", h) is False
    # Two hashes of the same password differ (unique salts)
    assert hash_password("S3curePass!2026") != h


def test_password_verify_malformed_hash():
    assert verify_password("anything", "not-a-valid-hash") is False
    assert verify_password("anything", "") is False


# --------------------------------------------------------------------
# Session tokens
# --------------------------------------------------------------------
def test_session_token_roundtrip():
    token = create_session_token("user-123", "admin", "owner@test.com")
    payload = verify_session_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_session_token_tamper_rejected():
    token = create_session_token("user-123", "admin", "owner@test.com")
    tampered = token[:-4] + "AAAA"
    assert verify_session_token(tampered) is None
    assert verify_session_token("garbage.token") is None
    assert verify_session_token("") is None


def test_session_token_wrong_secret_rejected(monkeypatch):
    from src.config import settings
    token = create_session_token("u1", "admin", "a@b.com")
    old = settings.SECRET_KEY
    settings.SECRET_KEY = "another-secret-key-totally-different"
    try:
        assert verify_session_token(token) is None
    finally:
        settings.SECRET_KEY = old


# --------------------------------------------------------------------
# Registration & Login flows (isolated in-memory store via conftest)
# NOTE: tests that use the `admin_creds`/`client` fixtures must come first
# alphabetically-per-module is NOT guaranteed, so the admin bootstrap fixture
# is requested explicitly wherever admin precedence matters.
# --------------------------------------------------------------------
def test_register_login_logout_flow(anon_client, admin_creds):
    """Explicitly requests admin_creds so the admin user is always created FIRST."""
    import uuid
    email = f"flow_user_{uuid.uuid4().hex[:6]}@hudhud.test"
    reg = anon_client.post("/auth/register", json={
        "email": email, "password": "StrongPass#1", "terms_accepted": True, "phone": "+201234567890", "full_name": "Flow User", "terms_accepted": True,
    })
    assert reg.status_code == 200
    assert reg.json()["status"] == "success"
    assert reg.json()["role"] == "user"  # admin already exists

    # Session cookie set
    assert "hudhud_session" in anon_client.cookies

    # Me endpoint reflects the session
    me = anon_client.get("/auth/me").json()
    assert me["authenticated"] is True
    assert me["email"] == email

    # Logout clears session
    anon_client.post("/auth/logout")
    me_after = anon_client.get("/auth/me").json()
    assert me_after["authenticated"] is False


def test_register_duplicate_email_rejected(anon_client, admin_creds):
    res = anon_client.post("/auth/register", json={
        "email": admin_creds["email"], "password": "StrongPass#1", "terms_accepted": True,
    })
    assert res.status_code == 400
    assert "مسجل" in res.json()["detail"]


def test_register_short_password_rejected(anon_client):
    res = anon_client.post("/auth/register", json={
        "email": "shortpw@hudhud.test", "password": "123",
    })
    assert res.status_code == 400


def test_login_wrong_password_rejected(anon_client, admin_creds):
    res = anon_client.post("/auth/login", json={
        "email": admin_creds["email"], "password": "WrongPassword!",
    })
    assert res.status_code == 401


def test_second_user_is_not_admin(anon_client):
    # Register a fresh second user (admin already exists in session scope)
    import uuid
    email = f"user_{uuid.uuid4().hex[:6]}@hudhud.test"
    res = anon_client.post("/auth/register", json={
        "email": email, "password": "StrongPass#1", "terms_accepted": True,
    })
    assert res.status_code == 200
    assert res.json()["role"] == "user"


# --------------------------------------------------------------------
# Route protection
# --------------------------------------------------------------------
def test_protected_page_redirects_anonymous(anon_client):
    res = anon_client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 303
    assert "/login" in res.headers["location"]


def test_protected_api_returns_401_anonymous(anon_client):
    res = anon_client.get("/api/leads")
    assert res.status_code == 401


def test_public_routes_open_anonymous(anon_client):
    assert anon_client.get("/").status_code == 200
    assert anon_client.get("/login").status_code == 200
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/privacy").status_code == 200
    assert anon_client.get("/data-deletion").status_code == 200


def test_tenant_meta_config_requires_a_real_connection_payload(anon_client, admin_creds):
    # Register a plain user
    import uuid
    email = f"plain_{uuid.uuid4().hex[:6]}@hudhud.test"
    anon_client.post("/auth/register", json={"email": email, "password": "StrongPass#1", "terms_accepted": True})

    # Manual connection setup is tenant-scoped, so a regular user may reach
    # it, but cannot create a connection without the required page token.
    res = anon_client.post("/api/meta/configure", json={"page_id": "123456"})
    assert res.status_code == 400

    # Try admin-only page
    page = anon_client.get("/settings", follow_redirects=False)
    assert page.status_code == 403


# --------------------------------------------------------------------
# Webhook event deduplication
# --------------------------------------------------------------------
def test_event_dedup_claim_logic():
    d = EventDeduplicator()
    assert d.claim("evt-1", "message") is True
    assert d.claim("evt-1", "message") is False  # duplicate blocked
    assert d.claim("evt-2", "comment") is True
    assert d.claim("", "message") is False  # empty keys never claimed
    assert d.claim("same-event", "message", scope="tenant-a") is True
    assert d.claim("same-event", "message", scope="tenant-b") is True
    assert d.claim("same-event", "message", scope="tenant-a") is False


def test_event_dedup_memory_limit():
    d = EventDeduplicator()
    for i in range(5010):
        d.claim(f"evt-{i}", "message")
    # Oldest keys evicted, newest retained
    assert d.claim("evt-0") is True  # evicted -> claimable again
    assert d.already_processed("evt-5009") is True


def test_webhook_duplicate_payload_processed_once(client, monkeypatch):
    """Full-loop idempotency: same HMAC-signed webhook payload only queues once."""
    import hashlib
    import hmac as hmac_mod
    import json
    from src.config import settings

    # Prevent the orchestrator from actually processing (live Meta/DB calls in tests).
    # Patch the INSTANCE attributes (main.py holds references to singletons).
    import src.agent.orchestrator as orch_mod
    import src.automations.service as auto_mod

    async def _noop(ev):
        return {}
    orig_orch = orch_mod.agent_orchestrator.process_incoming_message_event
    orig_auto = auto_mod.automations_service.process_comment_event
    from src.modules.connections.service import connection_service
    orig_owner = connection_service.owner_for_account
    orch_mod.agent_orchestrator.process_incoming_message_event = _noop
    auto_mod.automations_service.process_comment_event = lambda ev: None
    connection_service.owner_for_account = lambda platform, account_id: "tenant-webhook"
    try:
        payload = {
            "object": "instagram",
            "entry": [{
                "id": "17841459820747642",
                "time": 1725648000,
                "messaging": [{
                    "sender": {"id": "guest_777"},
                    "recipient": {"id": "17841459820747642"},
                    "timestamp": 1725648000123,
                    "message": {"mid": "dedup_test_mid_unique_001", "text": "مرحبا"},
                }],
            }],
        }
        raw = json.dumps(payload).encode("utf-8")
        secret = (settings.META_APP_SECRET or "dev-secret").encode("utf-8")
        sig = "sha256=" + hmac_mod.new(secret, raw, hashlib.sha256).hexdigest()

        r1 = client.post("/api/webhook/meta", content=raw,
                         headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
        assert r1.status_code == 200
        queued_first = r1.json()["events_queued"]

        r2 = client.post("/api/webhook/meta", content=raw,
                         headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
        assert r2.status_code == 200
        queued_second = r2.json()["events_queued"]
    finally:
        orch_mod.agent_orchestrator.process_incoming_message_event = orig_orch
        auto_mod.automations_service.process_comment_event = orig_auto
        connection_service.owner_for_account = orig_owner

    assert queued_first == 1
    assert queued_second == 0  # duplicate suppressed
