"""Regression tests for tenant KB runtime hardening (2026-09-17)."""
from pathlib import Path

import pytest

from src.agent.content_engine import content_engine
from src.agent.knowledge_base import KnowledgeBaseManager
from src.content_studio.models import ContentGenerationRequest
from src.knowledge.db_knowledge_base import db_knowledge_base
from src.knowledge.document_processor import DocumentProcessor


def test_document_processing_survives_read_only_legacy_directory(tmp_path, monkeypatch):
    """The DB upload path remains usable when Vercel rejects a local copy."""
    processor = DocumentProcessor(kb_dir=str(tmp_path))

    def reject_write(self, *args, **kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(Path, "write_text", reject_write)
    result = processor.process_text_or_markdown("catalog.txt", "منتج العميل وسعره الموثق")

    assert result["status"] == "success"
    assert result["content"].endswith("منتج العميل وسعره الموثق")
    assert result["legacy_file_saved"] is False


def test_db_mode_global_cache_is_never_loaded(monkeypatch):
    """DB mode must not query/cache all tenants' documents by filename."""
    from src.core import supabase_client

    monkeypatch.setattr(supabase_client.supabase_db, "is_connected", True)
    manager = KnowledgeBaseManager()

    def reject_global_select(*args, **kwargs):
        raise AssertionError("global kb_documents select must not occur")

    monkeypatch.setattr(supabase_client.supabase_db, "select", reject_global_select)
    manager.reload()
    assert manager.knowledge_cache == {}


def test_missing_query_embedding_uses_tenant_keyword_fallback(monkeypatch):
    """A NULL vector must not enter the semantic RPC ranking path."""
    from src.knowledge import db_knowledge_base as kb_module

    expected = [(2.0, "tenant.md", "نتيجة مطابقة بالكلمات")]
    monkeypatch.setattr(kb_module.supabase_db, "is_connected", True)
    monkeypatch.setattr(kb_module.supabase_db, "client", object())
    monkeypatch.setattr(db_knowledge_base, "_embed", lambda _query: None)
    monkeypatch.setattr(
        db_knowledge_base,
        "_fallback_keyword_search",
        lambda query, top_k, user_id=None: expected,
    )

    result = db_knowledge_base.search("سعر الباقة", top_k=3, user_id="tenant-a")

    assert result == expected


def test_chunk_embeddings_use_one_bounded_batch_request(monkeypatch):
    """Large document chunks are embedded together, not one HTTP call each."""
    from src.knowledge import db_knowledge_base as kb_module

    class BatchResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"embeddings": [{"values": [0.1] * kb_module.EMBED_DIMS}] * 2}

    called = {}

    def fake_post(url, **kwargs):
        called["url"] = url
        called["requests"] = kwargs["json"]["requests"]
        return BatchResponse()

    monkeypatch.setattr(kb_module.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(kb_module.httpx, "post", fake_post)
    db_knowledge_base._embed_cache.clear()

    vectors = db_knowledge_base._embed_many(["unique chunk alpha", "unique chunk beta"])

    assert called["url"] == kb_module.GEMINI_BATCH_EMBED_URL
    assert len(called["requests"]) == 2
    assert all(vector and len(vector) == kb_module.EMBED_DIMS for vector in vectors)


@pytest.mark.asyncio
async def test_content_prompt_is_grounded_in_only_the_callers_knowledge(monkeypatch):
    req = ContentGenerationRequest(topic="إطلاق المنتج", cta_keyword="اطلب")
    prompt = content_engine._build_gemini_prompt(
        req, "[من وثيقة: tenant-a.md] السعر المعتمد 500 جنيه"
    )

    assert "tenant-a.md" in prompt
    assert "السعر المعتمد 500 جنيه" in prompt
    assert "لا تخلط أي معلومة من نشاط آخر" in prompt

    observed = {}

    async def fake_context(request, user_id):
        observed["user_id"] = user_id
        return "معلومة خاصة بهذا العميل فقط"

    monkeypatch.setattr(content_engine, "_tenant_knowledge_context", fake_context)
    result = await content_engine.generate_content(req, user_id="tenant-a")
    assert observed["user_id"] == "tenant-a"
    assert result is not None
