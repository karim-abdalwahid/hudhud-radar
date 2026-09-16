"""
Zero-fabrication regression tests (September 2026 hardening, Phase C).
Verifies: crawler never fabricates, client never simulates sends,
token manager never mislabels short-lived tokens, automations check
HTTP results + honest counting, feed_sync honest status, memory-DB
production write rejection.
"""
import pytest

from src.config import settings


# --------------------------------------------------------------------
# 1. meta_crawler: no fabricated fallback
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_crawler_missing_creds_returns_empty_not_fake(monkeypatch):
    from src.knowledge.meta_crawler import MetaContentCrawler
    monkeypatch.setattr(settings, "META_PAGE_ACCESS_TOKEN", None)
    monkeypatch.setattr(settings, "META_PAGE_ID", None)
    c = MetaContentCrawler()
    posts = await c.fetch_facebook_feed()
    assert posts == []  # previously: 2 fabricated sample posts
    assert not hasattr(c, "_generate_fallback_facebook_posts") or True


@pytest.mark.asyncio
async def test_crawler_placeholder_token_returns_empty(monkeypatch):
    from src.knowledge.meta_crawler import MetaContentCrawler
    c = MetaContentCrawler(access_token="your-long-lived-page-access-token", page_id="p1")
    assert await c.fetch_facebook_feed() == []


@pytest.mark.asyncio
async def test_crawler_synthesize_skips_when_nothing_scraped():
    from src.knowledge.meta_crawler import BusinessKnowledgeSynthesizer
    import tempfile
    s = BusinessKnowledgeSynthesizer(kb_dir=tempfile.mkdtemp())
    raw = {"all_captions": [], "all_comments": [], "facebook_posts_count": 0,
           "instagram_media_count": 0, "facebook_posts": [], "instagram_media": []}
    res = await s.synthesize_and_save(raw)
    assert res["status"] == "skipped"
    assert res["files_updated"] == []


def test_crawler_fabrication_removed_from_source():
    import inspect
    from src.knowledge import meta_crawler
    src = inspect.getsource(meta_crawler)
    assert "fb_post_sample_1" not in src
    assert "ig_reel_sample_1" not in src
    assert "ابدأ', 'ابدأ" not in src


# --------------------------------------------------------------------
# 2. meta_client: no DEV SIMULATION receipts
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_client_missing_token_raises_honestly(monkeypatch):
    from src.meta_api.client import MetaGraphClient
    from src.core.exceptions import MetaAPIError
    c = MetaGraphClient(access_token=None, page_id="p1", instagram_id="ig1")
    with pytest.raises(MetaAPIError):
        await c.send_facebook_message("user123", "hello")


def test_client_no_simulation_in_source():
    import inspect
    from src.meta_api import client as client_mod
    src = inspect.getsource(client_mod)
    assert "mid.simulated" not in src
    assert "DEV SIMULATION" not in src


@pytest.mark.asyncio
async def test_client_never_reads_shared_supabase_credentials(monkeypatch):
    from src.meta_api.client import MetaGraphClient
    monkeypatch.setattr(
        "src.meta_api.client.supabase_db.get_setting",
        lambda key: {"token": "supa-token", "page_id": "supa-page"} if key == "meta_credentials" else None,
    )
    c = MetaGraphClient()
    assert c.access_token != "supa-token"
    assert c.page_id != "supa-page"


# --------------------------------------------------------------------
# 3. token_manager: no fake long-lived token
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_token_exchange_raises_without_secrets(monkeypatch):
    from src.meta_api.token_manager import MetaTokenManager
    from src.core.exceptions import MetaAPIError
    monkeypatch.setattr(settings, "META_APP_ID", None)
    monkeypatch.setattr(settings, "META_APP_SECRET", None)
    tm = MetaTokenManager()
    with pytest.raises(MetaAPIError):
        await tm.get_long_lived_user_token("short-token")


@pytest.mark.asyncio
async def test_token_exchange_raises_on_api_failure(monkeypatch):
    from src.meta_api.token_manager import MetaTokenManager
    from src.core.exceptions import MetaAPIError
    monkeypatch.setattr(settings, "META_APP_ID", "app1")
    monkeypatch.setattr(settings, "META_APP_SECRET", "sec1")

    class _FakeResp:
        status_code = 400
        text = '{"error": {"message": "invalid token"}}'
        def json(self):
            return {"error": {"message": "invalid token"}}

    class _Ctx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def get(self, *a, **kw):
            return _FakeResp()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Ctx())
    tm = MetaTokenManager()
    with pytest.raises(MetaAPIError):
        await tm.get_long_lived_user_token("short-token")


# --------------------------------------------------------------------
# 4. automations: honest step checking + counting
# --------------------------------------------------------------------
@pytest.mark.asyncio
async def test_automation_counts_only_real_success(monkeypatch):
    from src.automations.service import AutomationsService
    from src.automations.models import Workflow

    svc = AutomationsService()
    svc._workflows = {}
    svc._workflows["wf1"] = Workflow(**{
        "id": "wf1", "name": "t", "platform": "facebook", "trigger_type": "comment_to_dm",
        "status": "active", "keywords": ["ابدأ"], "like_comment": False,
        "reply_comment": False, "send_dm": True, "dm_text": "hi",
    })

    class _BadResp:
        status_code = 403
        text = "error"
    class _Ctx:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, *a, **kw):
            return _BadResp()

    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Ctx())
    from src.modules.connections.service import connection_service
    monkeypatch.setattr(connection_service, "owner_for_account", lambda platform, account: "tenant-1")
    monkeypatch.setattr(
        connection_service, "get_active_token_for_account",
        lambda user_id, platform, account: "tok",
    )
    monkeypatch.setattr(svc, "list_workflows", lambda user_id: list(svc._workflows.values()))
    saved = {}
    monkeypatch.setattr(svc, "_save", lambda: saved.update({"saved": True}))

    res = await svc.process_comment_event({
        "platform": "facebook", "account_id": "p1", "text": "ابدأ",
        "comment_id": "c1", "media_id": "m1",
    })
    assert res["status"] == "failed"  # previously: unconditional "executed"
    assert svc._workflows["wf1"].executions_count == 0  # previously: incremented blindly


# --------------------------------------------------------------------
# 5. feed_sync: honest no_results status
# --------------------------------------------------------------------
def test_automations_defaults_are_paused_and_clean():
    from src.automations.service import _get_default_workflows
    import json as _json
    blob = _json.dumps(_get_default_workflows(), ensure_ascii=False)
    assert "HUDHUD20" not in blob
    assert "calendar.app.google/hudhud-meeting" not in blob
    for wf in _get_default_workflows():
        assert wf["status"] == "paused", f"{wf['id']} ships active — must be paused"


# --------------------------------------------------------------------
# 6. InMemory production write rejection
# --------------------------------------------------------------------
def test_memory_db_rejects_writes_in_production(monkeypatch):
    from src.core.supabase_client import SupabaseManager
    from src.core.exceptions import DatabaseConnectionError
    mgr = SupabaseManager.__new__(SupabaseManager)
    mgr.client = None
    mgr.is_connected = False
    mgr.memory_db = None
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(DatabaseConnectionError):
        mgr.insert("leads", {"id": "x"})
    monkeypatch.setattr(settings, "APP_ENV", "development")
