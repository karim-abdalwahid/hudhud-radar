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

    loaded = db_load_workflows(db, user_id="user-1")
    assert loaded is not None and len(loaded) == 2
    by_name = {w.name: w for w in loaded}
    assert by_name["Alpha"].status == "active"
    assert by_name["Beta"].status == "paused"
    # full model fidelity via config JSONB
    assert by_name["Alpha"].keywords == _wf().keywords


def test_db_upsert_updates_not_duplicates():
    db = FakeDB()
    wf = _wf("Mutable")
    db_save_workflows(db, {wf.id: wf}, owner_user_id="user-1")
    wf2 = db_load_workflows(db, user_id="user-1")[0]
    wf2.name = "Mutated"
    db_save_workflows(db, {wf2.id: wf2}, owner_user_id="user-1")

    assert len(db.select("automations_workflows")) == 1
    assert db_load_workflows(db, user_id="user-1")[0].name == "Mutated"


def test_owner_is_required_for_all_tenant_queries_and_writes():
    db = FakeDB()
    assert db_load_workflows(db) is None
    assert db_save_workflows(db, {_wf().id: _wf()}) is False


def test_disconnected_db_is_safe():
    class Off(FakeDB):
        is_connected = False
    assert db_load_workflows(Off()) is None
    assert db_save_workflows(Off(), {}) is False


def test_malformed_row_skipped_not_fatal():
    db = FakeDB()
    db.insert("automations_workflows", {"id": "wf_bad", "user_id": "user-1", "config": {"not": "a workflow"}})
    good = _wf("Good")
    db_save_workflows(db, {good.id: good}, owner_user_id="user-1")
    loaded = db_load_workflows(db, user_id="user-1")
    assert loaded is not None and [w.name for w in loaded] == ["Good"]


def test_service_does_not_bootstrap_global_legacy_settings(monkeypatch):
    """A shared legacy store is never assigned to an arbitrary tenant."""
    import src.automations.service as amod
    db = FakeDB()
    db.set_setting = lambda *a, **k: True
    svc = amod.AutomationsService.__new__(amod.AutomationsService)
    svc._workflows = {}
    svc._load()
    assert svc._workflows == {}
