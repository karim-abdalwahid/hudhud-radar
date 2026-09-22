"""
Phase 9.2 — Polar gateway + webhook pipeline tests.
Covers: svix signature fail-closed, dedup of duplicate events, entitlement
sync from payment truth, canceled → revoke. Zero prod writes (fakes).
"""
import base64
import hashlib
import hmac
import json
import time
import uuid

import pytest
from starlette.testclient import TestClient

import src.modules.billing as billing_mod
from src.config import settings
from src.payments.polar import PolarGateway


def _make_sig(secret: str, body: bytes, ts: int | None = None):
    ts = ts or int(time.time())
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"msg_test.{ts}.".encode() + body
    sig = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
    return {"svix-id": "msg_test", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


def _event_payload(event_id, event_type, email, platforms, sub_ref="sub_1"):
    return {
        "type": event_type, "id": event_id,
        "data": {
            "customer": {"email": email},
            "metadata": {"platforms": platforms},
            "subscription_id": sub_ref,
        },
    }


@pytest.fixture
def polar_env(monkeypatch):
    monkeypatch.setattr(settings, "POLAR_ACCESS_TOKEN", "polar_test_token")
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET", base64.b64encode(b"sandbox-secret").decode())


@pytest.fixture
def fake_billing(client, monkeypatch):
    """Same isolation pattern as test_billing.py (users/ent/subs + events)."""
    from src.core.auth import user_store

    me = client.get("/auth/me").json()
    users = {me["user_id"]: {"id": me["user_id"], "email": me.get("email"),
                             "role": me.get("role"), "is_active": True}}
    ent, subs, events = {}, {}, []
    seen_emails = {me.get("email", "").lower(): me["user_id"]}

    def select(table, filters=None):
        f = filters or {}
        if table == "users":
            rows = list(users.values())
            if f.get("id"): rows = [r for r in rows if r["id"] == f["id"]]
            return rows
        if table == "user_entitlements":
            rows = list(ent.values())
            if f.get("user_id"): rows = [r for r in rows if r["user_id"] == f["user_id"]]
            if f.get("entitlement"): rows = [r for r in rows if r["entitlement"] == f["entitlement"]]
            return rows
        if table == "user_subscriptions":
            uid = f.get("user_id")
            return [subs[uid]] if uid in subs else []
        if table == "payment_events":
            return events
        return []

    def insert(table, data):
        if table == "user_entitlements":
            rid = f"e{len(ent)+1}"
            ent[rid] = {"id": rid, **data}
            return ent[rid]
        if table == "user_subscriptions":
            subs[data["user_id"]] = {**data}
            return subs[data["user_id"]]
        if table == "payment_events":
            events.append(data)
            return data
        return data

    def update(table, rid, data):
        if table == "user_entitlements" and rid in ent:
            ent[rid].update(data); return ent[rid]
        if table == "user_subscriptions":
            return data
        return data

    def delete(table, rid):
        ent.pop(rid, None)
        return True

    monkeypatch.setattr(billing_mod.supabase_db, "select", select)
    monkeypatch.setattr(billing_mod.supabase_db, "insert", insert)
    monkeypatch.setattr(billing_mod.supabase_db, "update", update)
    monkeypatch.setattr(billing_mod.supabase_db, "delete", delete)
    from src.core import auth as _auth_mod
    _real_get_by_email = _auth_mod.user_store.get_by_email

    def _patched_get_by_email(email):
        e = (email or "").strip().lower()
        if e in seen_emails:
            return {"id": seen_emails[e]}
        return _real_get_by_email(email)
    monkeypatch.setattr("src.core.auth.user_store.get_by_email", _patched_get_by_email)

    def register(email):
        TestClient(client.app).post("/auth/register", json={
            "email": email, "password": "StrongPass#1", "terms_accepted": True})
        u = user_store.get_by_email(email)
        users[u["id"]] = {**u}
        seen_emails[email.lower()] = u["id"]
        return u

    return {"users": users, "ent": ent, "subs": subs, "register": register}


def test_webhook_invalid_signature_rejected(client: TestClient, polar_env, fake_billing):
    body = json.dumps(_event_payload("evt-1", "order.paid", "x@test.com", ["facebook"])).encode()
    headers = _make_sig(base64.b64encode(b"WRONG-SECRET").decode(), body)
    r = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r.status_code == 400
    assert fake_billing["ent"] == {}          # nothing granted


def test_webhook_missing_secret_rejected(client: TestClient, monkeypatch, fake_billing):
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET", None)
    body = json.dumps(_event_payload("evt-2", "order.paid", "x@test.com", ["facebook"])).encode()
    headers = _make_sig(base64.b64encode(b"anything").decode(), body)
    r = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r.status_code == 400


def test_webhook_valid_signature_activates_entitlements(client: TestClient, polar_env, fake_billing):
    u = fake_billing["register"](f"paid_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_event_payload("evt-ok-1", "subscription.active", u["email"],
                                     ["facebook", "instagram"])).encode()
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body)
    r = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r.status_code == 200
    svc = PolarGateway()
    from src.modules.billing.services import entitlement_service
    assert set(entitlement_service.connected_platforms(u["id"])) == {"facebook", "instagram"}
    assert fake_billing["subs"][u["id"]]["status"] == "active"


