"""
Tests for AI Provider & Model management (Phase 8 — opencode-style).
DB isolated via mocked supabase_db; discovery HTTP mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.ai.provider_manager import AIProviderManager, OFFICIAL_PROVIDERS, _mask


@pytest.fixture
def mgr():
    m = AIProviderManager()
    m._fake_providers = {}
    m._fake_models = {}
    return m


def _patch_db(mgr, monkeypatch):
    """In-memory fake for the subset of supabase_db used by the manager."""
    import uuid

    def fake_insert(table, data):
        import uuid as _uuid
        data = {**data, "id": str(_uuid.uuid4())}
        if table == "ai_providers":
            mgr._fake_providers[data["id"]] = data
        elif table == "ai_models":
            mgr._fake_models[data["id"]] = data
        return data

    def fake_select(table, filters=None):
        if table == "ai_providers":
            rows = [v for v in mgr._fake_providers.values() if v]
        elif table == "ai_models":
            rows = [v for v in mgr._fake_models.values() if v]
        else:
            rows = []
        if filters:
            for k, v in filters.items():
                rows = [r for r in rows if r.get(k) == v]
        return rows

    def fake_update(table, record_id, updates):
        store = mgr._fake_providers if table == "ai_providers" else mgr._fake_models
        if record_id in store:
            store[record_id].update(updates)
            return store[record_id]
        return None

    def fake_delete(table, record_id):
        store = mgr._fake_providers if table == "ai_providers" else mgr._fake_models
        store.pop(record_id, None)
        if table == "ai_providers":
            for mid in [k for k, v in mgr._fake_models.items() if v.get("provider_id") == record_id]:
                mgr._fake_models.pop(mid, None)
        return True

    monkeypatch.setattr("src.ai.provider_manager.supabase_db.insert", staticmethod(fake_insert))
    monkeypatch.setattr("src.ai.provider_manager.supabase_db.select", staticmethod(fake_select))
    monkeypatch.setattr("src.ai.provider_manager.supabase_db.update", staticmethod(fake_update))
    monkeypatch.setattr("src.ai.provider_manager.supabase_db.delete", staticmethod(fake_delete))
    monkeypatch.setattr("src.ai.provider_manager.supabase_db.is_connected", True)
    return mgr


def test_mask_key():
    assert _mask("sk-abcdef1234567890") == "sk-abc…7890"
    assert _mask("short") == "•••"
    assert _mask(None) == ""


def test_official_registry_has_logos():
    assert set(OFFICIAL_PROVIDERS.keys()) >= {"google", "anthropic", "openai", "openrouter"}
    for key, reg in OFFICIAL_PROVIDERS.items():
        assert reg["logo_key"] == key
        assert reg["base_url"].startswith("https://")


def test_create_provider_unknown_official_rejected(mgr, monkeypatch):
    _patch_db(mgr, monkeypatch)
    with pytest.raises(ValueError):
        mgr.create_provider({"kind": "official", "provider_key": "bogus"})


def test_create_custom_requires_base_url(mgr, monkeypatch):
    _patch_db(mgr, monkeypatch)
    with pytest.raises(ValueError):
        mgr.create_provider({"kind": "custom", "provider_key": "myprov", "base_url": ""})


def test_custom_provider_full_flow(mgr, monkeypatch):
    _patch_db(mgr, monkeypatch)

    # Discovery mocked: returns 2 models
    mgr.discover_models = lambda prov: [
        {"model_id": "my-model-a", "display_name": "My Model A"},
        {"model_id": "my-model-b", "display_name": "My Model B"},
    ]

    res = mgr.create_provider({
        "kind": "custom", "provider_key": "myprovider",
        "display_name": "My AI Provider",
        "base_url": "https://api.myprovider.com/v1",
        "api_key": "sk-test-123",
        "custom_headers": [{"header": "X-Tenant", "value": "hudhud"}],
    })
    pid = res["provider_id"]
    sync = mgr.sync_provider_models(pid)
    assert sync["status"] == "success"
    assert sync["discovered"] == 2
    assert sync["available"] == 2

    # Toggle one model off → client brains show only the enabled one
    models = mgr.list_models(pid)
    mgr.set_model_toggle(models[0]["id"], False)
    brains = mgr.enabled_brain_options()
    assert len(brains) == 1
    assert brains[0]["ref"] == "myprovider/" + models[1]["model_id"]

    # Add a manual model
    add = mgr.add_manual_model(pid, "manual-model-1", "Manual One")
    assert add["status"] == "success"
    brains = mgr.enabled_brain_options()
    assert any(b["model_id"] == "manual-model-1" for b in brains)


def test_disabled_provider_hidden_from_brains(mgr, monkeypatch):
    _patch_db(mgr, monkeypatch)
    mgr.discover_models = lambda prov: [{"model_id": "m1", "display_name": "M1"}]
    res = mgr.create_provider({"kind": "custom", "provider_key": "p1", "display_name": "P1",
                              "base_url": "https://x.example/v1", "api_key": "k"})
    mgr.sync_provider_models(res["provider_id"])
    assert len(mgr.enabled_brain_options()) == 1

    mgr.update_provider(res["provider_id"], {"status": "disabled"})
    assert len(mgr.enabled_brain_options()) == 0


def test_discovery_failure_marks_models_unavailable(mgr, monkeypatch):
    _patch_db(mgr, monkeypatch)

    # First: discovery works
    mgr.discover_models = lambda prov: [{"model_id": "a", "display_name": "A"}]
    res = mgr.create_provider({"kind": "custom", "provider_key": "p", "display_name": "P",
                              "base_url": "https://x.example/v1"})
    mgr.sync_provider_models(res["provider_id"])
    assert len(mgr.enabled_brain_options()) == 1

    # Then: provider breaks (returns nothing)
    mgr.discover_models = lambda prov: []
    sync = mgr.sync_provider_models(res["provider_id"])
    assert sync["discovered"] == 0
    # Previously available model now unavailable → hidden
    assert len(mgr.enabled_brain_options()) == 0
