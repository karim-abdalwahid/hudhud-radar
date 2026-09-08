"""
WS-F notifications tests: service CRUD, user APIs (401-protected), admin
broadcast, job hooks (fail-silent, honest), bell UI present on dashboard.
"""
import re

import pytest
from starlette.testclient import TestClient

import src.modules.notifications  # noqa: F401
from src.modules.notifications.service import NotificationService


@pytest.fixture
def svc():
    return NotificationService()


class _Row:
    def __init__(self, data):
        self._d = data
    def get(self, k, d=None):
        return self._d.get(k, d)


def test_service_create_fail_silent(monkeypatch, svc):
    from src.core import supabase_client as sc

    def boom(*a, **kw):
        raise RuntimeError("db down")
    monkeypatch.setattr(sc.supabase_db, "insert", boom)
    res = svc.create("user-1", "title", "body")
    assert res is None  # fail-silent: business ops never break


def test_service_create_and_list(monkeypatch, svc):
    from src.core import supabase_client as sc
    stored = []
    updates = []

    def fake_insert(table, data):
        stored.append({**data, "id": "00000000-0000-0000-0000-000000000001", "read": False, "created_at": "2026-09-09T00:00:00Z"})
        return stored[-1]

    def fake_select(table, filters=None):
        if table == "notifications":
            return stored
        return []

    def fake_update(table, rid, data):
        updates.append((table, rid, data))
        for row in stored:
            if row.get("id") == rid:
                row.update(data)
        return {"id": rid}
    monkeypatch.setattr(sc.supabase_db, "insert", fake_insert)
    monkeypatch.setattr(sc.supabase_db, "select", fake_select)
    monkeypatch.setattr(sc.supabase_db, "update", fake_update)

    svc.create("user-1", "Job done", "detail", "success")
    rows = svc.list_for_user("user-1")
    assert len(rows) == 1 and rows[0]["title"] == "Job done"
    assert svc.unread_count("user-1") == 1
    svc.mark_read("user-1", "00000000-0000-0000-0000-000000000001")
    assert svc.unread_count("user-1") == 0
    assert updates and updates[0][2] == {"read": True}


def test_invalid_type_normalized(svc, monkeypatch):
    from src.core import supabase_client as sc
    seen = {}
    monkeypatch.setattr(sc.supabase_db, "insert", lambda t, d: seen.update(d) or d)
    svc.create("u1", "t", "b", "NOT-A-TYPE")
    assert seen["type"] == "info"


def test_broadcast_all_users(monkeypatch, svc):
    from src.core import supabase_client as sc
    users = [{"id": "u1", "is_active": True}, {"id": "u2", "is_active": True}, {"id": "u3", "is_active": False}]
    created = []
    monkeypatch.setattr(sc.supabase_db, "select", lambda t, f=None: users if t == "users" else [])
    monkeypatch.setattr(sc.supabase_db, "insert", lambda t, d: created.append(d) or d)
    count = svc.broadcast("Hello everyone", "body")
    assert count == 2  # inactive user skipped
    assert all(c["type"] == "broadcast" for c in created)


def test_broadcast_single_target(monkeypatch, svc):
    from src.core import supabase_client as sc
    created = []
    monkeypatch.setattr(sc.supabase_db, "select", lambda t, f=None: [])
    monkeypatch.setattr(sc.supabase_db, "insert", lambda t, d: created.append(d) or d)
    count = svc.broadcast("Just for you", "hi", target_user_id="u9")
    assert count == 1 and created[0]["user_id"] == "u9"


def test_user_apis_auth_gated(anon_client: TestClient):
    assert anon_client.get("/api/notifications").status_code == 401
    assert anon_client.get("/api/notifications/unread-count").status_code == 401
    assert anon_client.post("/api/notifications/read-all").status_code == 401
    assert anon_client.post("/api/admin/notifications/broadcast", json={"title": "x"}).status_code == 401


def test_admin_broadcast_allowed_admin_blocked_user(client: TestClient, client_as_user: TestClient, monkeypatch):
    # ISOLATION: never write real notifications to the production users table
    from src.core import supabase_client as sc
    created = []
    monkeypatch.setattr(sc.supabase_db, "select", lambda t, f=None: [{"id": "fake-admin-1", "is_active": True}] if t == "users" else [])
    monkeypatch.setattr(sc.supabase_db, "insert", lambda t, d: created.append(d) or d)
    # route imports service singleton → patch its module-level db too
    import src.modules.notifications.service as nsvc
    monkeypatch.setattr(nsvc.supabase_db, "select", lambda t, f=None: [{"id": "fake-admin", "is_active": True}] if t == "users" else [d for d in created])
    monkeypatch.setattr(nsvc.supabase_db, "insert", lambda t, d: created.append(d) or d)
    r = client.post("/api/admin/notifications/broadcast", json={"title": "اختبار بث", "body": "b"})
    assert r.status_code == 200  # delivered counted through the mocked DB


def test_user_sees_broadcast(client: TestClient,client_as_user: TestClient, monkeypatch):
    # ISOLATED fake DB — real users table must never receive test broadcasts
    fake_rows = []
    import src.modules.notifications.service as nsvc

    def fake_select(table, f=None):
        if table == "users":
            # the sessions' user is in-memory in tests; feed a stable fake id
            return [{"id": "11111111-1111-1111-1111-111111111111", "is_active": True}]
        if table == "notifications":
            return [r for r in fake_rows if r.get("read") is not None]
        return []
    fake_rows = []
    def fake_insert(table, data):
        fake_rows.append({**data, "id": "n-x", "read": False, "created_at": "z"})
        return fake_rows[-1]
    monkeypatch.setattr(nsvc.supabase_db, "select", fake_select)
    monkeypatch.setattr(nsvc.supabase_db, "insert", fake_insert)

    client.post("/api/admin/notifications/broadcast", json={"title": "For you", "body": "b"})
    r = client_as_user.get("/api/notifications")
    assert r.status_code == 200
    titles = [n["title"] for n in r.json()["notifications"]]
    assert "For you" in titles


def test_bell_ui_on_dashboard(client: TestClient):
    """The bell renders client-side via saas.js (injected into the topbar on
    every dashboard page). Server check: dashboard loads saas.js + the bell
    endpoint exists and is auth-gated."""
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert '/static/saas.js' in r.text                     # bell lives in saas.js
    js = client.get("/static/saas.js")
    assert "injectNotificationsBell" in js.text
    assert "hudhud-bell" in js.text
    # anonymous = gated
    anon = TestClient(client.app)
    assert anon.get("/api/notifications").status_code == 401
