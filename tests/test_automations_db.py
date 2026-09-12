"""Wave 9.8: automations_workflows table persistence — pure helpers + cascade."""
import pytest

from src.core.supabase_client import InMemoryDatabase
from src.automations.models import Workflow
from src.automations.service import db_load_workflows, db_save_workflows


class FakeDB(InMemoryDatabase):
    is_connected = True


def _wf(name="Test WF", **kw):
    return Workflow(name=name, description="d", platform="both", **kw)


def test_db_save_and_load_roundtrip():
    db = FakeDB()
    wfs = {_w.id: _w for _w in (_wf("Alpha"), _wf("Beta", status="paused"))}
    assert db_save_workflows(db, wfs, owner_user_id="user-1") is True

    rows = db.select("automations_workflows")
    assert len(rows) == 2
    assert all(r.get("user_id") == "user-1" for r in rows)

    loaded = db_load_workflows(db)
    assert loaded is not None and len(loaded) == 2
    by_name = {w.name: w for w in loaded}
    assert by_name["Alpha"].status == "active"
    assert by_name["Beta"].status == "paused"
    # full model fidelity via config JSONB
    assert by_name["Alpha"].keywords == _wf().keywords


def test_db_upsert_updates_not_duplicates():
    db = FakeDB()
    wf = _wf("Mutable")
    db_save_workflows(db, {wf.id: wf})
    wf2 = db_load_workflows(db)[0]
    wf2.name = "Mutated"
    db_save_workflows(db, {wf2.id: wf2})

    assert len(db.select("automations_workflows")) == 1
    assert db_load_workflows(db)[0].name == "Mutated"


def test_empty_table_returns_none_for_legacy_fallback():
    assert db_load_workflows(FakeDB()) is None


def test_disconnected_db_is_safe():
    class Off(FakeDB):
        is_connected = False
    assert db_load_workflows(Off()) is None
    assert db_save_workflows(Off(), {}) is False


def test_malformed_row_skipped_not_fatal():
    db = FakeDB()
    db.insert("automations_workflows", {"id": "wf_bad", "config": {"not": "a workflow"}})
    good = _wf("Good")
    db_save_workflows(db, {good.id: good})
    loaded = db_load_workflows(db)
    assert loaded is not None and [w.name for w in loaded] == ["Good"]


def test_service_bootstrap_cascade(monkeypatch):
    """Table empty → legacy app_settings mirror loads AND bootstraps the table."""
    import src.automations.service as amod
    db = FakeDB()
    db.set_setting = lambda *a, **k: True
    db.get_setting = lambda key: {
        "workflows": [ _wf("Legacy One").model_dump(mode="json") ]
    } if key == "automations_workflows" else None
    db.is_connected = True

    svc = amod.AutomationsService.__new__(amod.AutomationsService)
    svc._workflows = {}
    monkeypatch.setattr(svc, "_load_db", lambda: db_load_workflows(db))
    monkeypatch.setattr(svc, "_save_db", lambda: db_save_workflows(db, svc._workflows))
    monkeypatch.setattr(svc, "_load_supabase", lambda: db.get_setting("automations_workflows"))
    monkeypatch.setattr(svc, "_save_supabase", lambda: False)
    monkeypatch.setattr(svc, "_save", lambda: None)

    svc._load()
    assert [w.name for w in svc._workflows.values()] == ["Legacy One"]

    # bootstrap mirror (explicit _save_db as production does at first write)
    svc._save_db()
    assert len(db.select("automations_workflows")) == 1

    # second load: table is now the source of truth (legacy would be empty)
    db.get_setting = lambda key: None
    svc2 = amod.AutomationsService.__new__(amod.AutomationsService)
    svc2._workflows = {}
    monkeypatch.setattr(svc2, "_load_db", lambda: db_load_workflows(db))
    monkeypatch.setattr(svc2, "_save_db", lambda: db_save_workflows(db, svc2._workflows))
    monkeypatch.setattr(svc2, "_load_supabase", lambda: None)
    monkeypatch.setattr(svc2, "_save", lambda: None)
    svc2._load()
    assert [w.name for w in svc2._workflows.values()] == ["Legacy One"]
