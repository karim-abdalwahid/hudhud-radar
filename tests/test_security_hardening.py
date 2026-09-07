"""
Security regression tests for the September 2026 hardening pass.
Covers: data-deletion fail-closed, cron fail-closed + constant-time, webhook
verify-token privacy + fail-closed HMAC, admin gates on debug/paid endpoints.
"""
import base64
import hashlib
import hmac as hmac_mod
import json

import pytest
from starlette.testclient import TestClient

from src.config import settings
from src.meta_api.webhooks import webhook_handler


# --------------------------------------------------------------------
# 1. Data-deletion: JSON branch removed (fail-closed)
# --------------------------------------------------------------------
def test_data_deletion_json_branch_rejected(client: TestClient):
    # Previously: unauthenticated JSON {email: ...} deleted users. Must 400 now.
    r = client.post("/api/data-deletion", json={"email": "victim@example.com"})
    assert r.status_code == 400
    assert "signed_request" in r.json()["error"]


def test_data_deletion_without_signed_request_rejected(client: TestClient):
    r = client.post("/api/data-deletion", data={"email": "victim@example.com"})
    assert r.status_code == 400


def test_data_deletion_bad_signature_rejected(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret-123")
    payload = base64.urlsafe_b64encode(json.dumps({"user_id": "u1"}).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac_mod.new(b"wrong-secret", payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    r = client.post("/api/data-deletion", data={"signed_request": f"{sig}.{payload}"})
    assert r.status_code == 403


def test_data_deletion_valid_signature_accepted(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret-123")
    monkeypatch.setattr("src.meta_api.compliance_pages.supabase_db", _FakeDB(),)
    payload = base64.urlsafe_b64encode(json.dumps({"user_id": "meta-scoped-1"}).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(hmac_mod.new(b"test-secret-123", payload.encode(), hashlib.sha256).digest()).decode().rstrip("=")
    r = client.post("/api/data-deletion", data={"signed_request": f"{sig}.{payload}"})
    assert r.status_code == 200
    body = r.json()
    assert body["confirmation_code"]
    assert body["url"].startswith(settings.APP_BASE_URL)


class _FakeDB:
    def delete(self, *a, **kw):
        return True
    def select(self, *a, **kw):
        return []
    def insert(self, *a, **kw):
        return {"id": "log1"}


# --------------------------------------------------------------------
# 2. Webhooks: constant-time verify token + privacy + fail-closed HMAC
# --------------------------------------------------------------------
def test_webhook_verify_token_accepted(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "tok-abc")
    r = client.get("/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "tok-abc", "hub.challenge": "CH123"})
    assert r.status_code == 200
    assert r.text == "CH123"


def test_webhook_verify_wrong_token_rejected(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "META_WEBHOOK_VERIFY_TOKEN", "tok-abc")
    r = client.get("/webhooks/meta", params={"hub.mode": "subscribe", "hub.verify_token": "tok-wrong", "hub.challenge": "CH"})
    assert r.status_code == 403


def test_webhook_hmac_fail_closed_without_secret(monkeypatch):
    # Even in dev, no secret = reject (previously fail-open outside production)
    monkeypatch.setattr(settings, "META_APP_SECRET", None)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert webhook_handler.verify_signature(b"{}", "sha256=deadbeef") is False


def test_webhook_hmac_valid_signature(monkeypatch):
    monkeypatch.setattr(settings, "META_APP_SECRET", "sec-123")
    body = b'{"object":"page"}'
    sig = "sha256=" + hmac_mod.new(b"sec-123", body, hashlib.sha256).hexdigest()
    assert webhook_handler.verify_signature(body, sig) is True


# --------------------------------------------------------------------
# 3. Cron: fail-closed in production, constant-time, bad secret rejected
# --------------------------------------------------------------------
def test_cron_invalid_secret_rejected(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "real-secret")
    r = client.get("/api/cron/insights-sync", params={"key": "wrong-secret"})
    assert r.status_code == 401


def test_cron_correct_secret_via_query_allowed(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "real-secret")
    r = client.get("/api/cron/insights-sync", params={"key": "real-secret"})
    assert r.status_code == 200


def test_cron_fail_closed_in_production(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", None)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    r = client.get("/api/cron/insights-sync")
    assert r.status_code == 503


# --------------------------------------------------------------------
# 4. Admin gates: debug endpoints + paid external actions
# --------------------------------------------------------------------
def test_secrets_check_requires_admin(client_as_user: TestClient):
    r = client_as_user.get("/api/debug/secrets-check")
    assert r.status_code == 403


def test_llm_status_requires_admin(client_as_user: TestClient):
    r = client_as_user.get("/api/debug/llm-status")
    assert r.status_code == 403


def test_threads_publish_requires_admin(client_as_user: TestClient):
    r = client_as_user.post("/api/threads/publish", json={"text": "hi"})
    assert r.status_code == 403


def test_marketing_sync_requires_admin(client_as_user: TestClient):
    assert client_as_user.post("/api/marketing/sync-leads").status_code == 403
    assert client_as_user.post("/api/marketing/sync-campaigns").status_code == 403


def test_inbox_send_message_requires_admin(client_as_user: TestClient):
    r = client_as_user.post("/api/inbox/conversations/some-lead/send-message", json={"text": "hi"})
    assert r.status_code == 403


def test_admin_alerts_requires_admin(client_as_user: TestClient):
    assert client_as_user.get("/api/admin/alerts").status_code == 403


def test_admin_endpoints_allow_admin(client: TestClient):
    # client fixture = admin session
    assert client.get("/api/admin/alerts").status_code == 200


# --------------------------------------------------------------------
# 5. Info leaks removed
# --------------------------------------------------------------------
def test_meta_status_has_no_supabase_url(client_as_user: TestClient):
    r = client_as_user.get("/api/meta/status")
    assert r.status_code == 200
    assert "supabase_url" not in r.json()
