"""
Phase 9.1 tests — entitlements, composable pricing, subscription state.
FULLY isolated (fake users DB for the billing module only — no prod writes).

Note: no HTTP calls inside patched select (that recursed). The fake table is
seeded once from the session admin (captured pre-patch) + explicit registers
through the in-memory user store.
"""
import uuid
from fastapi.testclient import TestClient as _TC

import pytest
from starlette.testclient import TestClient

import src.modules.billing as billing
from src.modules.billing.services import EntitlementService, PricingService


@pytest.fixture
def fake_billing(client, monkeypatch):
    from src.core.auth import user_store

    # 1. seed admin ONCE (real client, before any patching)
    me = client.get("/auth/me").json()
    users = {}
    if me.get("authenticated"):
        users[me["user_id"]] = {"id": me["user_id"], "email": me.get("email"),
                                "role": me.get("role"), "is_active": True,
                                "created_at": "2026-09-09T00:00:00Z"}

    ent = {}
    subs = {}
    cat = {
        "facebook": {"id": "c-fb", "platform": "facebook", "display_name": "Facebook Page",
                     "price_usd": 15.0, "is_available": True, "sort_order": 1},
        "instagram": {"id": "c-ig", "platform": "instagram", "display_name": "Instagram Business",
                      "price_usd": 15.0, "is_available": True, "sort_order": 2},
        "threads": {"id": "c-th", "platform": "threads", "display_name": "Threads",
                    "price_usd": 10.0, "is_available": True, "sort_order": 3},
    }
    coupons = {}

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
        if table == "platform_addons_catalog":
            return list(cat.values())
        if table == "coupons":
            return [c for c in coupons.values()
                    if not f or f.get("code") in (None, c.get("code"))]
        return []

    def insert(table, data):
        if table == "user_entitlements":
            rid = f"e{len(ent)+1}"
            ent[rid] = {"id": rid, **data}
            return ent[rid]
        if table == "user_subscriptions":
            subs[data["user_id"]] = {**data}
            return subs[data["user_id"]]
        if table == "coupons":
            coupons[data["code"]] = {**data}
            return coupons[data["code"]]
        return data

    def update(table, rid, data):
        if table == "user_entitlements" and rid in ent:
            ent[rid].update(data)
            return ent[rid]
        if table == "user_subscriptions":
            return data
        if table == "platform_addons_catalog" and rid in cat:
            cat[rid].update(data)
            return cat[rid]
        return data

    def delete(table, rid):
        if table == "user_entitlements" and rid in ent:
            del ent[rid]
        return True

    monkeypatch.setattr(billing.supabase_db, "select", select)
    monkeypatch.setattr(billing.supabase_db, "insert", insert)
    monkeypatch.setattr(billing.supabase_db, "update", update)
    monkeypatch.setattr(billing.supabase_db, "delete", delete)

    def register_and_track(email):
        """Register via in-memory user store + mirror into the fake users table."""
        _TC(client.app).post("/auth/register", json={
            "email": email, "password": "StrongPass#1", "terms_accepted": True})
        u = user_store.get_by_email(email)
        users[u["id"]] = {**u}
        return u

    return {"users": users, "ent": ent, "subs": subs, "cat": cat,
            "coupons": coupons, "register_and_track": register_and_track}


# ── Entitlement service ──────────────────────────────────────────────────
def test_grant_and_has(fake_billing):
    svc = EntitlementService()
    u = fake_billing["register_and_track"](f"e1_{uuid.uuid4().hex[:6]}@hudhud.test")
    assert svc.has_platform(u["id"], "facebook") is False
    svc.grant(u["id"], "platform:facebook")
    assert svc.has_platform(u["id"], "facebook") is True
    assert svc.connected_platforms(u["id"]) == ["facebook"]


def test_revoke_removes_access(fake_billing):
    svc = EntitlementService()
    u = fake_billing["register_and_track"](f"e2_{uuid.uuid4().hex[:6]}@hudhud.test")
    svc.grant(u["id"], "platform:instagram")
    svc.revoke(u["id"], "platform:instagram")
    assert svc.has_platform(u["id"], "instagram") is False


def test_sync_from_platforms_exact_set(fake_billing):
    svc = EntitlementService()
    u = fake_billing["register_and_track"](f"e3_{uuid.uuid4().hex[:6]}@hudhud.test")
    svc.sync_from_platforms(u["id"], ["facebook", "instagram"])
    assert set(svc.connected_platforms(u["id"])) == {"facebook", "instagram"}
    svc.sync_from_platforms(u["id"], ["facebook", "threads"])  # payment truth swap
    assert set(svc.connected_platforms(u["id"])) == {"facebook", "threads"}


def test_fail_closed_on_db_error(fake_billing, monkeypatch):
    from src.modules import billing as b
    svc = EntitlementService()
    monkeypatch.setattr(b.supabase_db, "select",
                        lambda t, f=None: (_ for _ in ()).throw(RuntimeError("db down")))
    assert svc.user_entitlements("u-x") == []
    assert svc.has("u-x", "platform:facebook") is False


