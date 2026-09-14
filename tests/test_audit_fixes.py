"""Regression tests for the full-backend audit fixes (Phase 3-5):
- meta/configure no longer NameErrors (PROJECT_ROOT) -> never 5xx
- knowledge create/update validation -> 400 (was 500)
- publish double-execution guard (CAS claim)
- dedup duplicate-key tolerance (no DB-dedup self-disable)"""
from types import SimpleNamespace

import pytest


def test_meta_configure_empty_payload_not_500(client):
    # admin session from conftest; empty payload must not crash (was NameError 500)
    r = client.post("/api/meta/configure", json={})
    assert r.status_code < 500, r.text[:200]


def test_meta_configure_path_imported():
    from src.modules.meta import routes as m
    assert hasattr(m, "PROJECT_ROOT") and hasattr(m, "Path")


def test_knowledge_create_invalid_returns_400(client):
    r = client.post("/api/knowledge/documents", json={"filename": "", "content": ""})
    assert r.status_code == 400


def test_knowledge_update_invalid_returns_400(client):
    r = client.put("/api/knowledge/documents/bad.md", json={"content": "   "})
    assert r.status_code in (400, 404)


def test_publish_claim_blocks_double_execution(monkeypatch):
    from src.agent.scheduler import content_scheduler
    post = SimpleNamespace(id="post-1", platform=SimpleNamespace(value="facebook"),
                           post_type=SimpleNamespace(value="post"))
    monkeypatch.setattr(content_scheduler, "_claim_for_publish", lambda pid: False)
    res = __import__("asyncio").run(
        content_scheduler.publish_single_post(post, allow_inflight=False))
    assert res.get("status") == "skipped_already_publishing"


def test_publish_claim_allows_fresh_create_path(monkeypatch):
    from src.agent.scheduler import content_scheduler
    calls = []
    monkeypatch.setattr(content_scheduler, "_claim_for_publish",
                        lambda pid: calls.append(pid) or False)
    # allow_inflight=True must NOT consult the claim (create->publish path)
    post = SimpleNamespace(id="post-2", platform=SimpleNamespace(value="facebook"),
                           post_type=SimpleNamespace(value="post"),
                           content_text="", media_urls=[], status=None)
    # we only assert the claim was skipped before any early-return logic ran
    try:
        __import__("asyncio").run(
            content_scheduler.publish_single_post(post, allow_inflight=True))
    except Exception:
        pass
    assert calls == []  # claim not consulted at all when allow_inflight


def test_dedup_duplicate_key_keeps_db_dedup_enabled(monkeypatch):
    from src.core.event_dedup import EventDeduplicator

    class ConflictDB:
        is_connected = True

        def insert(self, table, data):
            raise Exception('duplicate key value violates unique constraint "processed_events_event_key_key"')

    d = EventDeduplicator()
    d._db_disabled = False
    monkeypatch.setattr("src.core.supabase_client.supabase_db", ConflictDB())
    monkeypatch.setattr(d, "_db_ready", lambda: True)
    assert d.mark_processed("evt-x", "message") is False
    assert d._db_disabled is False  # NOT disabled


def test_ai_provider_empty_custom_returns_400_not_500(client):
    """Button audit: submitNewProvider() with an empty form must 400 (was 500)."""
    r = client.post("/api/ai/providers",
                    json={"kind": "custom", "provider_key": "",
                          "display_name": "", "base_url": "", "api_key": ""})
    assert r.status_code == 400, r.text[:250]
    assert "display_name" in r.text or "اسم" in r.text


def test_ai_provider_bad_base_url_returns_400(client):
    r = client.post("/api/ai/providers", json={
        "kind": "custom", "provider_key": "bad-url-test",
        "display_name": "X", "base_url": "not-a-url", "api_key": ""})
    assert r.status_code == 400, r.text[:200]
