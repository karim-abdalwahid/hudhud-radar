"""
WS-G Templates Manager tests: admin CRUD on message_templates (fully
isolated fake DB — production untouched), lifecycle rendering, page gate.
"""
import pytest
from starlette.testclient import TestClient

import src.modules.templates_manager as tm


@pytest.fixture
def fake_tpl_db(monkeypatch):
    """In-memory message_templates table (seeded from DEFAULT_TEMPLATES)."""
    table = {}
    for k, v in tm.DEFAULT_TEMPLATES.items():
        table[f"row-{k}"] = {"id": f"row-{k}", "key": k, "channel": "inapp",
                             "is_active": True, "updated_at": "2026-09-09T00:00:00Z",
                             **v}

    def fake_select(table_name, filters=None):
        if table_name == "message_templates":
            rows = list(table.values())
            if filters and filters.get("key"):
                rows = [r for r in rows if r["key"] == filters["key"]]
            return rows
        if table_name == "users":
            return [{"id": "fake-admin", "role": "admin", "is_active": True}]
        return []

    def fake_update(table_name, rid, data):
        if table_name in ("message_templates",) and rid in table:
            table[rid].update(data)
            return table[rid]
        raise RuntimeError("not found")

    notifications_sent = []

    def fake_create(user_id, title, body, type="info", meta=None):
        notifications_sent.append({"user_id": user_id, "title": title, "body": body})
        return {"ok": True}

    monkeypatch.setattr(tm.supabase_db, "select", fake_select)
    monkeypatch.setattr(tm.supabase_db, "update", fake_update)
    monkeypatch.setattr(tm.supabase_db, "insert", lambda t, d: d)
    monkeypatch.setattr(tm.notification_service, "create", fake_create)
    return {"table": table, "sent": notifications_sent}


def test_list_templates_admin_only(anon_client: TestClient, client_as_user: TestClient):
    assert anon_client.get("/api/admin/templates").status_code == 401
    assert client_as_user.get("/api/admin/templates").status_code == 403


def test_list_seeded_templates(client: TestClient):
    r = client.get("/api/admin/templates")
    assert r.status_code == 200
    keys = [t["key"] for t in r.json()["templates"]]
    assert set(keys) >= {"welcome_signup", "trial_ending", "plan_purchased",
                         "credits_low", "agent_new_lead", "welcome_login"}


def test_update_template_subject_and_body(client: TestClient, fake_tpl_db):
    r = client.put("/api/admin/templates/welcome_signup", json={
        "subject": "مرحباً {user_name} 👋", "body": "نص مخصص للترحيب"
    })
    assert r.status_code == 200
    assert fake_tpl_db["table"]["row-welcome_signup"]["body"] == "نص مخصص للترحيب"


def test_update_unknown_key_rejected(client: TestClient):
    r = client.put("/api/admin/templates/not_a_key", json={"subject": "x"})
    assert r.status_code == 400


def test_restore_default(client: TestClient, fake_tpl_db):
    client.put("/api/admin/templates/welcome_signup", json={
        "body": "معدّل بالكامل", "is_active": False})
    r = client.post("/api/admin/templates/welcome_signup/restore")
    assert r.status_code == 200
    row = fake_tpl_db["table"]["row-welcome_signup"]
    assert row["body"] == tm.DEFAULT_TEMPLATES["welcome_signup"]["body"]
    assert row["is_active"] is True


def test_toggle_disabled_stops_delivery(client: TestClient, fake_tpl_db):
    client.put("/api/admin/templates/welcome_signup", json={"is_active": False})
    before = len(fake_tpl_db["sent"])
    delivered = tm.render_and_notify("welcome_signup", "u1", {"user_name": "أحمد"})
    assert delivered is False
    assert len(fake_tpl_db["sent"]) == before


def test_lifecycle_render_fills_placeholders_and_notifies(client: TestClient, fake_tpl_db):
    ok = tm.render_and_notify("welcome_signup", "user-9", {"user_name": "أحمد محمد"})
    assert ok is True
    sent = fake_tpl_db["sent"][-1]
    assert "أحمد محمد" in sent["title"]
    assert "{user_name}" not in sent["title"]


def test_render_unknown_template_is_fail_silent(fake_tpl_db):
    assert tm.render_and_notify("no_such_key", "u1") is False


def test_templates_page_admin_only(client: TestClient, client_as_user: TestClient):
    assert client.get("/templates").status_code == 200
    assert client_as_user.get("/templates").status_code == 403