# ── Trial ────────────────────────────────────────────────────────────────
def test_start_trial_grants_all_platforms_3_days(fake_billing):
    svc = EntitlementService()
    u = fake_billing["register_and_track"](f"t1_{uuid.uuid4().hex[:6]}@hudhud.test")
    svc.start_trial(u["id"])
    assert fake_billing["subs"][u["id"]]["status"] == "trialing"
    assert set(svc.connected_platforms(u["id"])) == {"facebook", "instagram", "threads"}
    st = svc.subscription_status(u["id"])
    assert st["can_connect"] is True and st["status"] == "trialing"


def test_trial_auto_expires(fake_billing):
    svc = EntitlementService()
    u = fake_billing["register_and_track"](f"t2_{uuid.uuid4().hex[:6]}@hudhud.test")
    from datetime import datetime, timedelta, timezone
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    # seeded WITH id — subscription_status calls upsert on expiry which needs it
    fake_billing["subs"][u["id"]] = {"id": "sub-t2", "user_id": u["id"],
                                     "status": "trialing", "trial_ends_at": past}
    st = svc.subscription_status(u["id"])
    assert st["status"] == "canceled"
    assert svc.connected_platforms(u["id"]) == []
    assert st["can_connect"] is False


# ── Composable pricing ───────────────────────────────────────────────────
def test_quote_single_platform_no_discount(fake_billing):
    q = PricingService().quote(["facebook"])
    assert q["subtotal_usd"] == 15.0 and q["multi_platform_discount_percent"] == 0
    assert q["total_usd"] == 15.0


def test_quote_two_platforms_discount10(fake_billing):
    q = PricingService().quote(["facebook", "instagram"])
    assert q["subtotal_usd"] == 30.0
    assert q["multi_platform_discount_percent"] == 10
    assert q["total_usd"] == 27.0


def test_quote_three_platforms_discount20(fake_billing):
    q = PricingService().quote(["facebook", "instagram", "threads"])
    assert q["subtotal_usd"] == 40.0
    assert q["multi_platform_discount_percent"] == 20
    assert q["total_usd"] == 32.0


def test_quote_percent_coupon(fake_billing):
    q = PricingService().quote(["facebook", "instagram"],
                               coupon={"kind": "percent", "value": 10})
    assert q["subtotal_usd"] == 30.0
    assert q["coupon_discount_usd"] == 2.7
    assert q["total_usd"] == 24.3


def test_quote_unknown_platform_skipped(fake_billing):
    q = PricingService().quote(["facebook", "tiktok"])
    assert q["platforms"] == ["facebook"]
    assert q["total_usd"] == 15.0


# ── API endpoints ────────────────────────────────────────────────────────
def test_subscription_api_auth_gated(anon_client: TestClient):
    assert anon_client.get("/api/billing/subscription").status_code == 401


def test_admin_catalog_gates(client: TestClient, client_as_user: TestClient,
                             anon_client: TestClient, fake_billing):
    assert anon_client.get("/api/admin/billing/catalog").status_code == 401
    assert client_as_user.get("/api/admin/billing/catalog").status_code == 403
    r = client.get("/api/admin/billing/catalog")
    assert r.status_code == 200 and len(r.json()["catalog"]) == 3


def test_admin_edit_catalog_price(client: TestClient, fake_billing):
    r = client.put("/api/admin/billing/catalog/threads", json={"price_usd": 12.0})
    assert r.status_code == 200 and r.json()["addon"]["price_usd"] == 12.0


def test_my_subscription_empty(client: TestClient, fake_billing):
    r = client.get("/api/billing/subscription")
    assert r.status_code == 200
    assert r.json()["status"] == "none"

# ── Checkout + coupons + site settings (9.3) ─────────────────────────────
def test_checkout_requires_auth(anon_client: TestClient):
    r = anon_client.post("/api/billing/checkout", json={"platforms": ["facebook"]})
    assert r.status_code == 401


def test_checkout_rejects_empty_platforms(client: TestClient, fake_billing):
    r = client.post("/api/billing/checkout", json={"platforms": []})
    assert r.status_code == 400


def test_coupon_create_requires_admin(client_as_user: TestClient):
    r = client_as_user.post("/api/admin/billing/coupons", json={
        "code": "TEST10", "kind": "percent", "value": 10})
    assert r.status_code == 403


def test_site_settings_gated(client_as_user: TestClient, anon_client: TestClient):
    assert client_as_user.get("/api/admin/site-settings").status_code == 403
    assert anon_client.get("/api/admin/site-settings").status_code == 401


def test_site_settings_rejects_unknown_key(client: TestClient, fake_billing):
    """Pydantic ignores unknown fields; ALLOWED_SETTING_KEYS whitelist means
    nothing unknown is ever persisted (safe default-deny)."""
    r = client.put("/api/admin/site-settings", json={"evil_key": "x"})
    st = client.get("/api/admin/site-settings").json()["settings"]
    assert "evil_key" not in st
