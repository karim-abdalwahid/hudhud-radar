"""Tests: self-serve AI-credit pack purchases.

This feature required fixing a real, pre-existing bug in parse_event():
order.paid was unconditionally mapped to "subscription_activated", which
would have made a one-time credit purchase get processed as if it were a
platform subscription activation. Section 2 below is the regression test
for that fix; section 2 also proves the FIX is additive-only — every event
shape that previously mapped to subscription_activated still does.
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
from src.modules.billing.usage import CREDIT_PACKS
from src.payments.polar import PolarGateway


# ─────────────────────────────────────────────────────────────────────────
# 1. UsageService.grant_purchased_credits — genuinely additive
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture
def fake_usage_db(monkeypatch):
    users = {}

    class FakeDB:
        def select(self, table, filters=None):
            if table != "users":
                return []
            rows = list(users.values())
            f = filters or {}
            return [r for r in rows if r["id"] == f["id"]] if f.get("id") else rows

        def update(self, table, rid, data):
            if table == "users" and rid in users:
                users[rid].update(data)
                return users[rid]
            return None

    db = FakeDB()
    from src.core.supabase_client import supabase_db as real_db
    monkeypatch.setattr(real_db, "select", db.select)
    monkeypatch.setattr(real_db, "update", db.update)
    return users


def test_grant_purchased_credits_adds_on_top_of_existing_balance(fake_usage_db):
    from src.modules.billing.usage import usage_service
    fake_usage_db["u1"] = {"id": "u1", "ai_credits": 400}
    usage_service.grant_purchased_credits("u1", 2000)
    assert fake_usage_db["u1"]["ai_credits"] == 2400  # additive, not clamped to 2000


def test_grant_purchased_credits_ignores_non_positive_amounts(fake_usage_db):
    from src.modules.billing.usage import usage_service
    fake_usage_db["u1"] = {"id": "u1", "ai_credits": 400}
    usage_service.grant_purchased_credits("u1", 0)
    usage_service.grant_purchased_credits("u1", -50)
    assert fake_usage_db["u1"]["ai_credits"] == 400


def test_grant_purchased_credits_never_raises_for_unknown_user(fake_usage_db):
    from src.modules.billing.usage import usage_service
    usage_service.grant_purchased_credits("ghost-user", 500)  # must not raise


def test_grant_purchased_credits_never_raises_on_db_failure(fake_usage_db, monkeypatch):
    from src.modules.billing.usage import usage_service

    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr("src.core.supabase_client.supabase_db.select", boom)
    usage_service.grant_purchased_credits("u1", 500)  # must not raise


# ─────────────────────────────────────────────────────────────────────────
# 2. parse_event kind routing — the actual bug fix
# ─────────────────────────────────────────────────────────────────────────
def _order_paid_payload(event_id, email, metadata):
    return {"type": "order.paid", "id": event_id,
            "data": {"customer": {"email": email}, "metadata": metadata}}


def test_order_paid_with_credit_pack_metadata_routes_to_order_paid_kind():
    g = PolarGateway()
    parsed = g.parse_event({}, _order_paid_payload(
        "evt-1", "x@test.com", {"user_id": "u1", "credit_pack": "credits_500"}))
    assert parsed["kind"] == "order_paid"
    assert parsed["credit_pack"] == "credits_500"


def test_order_paid_without_credit_pack_metadata_still_means_subscription_activated():
    """The backward-compat guarantee: every existing subscription-checkout
    order.paid event (no credit_pack key at all) must keep working exactly
    as before this feature existed."""
    g = PolarGateway()
    parsed = g.parse_event({}, _order_paid_payload(
        "evt-2", "x@test.com", {"user_id": "u1", "platforms": ["facebook"]}))
    assert parsed["kind"] == "subscription_activated"
    assert parsed["credit_pack"] is None


def test_order_paid_with_empty_string_credit_pack_is_not_treated_as_a_purchase():
    g = PolarGateway()
    parsed = g.parse_event({}, _order_paid_payload(
        "evt-3", "x@test.com", {"credit_pack": ""}))
    assert parsed["kind"] == "subscription_activated"  # falsy — same as absent


def test_subscription_active_event_type_is_unaffected_by_the_credit_pack_check():
    g = PolarGateway()
    payload = {"type": "subscription.active", "id": "evt-4",
               "data": {"customer": {"email": "x@test.com"},
                        "metadata": {"platforms": ["instagram"]}}}
    parsed = g.parse_event({}, payload)
    assert parsed["kind"] == "subscription_activated"


# ─────────────────────────────────────────────────────────────────────────
# 3. create_credits_checkout
# ─────────────────────────────────────────────────────────────────────────
def test_create_credits_checkout_builds_a_single_product_one_time_payload(monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_token", lambda: "test-token")
    monkeypatch.setattr(g, "_credit_pack_product_ids", lambda: {"credits_500": "prod_credits_500"})
    captured = {}

    class FakeResp:
        status_code = 201
        def json(self):
            return {"url": "https://sandbox.polar.sh/checkout/abc", "id": "co_abc"}

    class FakeClient:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, headers, json):
            captured["url"], captured["json"] = url, json
            return FakeResp()

    monkeypatch.setattr("src.payments.polar.httpx.Client", lambda **_k: FakeClient())
    result = g.create_credits_checkout({"id": "u1", "email": "u1@x.com"}, "credits_500",
                                        "https://app.test/billing/success?type=credits")
    assert result == {"checkout_url": "https://sandbox.polar.sh/checkout/abc", "provider_ref": "co_abc"}
    assert captured["json"]["products"] == ["prod_credits_500"]
    assert captured["json"]["metadata"]["credit_pack"] == "credits_500"
    assert "platforms" not in captured["json"]["metadata"]  # one-time, not a platform subscription


def test_create_credits_checkout_raises_clearly_when_pack_unmapped(monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_token", lambda: "test-token")
    monkeypatch.setattr(g, "_credit_pack_product_ids", lambda: {})
    with pytest.raises(RuntimeError, match="لا يوجد منتج Polar مربوط لحزمة الرصيد"):
        g.create_credits_checkout({"id": "u1", "email": "u1@x.com"}, "credits_500", "https://app.test/success")


def test_create_credits_checkout_requires_a_token(monkeypatch):
    g = PolarGateway()
    monkeypatch.setattr(g, "_token", lambda: "")
    with pytest.raises(RuntimeError, match="POLAR_ACCESS_TOKEN"):
        g.create_credits_checkout({"id": "u1", "email": "u1@x.com"}, "credits_500", "https://app.test/success")


# ─────────────────────────────────────────────────────────────────────────
# 4. Routes: catalog + checkout creation
# ─────────────────────────────────────────────────────────────────────────
def test_credit_packs_catalog_route_returns_all_packs(client: TestClient):
    res = client.get("/api/billing/credits/packs")
    assert res.status_code == 200
    packs = {p["pack"]: p for p in res.json()["packs"]}
    assert set(packs) == set(CREDIT_PACKS)
    for key, credits in CREDIT_PACKS.items():
        assert packs[key]["credits"] == credits
        assert packs[key]["price_usd"] > 0  # coded fallback prices are non-zero


def test_credit_packs_catalog_requires_login():
    from src.main import app
    res = TestClient(app).get("/api/billing/credits/packs")
    assert res.status_code in (401, 303)


def test_credits_checkout_rejects_unknown_pack(client: TestClient):
    res = client.post("/api/billing/credits/checkout", json={"pack": "credits_999999"})
    assert res.status_code == 400


def test_credits_checkout_returns_checkout_url_for_a_valid_pack(client: TestClient, monkeypatch):
    from src.payments.registry import GATEWAYS

    monkeypatch.setattr(GATEWAYS["polar"], "create_credits_checkout",
                        lambda user, pack, return_url: {"checkout_url": "https://sandbox.polar.sh/x",
                                                        "provider_ref": "co_x"})
    res = client.post("/api/billing/credits/checkout", json={"pack": "credits_2000"})
    assert res.status_code == 200
    body = res.json()
    assert body["checkout_url"] == "https://sandbox.polar.sh/x"
    assert body["pack"] == "credits_2000"


def test_credits_checkout_surfaces_gateway_errors_as_502(client: TestClient, monkeypatch):
    from src.payments.registry import GATEWAYS

    def boom(*_a, **_k):
        raise RuntimeError("لا يوجد منتج Polar مربوط لحزمة الرصيد: credits_500")
    monkeypatch.setattr(GATEWAYS["polar"], "create_credits_checkout", boom)
    res = client.post("/api/billing/credits/checkout", json={"pack": "credits_500"})
    assert res.status_code == 502


# ─────────────────────────────────────────────────────────────────────────
# 5. Full webhook integration — signed request all the way to ai_credits
# ─────────────────────────────────────────────────────────────────────────
def _make_sig(secret, body, ts=None):
    ts = ts or int(time.time())
    secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"msg_test.{ts}.".encode() + body
    sig = base64.b64encode(hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
    return {"svix-id": "msg_test", "svix-timestamp": str(ts), "svix-signature": f"v1,{sig}"}


@pytest.fixture
def polar_env(monkeypatch):
    monkeypatch.setattr(settings, "POLAR_ACCESS_TOKEN", "polar_test_token")
    monkeypatch.setattr(settings, "POLAR_WEBHOOK_SECRET", base64.b64encode(b"sandbox-secret").decode())


@pytest.fixture
def fake_billing_with_credits(client, monkeypatch):
    """Same shape as test_payments.py's fake_billing, extended to persist
    ai_credits writes on the "users" table — needed here because that
    fixture's update() never touched "users" (nothing did, until this
    feature and the ai_credits gate before it).

    user_store (auth's real in-memory store) is left untouched: /auth/register
    already populates it correctly, and the webhook handler's target_user
    resolution calls it directly. Only supabase_db — the separate store that
    ai_credits/select("users", ...) reads from — needs a fake backing dict.
    """
    from src.core.auth import user_store

    users = {}

    def select(table, filters=None):
        f = filters or {}
        if table == "users":
            rows = list(users.values())
            return [r for r in rows if r["id"] == f["id"]] if f.get("id") else rows
        return []

    def update(table, rid, data):
        if table == "users" and rid in users:
            users[rid].update(data)
            return users[rid]
        return data

    def insert(table, data):
        return data  # payment_events — not asserted on here

    monkeypatch.setattr(billing_mod.supabase_db, "select", select)
    monkeypatch.setattr(billing_mod.supabase_db, "update", update)
    monkeypatch.setattr(billing_mod.supabase_db, "insert", insert)

    def register(email):
        TestClient(client.app).post("/auth/register", json={
            "email": email, "password": "StrongPass#1", "terms_accepted": True})
        u = user_store.get_by_email(email)
        users[u["id"]] = {"id": u["id"], "email": u["email"], "ai_credits": 0}
        return u

    return {"users": users, "register": register}


def test_webhook_order_paid_with_credit_pack_grants_credits(client, polar_env, fake_billing_with_credits):
    u = fake_billing_with_credits["register"](f"buyer_{uuid.uuid4().hex[:6]}@hudhud.test")
    fake_billing_with_credits["users"][u["id"]]["ai_credits"] = 100
    body = json.dumps(_order_paid_payload(
        "evt-buy-1", u["email"], {"user_id": u["id"], "credit_pack": "credits_2000"})).encode()
    res = client.post("/api/payments/webhook/polar", content=body,
                      headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert res.status_code == 200
    assert res.json()["kind"] == "order_paid"
    assert fake_billing_with_credits["users"][u["id"]]["ai_credits"] == 100 + CREDIT_PACKS["credits_2000"]


def test_webhook_order_paid_duplicate_event_id_grants_only_once(client, polar_env, fake_billing_with_credits):
    u = fake_billing_with_credits["register"](f"buyer_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_order_paid_payload(
        "evt-buy-dup", u["email"], {"user_id": u["id"], "credit_pack": "credits_500"})).encode()
    headers = _make_sig(settings.POLAR_WEBHOOK_SECRET, body)
    r1 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r1.json()["status"] == "received"
    r2 = client.post("/api/payments/webhook/polar", content=body, headers=headers)
    assert r2.json()["status"] == "duplicate_ignored"
    assert fake_billing_with_credits["users"][u["id"]]["ai_credits"] == CREDIT_PACKS["credits_500"]


def test_webhook_order_paid_with_unrecognized_pack_grants_nothing(client, polar_env, fake_billing_with_credits):
    u = fake_billing_with_credits["register"](f"buyer_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_order_paid_payload(
        "evt-buy-bad", u["email"], {"user_id": u["id"], "credit_pack": "not_a_real_pack"})).encode()
    res = client.post("/api/payments/webhook/polar", content=body,
                      headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert res.status_code == 200  # accepted, just nothing to apply
    assert fake_billing_with_credits["users"][u["id"]]["ai_credits"] == 0


def test_webhook_order_paid_without_credit_pack_does_not_touch_ai_credits(
        client, polar_env, fake_billing_with_credits):
    """Full-webhook proof of the backward-compat guarantee from section 2:
    a plain platform-subscription order.paid must not grant AI credits via
    the NEW order_paid branch (it goes through subscription_activated, which
    grants via grant_platform_credits instead — a different code path,
    already covered by test_payments.py)."""
    u = fake_billing_with_credits["register"](f"buyer_{uuid.uuid4().hex[:6]}@hudhud.test")
    body = json.dumps(_order_paid_payload(
        "evt-sub-1", u["email"], {"user_id": u["id"]})).encode()  # no credit_pack, no platforms
    res = client.post("/api/payments/webhook/polar", content=body,
                      headers=_make_sig(settings.POLAR_WEBHOOK_SECRET, body))
    assert res.status_code == 200
    assert res.json()["kind"] == "subscription_activated"


# ─────────────────────────────────────────────────────────────────────────
# 6. Pricing catalog + admin settings
# ─────────────────────────────────────────────────────────────────────────
def test_credit_pack_catalog_uses_coded_fallback_when_no_override(monkeypatch):
    from src.modules.billing.services import pricing_service, DEFAULT_CREDIT_PACK_PRICES_USD
    monkeypatch.setattr("src.modules.billing.services.supabase_db.get_setting", lambda *_a, **_k: None)
    catalog = {p["pack"]: p for p in pricing_service.credit_pack_catalog()}
    for key, price in DEFAULT_CREDIT_PACK_PRICES_USD.items():
        assert catalog[key]["price_usd"] == price


def test_credit_pack_catalog_respects_admin_override(monkeypatch):
    from src.modules.billing.services import pricing_service
    monkeypatch.setattr("src.modules.billing.services.supabase_db.get_setting",
                        lambda key, *_a, **_k: {"credits_500": 4.99} if key == "credit_packs_pricing" else None)
    catalog = {p["pack"]: p for p in pricing_service.credit_pack_catalog()}
    assert catalog["credits_500"]["price_usd"] == 4.99
    assert catalog["credits_2000"]["price_usd"] > 0  # unaffected packs keep their fallback


def test_admin_can_set_credit_pack_settings(client: TestClient):
    res = client.put("/api/admin/site-settings", json={
        "polar_credit_pack_ids": {"credits_500": "prod_abc"},
        "credit_packs_pricing": {"credits_500": 7.99},
    })
    assert res.status_code == 200
    assert set(res.json()["updated"]) == {"polar_credit_pack_ids", "credit_packs_pricing"}


def test_admin_can_now_set_polar_product_ids_too(client: TestClient):
    """Regression test for a pre-existing bug found while building this
    feature: polar_product_ids was allow-listed in ALLOWED_SETTING_KEYS but
    had no matching SiteSettingsPayload field, so it was silently dropped by
    Pydantic and could never actually be set through this endpoint."""
    res = client.put("/api/admin/site-settings", json={
        "polar_product_ids": {"facebook": "prod_fb"},
    })
    assert res.status_code == 200
    assert "polar_product_ids" in res.json()["updated"]
