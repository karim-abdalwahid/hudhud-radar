"""
WS-E+H Admin Console API tests — FULLY ISOLATED (no production writes).

Production isolation strategy:
- users traffic: _traffic_log_middleware skips writes when Supabase is in
  test mode (we gate it via the in-memory fallback flag used by conftest).
- Admin Console tests read/write users through a fake in-memory table.
"""
import re
import uuid

import pytest
from starlette.testclient import TestClient

import src.modules.pages  # noqa: F401
import src.modules.admin_console  # noqa: F401


@pytest.fixture
def fake_users_db(client, monkeypatch):
    """Intercepts Admin Console users-table ops with an in-memory store."""
    from fastapi.testclient import TestClient as _TC
    from src.core.auth import user_store
    from src.modules import admin_console as ac

    table = {}

    def _sync_admin():
        """Seed the fake table with the session admin (from /auth/me)."""
        try:
            me = client.get("/auth/me").json()
            if me.get("authenticated") and me["user_id"] not in table:
                table[me["user_id"]] = {
                    "id": me["user_id"], "email": me.get("email"),
                    "role": me.get("role", "admin"), "is_active": True,
                    "plan": "free", "ai_credits": 100, "created_at": "2026-09-09T00:00:00Z",
                }
        except Exception:
            pass

    def fake_select(table_name, filters=None):
        if table_name == "users":
            _sync_admin()
            return list(table.values())
        return []

    def fake_update(table_name, rid, data):
        if table_name == "users":
            _sync_admin()
            if rid in table:
                table[rid].update(data)
                return table[rid]
        raise RuntimeError(f"user {rid} not found (fake users db)")

    def fake_insert(table_name, data):
        if table_name == "users":
            rid = data.get("id") or str(uuid.uuid4())
            table[rid] = {**data, "id": rid}
            return table[rid]
        return {}

    def register_and_track(email, password="StrongPass#1", **extra):
        # SEPARATE client: registering would overwrite the admin session cookie
        from src.main import app as _app
        boot = _TC(_app)
        boot.post("/auth/register", json={
            "email": email, "password": password, "terms_accepted": True, **extra,
        })
        user = user_store.get_by_email(email)
        assert user, "registration should succeed (in-memory store)"
        table[user["id"]] = {**user}
        return user

    monkeypatch.setattr(ac.supabase_db, "select", fake_select)
    monkeypatch.setattr(ac.supabase_db, "update", fake_update)
    monkeypatch.setattr(ac.supabase_db, "insert", fake_insert)
    return {"table": table, "register_and_track": register_and_track}


def test_users_list_admin_only(client_as_user, anon_client):
    assert client_as_user.get("/api/admin/users").status_code == 403
    assert anon_client.get("/api/admin/users").status_code == 401


def test_users_list_shows_registered(client, fake_users_db):
    u = fake_users_db["register_and_track"](f"a_{uuid.uuid4().hex[:6]}@hudhud.test")
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    emails = [x["email"] for x in r.json()["users"]]
    assert u["email"] in emails


def test_users_search_filters(client, fake_users_db):
    fake_users_db["register_and_track"](f"searchable_{uuid.uuid4().hex[:6]}@hudhud.test")
    r = client.get("/api/admin/users?search=nonexistent-zzz")
    assert r.status_code == 200 and r.json()["count"] == 0


def test_create_edit_disable_user_flow(client, fake_users_db):
    u = fake_users_db["register_and_track"](f"flow_{uuid.uuid4().hex[:6]}@hudhud.test")
    uid = u["id"]

    r2 = client.patch(f"/api/admin/users/{uid}", json={"is_active": False})
    assert r2.status_code == 200 and r2.json()["user"]["is_active"] is False
    r3 = client.patch(f"/api/admin/users/{uid}", json={"is_active": True})
    assert r3.json()["user"]["is_active"] is True
    r4 = client.patch(f"/api/admin/users/{uid}", json={"full_name": "Renamed"})
    assert r4.json()["user"]["full_name"] == "Renamed"


def test_admin_cannot_disable_self(client, fake_users_db):
    me = client.get("/auth/me").json()
    r = client.patch(f"/api/admin/users/{me['user_id']}", json={"is_active": False})
    assert r.status_code == 400


def test_grant_credits_adds(client, fake_users_db):
    u = fake_users_db["register_and_track"](f"cr_{uuid.uuid4().hex[:6]}@hudhud.test")
    before = fake_users_db["table"][u["id"]].get("ai_credits", 100)
    r = client.post(f"/api/admin/users/{u['id']}/credits", json={"amount": 250, "note": "bonus"})
    assert r.status_code == 200
    assert r.json()["ai_credits"] == before + 250


def test_grant_credits_rejects_negative(client, fake_users_db):
    u = fake_users_db["register_and_track"](f"neg_{uuid.uuid4().hex[:6]}@hudhud.test")
    r = client.post(f"/api/admin/users/{u['id']}/credits", json={"amount": -5})
    assert r.status_code == 400


def test_set_plan_validates(client, fake_users_db):
    u = fake_users_db["register_and_track"](f"plan_{uuid.uuid4().hex[:6]}@hudhud.test")
    r = client.post(f"/api/admin/users/{u['id']}/plan", json={"plan": "growth"})
    assert r.status_code == 200 and r.json()["plan"] == "growth"
    r2 = client.post(f"/api/admin/users/{u['id']}/plan", json={"plan": "diamond-ultra"})
    assert r2.status_code == 400


def test_admin_overview_kpis(client, fake_users_db):
    r = client.get("/api/admin/overview")
    assert r.status_code == 200
    d = r.json()
    for k in ("users_total", "signups_7d", "leads_total", "plan_distribution"):
        assert k in d
    assert d["users_total"] >= 1


def test_traffic_log_written_on_dashboard_visit(client, fake_users_db, monkeypatch):
    # traffic also must be isolated: intercept site_traffic writes
    from src.modules import pages as pages_mod
    traffic = []
    def fake_traffic_insert(table, data):
        if table == "site_traffic":
            traffic.append(data)
        return data
    monkeypatch.setattr(pages_mod.supabase_db, "insert", fake_traffic_insert)
    client.get("/dashboard")
    assert any(t.get("path") == "/dashboard" for t in traffic)


def test_users_page_admin_only(client, client_as_user):
    assert client.get("/users").status_code == 200
    assert client_as_user.get("/users").status_code == 403


def test_users_page_in_admin_nav(client, client_as_user):
    nav = re.search(r'<nav class="sidebar-nav">(.*?)</nav>', client.get("/users").text, re.S).group(1)
    assert "/users" in nav
    nav_u = client_as_user.get("/leads").text
    # regular user: no admin links at all
    assert "/users" not in re.search(r'<nav class="sidebar-nav">(.*?)</nav>', nav_u, re.S).group(1)
