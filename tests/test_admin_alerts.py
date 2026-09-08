"""
Admin alerts: shared Supabase cache, force bypass, honest per-minute 429.
(Entry 029 — Gemini free tier is 20 req/MINUTE; health checks burned it.)
"""
import time

import pytest
from starlette.testclient import TestClient

from src.config import settings


def test_alerts_cached_in_supabase_shared_store(client: TestClient, monkeypatch):
    import src.core.admin_alerts as aa

    # Reset memory cache to force a fresh round
    aa._alerts_cache["alerts"] = None
    aa._alerts_cache["ts"] = 0.0

    stored = {}

    def fake_get_setting(key, default=None):
        if key == "system_alerts_cache":
            return stored.get(key)
        return None

    def fake_set_setting(key, value):
        stored[key] = value
        return True

    monkeypatch.setattr("src.core.admin_alerts.supabase_db.get_setting", fake_get_setting)
    monkeypatch.setattr("src.core.admin_alerts.supabase_db.set_setting", fake_set_setting)

    # Avoid real external calls: patch each check
    monkeypatch.setattr(aa, "_check_meta_token", lambda: {"id": "meta_token", "level": "ok", "title_ar": "x", "title_en": "x"})
    monkeypatch.setattr(aa, "_check_threads_token", lambda: {"id": "threads_token", "level": "ok", "title_ar": "x", "title_en": "x"})
    monkeypatch.setattr(aa, "_check_gemini", lambda: {"id": "gemini", "level": "ok", "title_ar": "x", "title_en": "x"})
    monkeypatch.setattr(aa, "_check_webhook_subscription", lambda: {"id": "webhook", "level": "ok", "title_ar": "x", "title_en": "x"})
    monkeypatch.setattr(aa, "_check_scheduler", lambda: {"id": "scheduler", "level": "ok", "title_ar": "x", "title_en": "x"})
    monkeypatch.setattr(aa, "_check_supabase", lambda: {"id": "supabase", "level": "ok", "title_ar": "x", "title_en": "x"})

    calls = {"n": 0}
    real_gemini = aa._check_gemini
    def counting_gemini():
        calls["n"] += 1
        return {"id": "gemini", "level": "ok", "title_ar": "x", "title_en": "x"}
    monkeypatch.setattr(aa, "_check_gemini", counting_gemini)

    # First call runs checks + persists shared cache
    r1 = aa.collect_alerts()
    assert calls["n"] == 1
    assert "system_alerts_cache" in stored

    # Memory cache hit — no new checks
    aa.collect_alerts()
    assert calls["n"] == 1

    # New instance simulation: memory wiped, shared cache serves
    aa._alerts_cache["alerts"] = None
    aa._alerts_cache["ts"] = 0.0
    aa.collect_alerts()
    assert calls["n"] == 1  # served from SHARED cache — no new Gemini call

    # force bypasses everything
    aa.collect_alerts(force=True)
    assert calls["n"] == 2


def test_gemini_429_per_minute_message(monkeypatch):
    from src.core.admin_alerts import _check_gemini

    class _Resp:
        status_code = 429
        text = '{"error": {"message": "Quota exceeded ... Please retry in 54.047s."}}'
        def json(self):
            return {"error": {"message": "You exceeded your current quota... Please retry in 54.047349933s.",
                              "status": "RESOURCE_EXHAUSTED"}}

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    import httpx as _httpx
    monkeypatch.setattr(_httpx, "post", lambda *a, **kw: _Resp())

    alert = _check_gemini()
    assert alert["level"] == "warning"
    # Must say per-minute with the retry window — NOT "daily exhausted"
    assert "54" in alert["title_en"]
    assert "per-minute" in alert["title_en"] or "20 req/min" in alert["title_en"]
    assert "daily" not in alert["title_en"].lower()


def test_gemini_429_daily_fallback_message(monkeypatch):
    from src.core.admin_alerts import _check_gemini

    class _Resp:
        status_code = 429
        text = '{"error": {"message": "Quota exceeded for metric: ..._per_day"}}'
        def json(self):
            return {"error": {"message": "You exceeded your current quota. Please retry in 36000s."}}

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    import httpx as _httpx
    monkeypatch.setattr(_httpx, "post", lambda *a, **kw: _Resp())

    alert = _check_gemini()
    assert "daily" in alert["title_en"].lower()


def test_overview_has_working_rerun_function():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src" / "templates" / "overview.html").read_text(encoding="utf-8")
    assert "async function loadSystemAlerts(force = false)" in src
    assert "onclick=\"loadSystemAlerts(true)\"" in src
    assert "?force=true" in src
