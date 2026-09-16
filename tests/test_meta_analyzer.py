"""
Tests for the Structured Meta Posts Analyzer (owner-approved prompt).
All Gemini + Graph API calls mocked; DB KB isolated via tmp file mode (conftest).
"""
import json

import pytest

from src.knowledge.meta_analyzer import MetaPostsAnalyzer


def _valid_analysis(pid="p1"):
    return {
        "post_id": pid,
        "published_summary": "نشر عن الريلز",
        "promises": [{"claim": "خريطة القنوات", "evidence": "[منشور:p1]"}],
        "cta_requested": {"keyword_or_action": "ابدأ", "quote_from_post": "اكتب ابدأ"},
        "comment_counts": {"total": 2, "cta_response": 1, "real_question": 1,
                           "complaint": 0, "spam": 0, "compliment": 0, "other": 0},
        "comment_classification": [
            {"comment_id": "c1", "text": "ابدأ", "type": "cta_response", "reason": "كلمة الـ CTA"},
            {"comment_id": "c2", "text": "بكام؟", "type": "real_question", "reason": "سؤال سعر"},
        ],
        "audience_real_questions": [{"topic": "السعر", "evidence": ["[تعليق:c2]"]}],
        "recurring_needs": ["السعر"],
        "gaps": ["لا يوجد رد صريح على السؤال الحقيقي"],
        "content_lessons": ["CTA شغال لكن الرد على الأسئلة الحقيقية أسرع"],
        "confidence": "high",
    }


def _async_return(items):
    async def inner(*args, **kwargs):
        return items
    return inner


class _FakeResp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body) if isinstance(body, dict) else str(body)
    def json(self):
        return self._body


class _FakeClientCtx:
    def __init__(self, responder):
        self._responder = responder
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        return False
    async def post(self, *a, **kw):
        return self._responder()


@pytest.fixture
def analyzer(monkeypatch):
    # conftest forces GEMINI_API_KEY=None for LLM isolation; restore a fake key
    # since all Gemini HTTP calls here are mocked anyway.
    from src.config import settings as _settings
    monkeypatch.setattr(_settings, "GEMINI_API_KEY", "test-key")
    a = MetaPostsAnalyzer()
    a._fetch_comments = _async_return([
        {"id": "c1", "message": "ابدأ"},
        {"id": "c2", "message": "بكام؟"},
    ])
    return a


@pytest.mark.asyncio
async def test_analyze_one_parses_strict_json(analyzer, monkeypatch):
    resp = _FakeResp(200, {"candidates": [{"content": {"parts": [
        {"text": json.dumps(_valid_analysis(), ensure_ascii=False)}
    ]}}]})

    class Ctx(_FakeClientCtx):
        async def post(self, *a, **kw):
            return resp

    monkeypatch.setattr("src.knowledge.meta_analyzer.httpx.AsyncClient", lambda **kw: Ctx(resp))
    post = {"id": "p1", "content_text": "اكتب ابدأ", "published_at": "", "platform": "instagram", "post_type": "reel"}
    result = await analyzer._analyze_one(post, [{"id": "c1", "message": "ابدأ"}, {"id": "c2", "message": "بكام؟"}])
    assert result is not None
    assert result["cta_requested"]["keyword_or_action"] == "ابدأ"
    assert result["comment_counts"]["cta_response"] == 1
    assert result["comment_counts"]["real_question"] == 1


@pytest.mark.asyncio
async def test_analyze_one_rejects_non_json(analyzer, monkeypatch):
    resp = _FakeResp(200, {"candidates": [{"content": {"parts": [
        {"text": "هذا تحليل نصي بلا JSON"}
    ]}}]})

    monkeypatch.setattr("src.knowledge.meta_analyzer.httpx.AsyncClient", lambda **kw: _FakeClientCtx(lambda: resp))
    result = await analyzer._analyze_one({"id": "p2", "content_text": "x"}, [])
    assert result is None  # non-JSON rejected — no fabrication


@pytest.mark.asyncio
async def test_analyze_one_retries_503_then_fails_cleanly(analyzer, monkeypatch, tmp_path):
    import asyncio as aio
    calls = {"n": 0}

    def responder():
        calls["n"] += 1
        return _FakeResp(503, {})

    monkeypatch.setattr("src.knowledge.meta_analyzer.httpx.AsyncClient", lambda **kw: _FakeClientCtx(responder))
    monkeypatch.setattr(aio, "sleep", _async_return(None))
    result = await analyzer._analyze_one({"id": "p3", "content_text": "x"}, [])
    assert result is None
    assert calls["n"] == 3  # retried exactly 3 times


@pytest.mark.asyncio
async def test_full_pipeline_refuses_global_meta_feed(analyzer):
    """No analyzer may consume the old globally cached Meta posts."""
    res = await analyzer.analyze_recent(limit=5, user_id="tenant-a")
    assert res["status"] == "skipped"
    assert "per-account" in res["reason"]


@pytest.mark.asyncio
async def test_analyzer_requires_tenant_owner(analyzer):
    res = await analyzer.analyze_recent(limit=3)
    assert res["status"] == "skipped"
    assert "tenant owner" in res["reason"]
