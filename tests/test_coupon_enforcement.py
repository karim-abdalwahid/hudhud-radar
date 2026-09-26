"""Coupon usage-limit enforcement tests (2026-09-26).

Pre-fix reality: coupons stored max_total_uses / max_uses_per_user /
expires_at, but NO code enforced any of them and NOTHING ever wrote a
coupon_redemptions row — so a coupon declared max_uses_per_user=1 could
be used infinitely many times. These tests lock in the enforcement:
  - checkout rejects expired / total-exhausted / per-user-exhausted coupons
  - quote preview simply stops applying an unusable coupon (no discount),
    while checkout is the hard 400 gate
  - the order.paid webhook records ONE redemption row per (coupon, user),
    which is what makes the limits durable going forward
"""
import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient

import src.modules.billing as billing_mod
from src.config import settings
from src.payments.polar import PolarGateway


def _iso(delta_minutes):
    now = datetime.now(timezone.utc)
    return (now + timedelta(minutes=delta_minutes)).isoformat()


# ---------------------------------------------------------------------
# Fake DB covering the coupon + redemption surfaces (checkout tests)
# ---------------------------------------------------------------------
@pytest.fixture
def fake_coupon_db(client, monkeypatch):
    me = client.get("/auth/me").json()
    users = {me.get("user_id"): {"id": me.get("user_id"), "email": me.get("email"),
                                 "role": me.get("role"), "is_active": True}}
    catalog = {
        "facebook": {"id": "c-fb", "platform": "facebook", "display_name": "Facebook Page",
                     "price_usd": 15.0, "is_available": True, "sort_order": 1},
    }
    coupons = {}
    redemptions = []

    def select(table, filters=None):
        f = filters or {}
        if table == "users":
            rows = list(users.values())
            if f.get("id"):
                rows = [r for r in rows if r["id"] == f["id"]]
            return rows
        if table == "platform_addons_catalog":
            return list(catalog.values())
        if table == "coupons":
            return [c for c in coupons.values()
                    if f.get("code") in (None, c.get("code"))]
        if table == "coupon_redemptions":
            rows = redemptions
            if f.get("coupon_id"):
                rows = [r for r in rows if r["coupon_id"] == f["coupon_id"]]
            if f.get("user_id"):
                rows = [r for r in rows if r["user_id"] == f["user_id"]]
            return rows
        return []

    def insert(table, data):
        if table == "coupons":
            coupons[data["code"]] = {**data}
            if "id" not in data:
                coupons[data["code"]]["id"] = str(uuid.uuid4())
            return coupons[data["code"]]
        if table == "coupon_redemptions":
            row = {"id": str(uuid.uuid4()), **data}
            redemptions.append(row)
            return row
        return data

    def update(table, rid, data):
        return data

    def delete(table, rid):
        return True

    monkeypatch.setattr(billing_mod.supabase_db, "select", select)
    monkeypatch.setattr(billing_mod.supabase_db, "insert", insert)
    monkeypatch.setattr(billing_mod.supabase_db, "update", update)
    monkeypatch.setattr(billing_mod.supabase_db, "delete", delete)
    return {"coupons": coupons, "redemptions": redemptions,
            "admin_id": me.get("user_id")}