def test_webhook_duplicate_event_ignored(client: TestClient, polar_env, fake_billing):
    u = fake_billing["register"](f"dup_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_event_payload("evt-dup", "subscription.active", u["email"],
                                     ["facebook"])).encode()
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body)
    r1 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r1.json()["status"] == "received"
    # same event id again → duplicate ignored, no double effects
    ent_before = dict(fake_billing["ent"])
    r2 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r2.json()["status"] == "duplicate_ignored"
    assert fake_billing["ent"] == ent_before


def test_webhook_canceled_revokes_platforms(client: TestClient, polar_env, fake_billing):
    u = fake_billing["register"](f"cancel_{uuid.uuid4().hex[:6]}@hudhud.test")
    from src.modules.billing.services import entitlement_service
    entitlement_service.sync_from_platforms(u["id"], ["facebook", "threads"])
    body = json.dumps(_event_payload("evt-cancel", "subscription.canceled", u["email"], [])).encode()
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body)
    r = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r.status_code == 200
    assert entitlement_service.connected_platforms(u["id"]) == []
    assert fake_billing["subs"][u["id"]]["status"] == "canceled"


def test_webhook_stale_timestamp_rejected(client: TestClient, polar_env, fake_billing):
    body = json.dumps(_event_payload("evt-old", "order.paid", "x@test.com", ["facebook"])).encode()
    old_ts = int(time.time()) - 3600  # 1 hour ago
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body, ts=old_ts)
    r = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r.status_code == 400


def test_unknown_provider_404(client: TestClient):
    r = client.post("/api/payments/webhook/notagateway", content=b"{}", headers={})
    assert r.status_code == 404


def test_parse_event_resolves_platforms_from_product_id(client, polar_env, monkeypatch):
    """checkout.created carries empty metadata — platforms resolved from
    product_id via the mapping (real Polar webhook behavior)."""
    g = PolarGateway()
    monkeypatch.setattr(g, "_product_ids", lambda: {
        "facebook": "f814fbcb-94bd-41fd-b020-cf1586518ecd",
    })
    payload = _event_payload("evt-prod", "checkout.created", "x@test.com", [])
    payload["data"]["product_id"] = "f814fbcb-94bd-41fd-b020-cf1586518ecd"  # facebook mapping
    parsed = g.parse_event({}, payload)
    assert parsed["platforms"] == ["facebook"]


def test_parse_event_products_array_resolution(client, polar_env, monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_product_ids", lambda: {
        "instagram": "04509b5b-b2f5-4f78-87ba-4f11a3d8f712",
        "threads": "8fb7d645-f441-45e5-a178-e2c5fe72fccb",
    })
    payload = _event_payload("evt-prod2", "order.paid", "x@test.com", [])
    payload["data"]["products"] = [
        {"id": "04509b5b-b2f5-4f78-87ba-4f11a3d8f712"},   # instagram
        {"id": "8fb7d645-f441-45e5-a178-e2c5fe72fccb"},   # threads
    ]
    parsed = g.parse_event({}, payload)
    assert set(parsed["platforms"]) == {"instagram", "threads"}


def test_parse_event_identifies_trial_products_without_granting_paid_platforms(client, polar_env, monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_product_ids", lambda: {
        "trial-facebook": "1719ac1c-36f9-4956-ab06-2ab29f44ffc4",
    })
    payload = _event_payload("evt-trial", "checkout.created", "x@test.com", [])
    payload["data"]["product_id"] = "1719ac1c-36f9-4956-ab06-2ab29f44ffc4"  # trial-facebook
    parsed = g.parse_event({}, payload)
    assert parsed["platforms"] == []  # trial products don't grant paid platforms directly
    assert parsed["is_trial"] is True


def test_trial_webhook_starts_single_local_trial(client, polar_env, fake_billing):
    u = fake_billing["register"](f"trial_{uuid.uuid4().hex[:6]}@hudhud.test")
    payload = _event_payload("evt-trial-start", "subscription.active", u["email"],
                             ["facebook", "instagram", "threads"])
    payload["data"]["metadata"]["trial"] = "true"
    payload["data"]["status"] = "trialing"
    body = json.dumps(payload).encode()
    response = client.post("/api/payments/webhook/polar", content=body,
                           headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert response.status_code == 200
    from src.modules.billing.services import entitlement_service
    status = entitlement_service.subscription_status(u["id"])
    assert status["status"] == "trialing"
    assert set(status["platforms"]) == {"facebook", "instagram", "threads"}
    assert entitlement_service.can_start_trial(u["id"]) is False


def test_trial_product_converted_to_active_is_not_started_as_a_second_trial(client, polar_env, fake_billing):
    g = PolarGateway()
    payload = _event_payload("evt-trial-converted", "subscription.active", "x@test.com", [])
    payload["data"]["metadata"]["trial"] = "true"
    payload["data"]["status"] = "active"
    parsed = g.parse_event({}, payload)
    assert parsed["is_trial"] is True
    assert parsed["subscription_status"] == "active"


def test_trial_checkout_never_falls_back_to_paid_products(monkeypatch):
    gateway = PolarGateway()
    monkeypatch.setattr(gateway, "_token", lambda: "polar-test-token")
    monkeypatch.setattr(gateway, "_product_ids", lambda: {"facebook": "paid-facebook"})
    with pytest.raises(RuntimeError, match="التجربة المجانية غير مهيأة"):
        gateway.start_trial({"id": "u1", "email": "u1@example.test"}, "https://example.test/success")
