"""
Tests for Multi-Tenant Social Knowledge Ingestion (POST /api/knowledge/sync-meta).
Verifies per-user extraction from TenantFeedService into kb_documents.
"""
import pytest
from unittest.mock import AsyncMock, patch
from starlette.testclient import TestClient

from src.main import app
from src.core.auth import create_session_token, SESSION_COOKIE_NAME


@pytest.fixture
def auth_client():
    client = TestClient(app)
    token = create_session_token("tenant-user-456", "user", "tenant@test.com")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    return client


def test_sync_meta_unauthenticated():
    client = TestClient(app)
    resp = client.post("/api/knowledge/sync-meta")
    assert resp.status_code == 401


def test_sync_meta_no_posts(auth_client, monkeypatch):
    from src.modules.meta.tenant_feed_service import tenant_feed_service
    monkeypatch.setattr(tenant_feed_service, "get_tenant_posts", AsyncMock(return_value=[]))

    resp = auth_client.post("/api/knowledge/sync-meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "skipped"
    assert data["synced_posts"] == 0


def test_sync_meta_with_real_posts(auth_client, monkeypatch):
    from src.modules.meta.tenant_feed_service import tenant_feed_service
    from src.knowledge.db_knowledge_base import db_knowledge_base

    mock_posts = [
        {
            "id": "fb_101",
            "platform": "facebook",
            "content_text": "عرض حصري: خصم 30% على خدمات التسويق وإدارة الحملات الرقمية هذا الأسبوع!",
            "published_at": "2026-09-20T12:00:00Z",
            "permalink": "https://facebook.com/101",
            "metrics": {"likes": 45, "comments": 12},
        },
        {
            "id": "ig_202",
            "platform": "instagram",
            "content_text": "ريلز جديد: كيف تصنع روبوت مبيعات ذكي يرد على استفسارات عملائك على مدار الساعة.",
            "published_at": "2026-09-21T15:30:00Z",
            "permalink": "https://instagram.com/p/202",
            "metrics": {"likes": 120, "comments": 34},
        },
        {
            "id": "th_303",
            "platform": "threads",
            "content_text": "ثريد سريع: أهم 5 أخطاء يقع فيها رواد الأعمال عند الرد على العملاء في الخاص.",
            "published_at": "2026-09-22T09:00:00Z",
            "permalink": "https://threads.net/@user/post/303",
            "metrics": {"likes": 15, "comments": 3},
        },
    ]

    saved_docs = {}

    def mock_save(filename, content, user_id=None):
        saved_docs[filename] = {"content": content, "user_id": user_id}
        return {"status": "success", "filename": filename, "words_count": len(content.split())}

    monkeypatch.setattr(tenant_feed_service, "get_tenant_posts", AsyncMock(return_value=mock_posts))
    monkeypatch.setattr(db_knowledge_base, "save_document", mock_save)

    resp = auth_client.post("/api/knowledge/sync-meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["synced_posts"] == 3
    assert data["filename"] == "social_posts_knowledge.md"
    assert data["words_count"] > 0

    # Verify saved document content
    assert "social_posts_knowledge.md" in saved_docs
    doc = saved_docs["social_posts_knowledge.md"]
    assert doc["user_id"] == "tenant-user-456"
    assert "عرض حصري: خصم 30%" in doc["content"]
    assert "FACEBOOK" in doc["content"]
    assert "INSTAGRAM" in doc["content"]
    assert "THREADS" in doc["content"]