def _create_coupon(client, code, **over):
    payload = {"code": code, "kind": "percent", "value": 10}
    payload.update(over)
    r = client.post("/api/admin/billing/coupons", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["coupon"]["id"]


# ---------------------------------------------------------------------
# Quote: unusable coupon must NOT be advertised as a discount
# ---------------------------------------------------------------------
def test_quote_does_not_apply_expired_coupon(client, fake_coupon_db):
    cid = _create_coupon(client, "QEXP", expires_at=_iso(-60))
    r = client.get("/api/billing/quote", params={"platforms": "facebook", "coupon": "QEXP"})
    assert r.status_code == 200
    body = r.json()
    assert body["coupon_discount_usd"] == 0
    assert body["total_usd"] == 15.0


def test_quote_does_not_apply_total_exhausted_coupon(client, fake_coupon_db):
    cid = _create_coupon(client, "QFULL", max_total_uses=1)
    fake_coupon_db["redemptions"].append(
        {"id": "r1", "coupon_id": cid, "user_id": "someone-else"})
    r = client.get("/api/billing/quote", params={"platforms": "facebook", "coupon": "QFULL"})
    assert r.status_code == 200
    assert r.json()["coupon_discount_usd"] == 0


def test_quote_applies_valid_coupon(client, fake_coupon_db):
    _create_coupon(client, "QVALID", max_total_uses=5)
    r = client.get("/api/billing/quote", params={"platforms": "facebook", "coupon": "QVALID"})
    assert r.status_code == 200
    assert r.json()["coupon_discount_usd"] > 0


# ---------------------------------------------------------------------
# Checkout: hard 400 gate on every limit
# ---------------------------------------------------------------------
def _checkout(client, code):
    return client.post("/api/billing/checkout",
                       json={"platforms": ["facebook"], "coupon": code})


def test_checkout_rejects_expired_coupon(client, fake_coupon_db):
    _create_coupon(client, "CEXP", expires_at=_iso(-60))
    r = _checkout(client, "CEXP")
    assert r.status_code == 400
    assert "انتهت" in r.json()["detail"]


def test_checkout_rejects_unknown_coupon(client, fake_coupon_db):
    r = _checkout(client, "NOEXIST")
    assert r.status_code == 400


def test_checkout_rejects_total_exhausted_coupon(client, fake_coupon_db):
    cid = _create_coupon(client, "CFULL", max_total_uses=1)
    fake_coupon_db["redemptions"].append(
        {"id": "r1", "coupon_id": cid, "user_id": "someone-else"})
    r = _checkout(client, "CFULL")
    assert r.status_code == 400
    assert "استهلاك" in r.json()["detail"]


def test_checkout_rejects_per_user_exhausted_coupon(client, fake_coupon_db):
    cid = _create_coupon(client, "CPER", max_uses_per_user=1)
    fake_coupon_db["redemptions"].append(
        {"id": "r1", "coupon_id": cid, "user_id": fake_coupon_db["admin_id"]})
    r = _checkout(client, "CPER")
    assert r.status_code == 400
    assert "استخدمت" in r.json()["detail"]


def test_checkout_allows_coupon_within_limits(client, fake_coupon_db, monkeypatch):
    from src.payments.registry import GATEWAYS
    _create_coupon(client, "COOK10", max_total_uses=5, max_uses_per_user=1)
    monkeypatch.setattr(GATEWAYS["polar"], "create_checkout",
                        lambda user, quote, return_url: {"checkout_url": "https://sandbox.polar.sh/x",
                                                         "provider_ref": "co_x"})
    r = _checkout(client, "COOK10")
    assert r.status_code == 200
    assert r.json()["quote"]["coupon_discount_usd"] > 0


# ---------------------------------------------------------------------
# Webhook: a PAID order records exactly one redemption per (coupon, user)
# ---------------------------------------------------------------------
def _make_sig(secret, body, ts=None):
    ts = ts or int(time.time())
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"msg_test.{ts}.".encode() + body
    sig = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
    return {"svix-id": "msg_test", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


@pytest.fixture
def fake_webhook_db(client, monkeypatch):
    from src.core.auth import user_store

    me = client.get("/auth/me").json()
    users, ent, subs, events = {}, {}, {}, []
    coupons, redemptions = {}, []

    def select(table, filters=None):
        f = filters or {}
        if table == "users":
            rows = list(users.values())
            if f.get("id"):
                rows = [r for r in rows if r["id"] == f["id"]]
            return rows
        if table == "user_entitlements":
            rows = list(ent.values())
            if f.get("user_id"):
                rows = [r for r in rows if r["user_id"] == f["user_id"]]
            if f.get("entitlement"):
                rows = [r for r in rows if r["entitlement"] == f["entitlement"]]
            return rows
        if table == "user_subscriptions":
            uid = f.get("user_id")
            return [subs[uid]] if uid in subs else []
        if table == "payment_events":
            return events
        if table == "coupons":
            return [c for c in coupons.values()
                    if f.get("code") in (None, c.get("code"))]
        if table == "coupon_redemptions":
            rows = redemptions
            if f.get("coupon_id"):
                rows = [r for r in rows if r["coupon_id"] == f["coupon_id"]]
            if f.get("user_id"):
                rows = [r for r in rows if r["user_id"] == f["user_id"]]
            return rows
        return []

    def insert(table, data):
        if table == "user_entitlements":
            rid = f"e{len(ent)+1}"
            ent[rid] = {"id": rid, **data}
            return ent[rid]
        if table == "user_subscriptions":
            subs[data["user_id"]] = {"id": f"sub-{data['user_id'][:8]}", **data}
            return subs[data["user_id"]]
        if table == "payment_events":
            events.append(data)
            return data
        if table == "coupons":
            coupons[data["code"]] = {**data}
            if "id" not in data:
                coupons[data["code"]]["id"] = str(uuid.uuid4())
            return coupons[data["code"]]
        if table == "coupon_redemptions":
            row = {"id": str(uuid.uuid4()), **data}
            redemptions.append(row)
            return row
        return data

    def update(table, rid, data):
        if table == "user_entitlements" and rid in ent:
            ent[rid].update(data)
            return ent[rid]
        if table == "user_subscriptions":
            for s in subs.values():
                if s.get("id") == rid or s.get("user_id") == rid:
                    s.update(data)
                    return s
            return data
        return data

    def delete(table, rid):
        return True

    monkeypatch.setattr(billing_mod.supabase_db, "select", select)
    monkeypatch.setattr(billing_mod.supabase_db, "insert", insert)
    monkeypatch.setattr(billing_mod.supabase_db, "update", update)
    monkeypatch.setattr(billing_mod.supabase_db, "delete", delete)

    def register(email):
        TestClient(client.app).post("/auth/register", json={
            "email": email, "password": "StrongPass#1", "terms_accepted": True})
        u = user_store.get_by_email(email)
        users[u["id"]] = {**u}
        return u

    return {"users": users, "coupons": coupons, "redemptions": redemptions,
            "register": register}


@pytest.fixture
def webhook_env(monkeypatch):
    monkeypatch.setattr(settings, "POLAR_ACCESS_TOKEN", "polar_test_token")
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET",
                        base64.b64encode(b"sandbox-secret").decode())


def _order_paid(coupon_code, email, platforms, event_id):
    meta = {"user_id": "u", "platforms": platforms}
    if coupon_code:
        meta["coupon_code"] = coupon_code
    return {"type": "order.paid", "id": event_id,
            "data": {"customer": {"email": email}, "metadata": meta}}


def test_webhook_order_paid_with_coupon_records_redemption(client, webhook_env, fake_webhook_db):
    u = fake_webhook_db["register"](f"red_{uuid.uuid4().hex[:6]}@hudhud.test")
    r = client.post("/api/admin/billing/coupons", json={
        "code": "REDEEM10", "kind": "percent", "value": 10, "max_total_uses": 3})
    assert r.status_code == 200, r.text
    body = json.dumps(_order_paid("REDEEM10", u["email"], ["facebook"], "evt-red-1")).encode()
    res = client.post("/api/payments/webhook/polar", content=body,
                      headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert res.status_code == 200
    rows = [x for x in fake_webhook_db["redemptions"] if x["user_id"] == u["id"]]
    assert len(rows) == 1


def test_webhook_does_not_duplicate_redemption_for_same_user(client, webhook_env, fake_webhook_db):
    u = fake_webhook_db["register"](f"red2_{uuid.uuid4().hex[:6]}@hudhud.test")
    client.post("/api/admin/billing/coupons", json={
        "code": "REDEEM11", "kind": "percent", "value": 10, "max_total_uses": 3})
    body = json.dumps(_order_paid("REDEEM11", u["email"], ["facebook"], "evt-red-2")).encode()
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body)
    r1 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r1.json()["status"] == "received"
    r2 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r2.json()["status"] == "duplicate_ignored"
    rows = [x for x in fake_webhook_db["redemptions"] if x["user_id"] == u["id"]]
    assert len(rows) == 1


def test_webhook_without_coupon_records_nothing(client, webhook_env, fake_webhook_db):
    u = fake_webhook_db["register"](f"red3_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_order_paid(None, u["email"], ["facebook"], "evt-red-3")).encode()
    res = client.post("/api/payments/webhook/polar", content=body,
                      headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert res.status_code == 200
    assert fake_webhook_db["redemptions"] == []


# ---------------------------------------------------------------------
# checkout metadata carries coupon_code so the webhook can identify it
# ---------------------------------------------------------------------
def test_create_checkout_places_coupon_code_in_metadata(monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_token", lambda: "test-token")
    monkeypatch.setattr(g, "_product_ids", lambda: {"facebook": "prod_fb"})
    captured = {}

    class FakeResp:
        status_code = 201

        def json(self):
            return {"url": "https://sandbox.polar.sh/c", "id": "co_c"}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers, json):
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr("src.payments.polar.httpx.Client", lambda **_k: FakeClient())
    quote = {"platforms": ["facebook"], "coupon_code": "SAVE10",
             "coupon_discount_usd": 1.5, "coupon_polar_id": "pol_x", "total_usd": 13.5}
    g.create_checkout({"id": "u1", "email": "u1@x.com"}, quote, "https://app.test/success")
    assert captured["json"]["metadata"]["coupon_code"] == "SAVE10"