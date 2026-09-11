"""
Tests for Content Studio: AI Generation, Persistence, Scheduler, Meta Publishing, and REST APIs.
API tests use the authenticated admin `client` fixture from conftest.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from src.content_studio.models import (
    ContentPlatform,
    PostType,
    ContentStatus,
    CreationMode,
    ContentPostCreate,
    ContentPostUpdate,
    ContentGenerationRequest,
)
from src.content_studio.service import ContentStudioService
from src.agent.content_engine import content_engine
from src.meta_api.publishing import MetaPublisher
from src.agent.scheduler import ContentScheduler


@pytest.fixture
def test_client(client):
    """Authenticated admin client (from conftest)."""
    return client


@pytest.fixture
def content_service():
    return ContentStudioService()


# -------------------------------------------------------------
# 1. Content Engine AI Generation Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_post_aida_framework():
    """Verify generated post adheres to AIDA marketing formula and CTA keyword."""
    req = ContentGenerationRequest(
        topic="أسرار التسويق الإلكتروني لزيادة المبيعات",
        post_type=PostType.POST,
        platform=ContentPlatform.BOTH,
        cta_keyword="ابدأ",
    )
    result = await content_engine.generate_content(req)
    assert result is not None
    assert result.post_type == PostType.POST
    assert len(result.generated_text) > 50
    assert "ابدأ" in result.generated_text
    assert len(result.suggested_hashtags) >= 1
    assert result.suggested_hook is not None


@pytest.mark.asyncio
async def test_generate_reel_script_structure():
    """Verify generated Reel script includes 3-sec hook, bullet points, and CTA."""
    req = ContentGenerationRequest(
        topic="كيف تبني متجر إلكتروني ناجح",
        post_type=PostType.REEL,
        platform=ContentPlatform.INSTAGRAM,
        cta_keyword="متجر",
    )
    result = await content_engine.generate_content(req)
    assert result is not None
    assert result.post_type == PostType.REEL
    assert result.script_breakdown is not None
    assert "متجر" in result.generated_text
    assert any("Hook" in k for k in result.script_breakdown.keys())
    assert any("CTA" in k for k in result.script_breakdown.keys())


@pytest.mark.asyncio
async def test_generate_story_sequence():
    """Verify generated Story contains a 4-frame interactive sequence."""
    req = ContentGenerationRequest(
        topic="نصائح إعلانات فيسبوك الممولة",
        post_type=PostType.STORY,
        platform=ContentPlatform.BOTH,
        cta_keyword="إعلان",
    )
    result = await content_engine.generate_content(req)
    assert result is not None
    assert result.post_type == PostType.STORY
    assert result.script_breakdown is not None
    assert len(result.script_breakdown) == 4
    assert "إعلان" in result.generated_text


# -------------------------------------------------------------
# 2. Content Studio Service (CRUD) Tests
# -------------------------------------------------------------
def test_content_post_lifecycle(content_service):
    """Test full CRUD lifecycle of a content post."""
    post_in = ContentPostCreate(
        platform=ContentPlatform.FACEBOOK,
        post_type=PostType.POST,
        content_text="بوست تجريبي رقم 1 لأتمتة المحتوى",
        status=ContentStatus.DRAFT,
        creation_mode=CreationMode.MANUAL,
    )
    # 1. Create
    created = content_service.create_post(post_in)
    assert created.id is not None
    assert created.status == ContentStatus.DRAFT
    assert created.content_text == post_in.content_text

    # 2. Read
    fetched = content_service.get_post(created.id)
    assert fetched is not None
    assert fetched.id == created.id

    # 3. Update
    updated = content_service.update_post(
        created.id,
        ContentPostUpdate(
            content_text="نص معدل باحترافية",
            status=ContentStatus.SCHEDULED,
            scheduled_for=datetime.now(timezone.utc) + timedelta(hours=2),
        )
    )
    assert updated.content_text == "نص معدل باحترافية"
    assert updated.status == ContentStatus.SCHEDULED

    # 4. List with filter
    posts = content_service.list_posts(status=ContentStatus.SCHEDULED)
    assert any(p.id == created.id for p in posts)

    # 5. Delete
    deleted = content_service.delete_post(created.id)
    assert deleted is True
    assert content_service.get_post(created.id) is None


# -------------------------------------------------------------
# 3. Meta Publisher Logic Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_publish_content_facebook_feed_mock():
    """Verify Facebook feed publishing invokes Graph API endpoint."""
    publisher = MetaPublisher(access_token="fake_token", page_id="1108892288983475")
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "fb_post_9999"}
        mock_resp.headers = {}
        mock_post.return_value = mock_resp

        res = await publisher.publish_content(
            platform=ContentPlatform.FACEBOOK,
            post_type=PostType.POST,
            text="منشور تجريبي لاختبار النشر التلقائي",
        )
        assert res["success"] is True
        assert res["published_ids"].get("facebook") == "fb_post_9999"


@pytest.mark.asyncio
async def test_publish_content_instagram_requires_media():
    """Verify Instagram publishing fails gracefully if no media URL is supplied."""
    publisher = MetaPublisher(access_token="fake_token", instagram_id="17841459820747642")
    res = await publisher.publish_content(
        platform=ContentPlatform.INSTAGRAM,
        post_type=PostType.POST,
        text="منشور بدون صورة لإنستغرام",
        media_urls=[],
    )
    assert res["success"] is False
    assert "media URL" in res["errors"].get("instagram", "")


# -------------------------------------------------------------
# 4. Background Scheduler Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_scheduler_executes_due_posts(content_service):
    """Verify scheduler detects past/due posts, triggers publisher, and marks as published."""
    # Create a post scheduled in the past
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    post_in = ContentPostCreate(
        platform=ContentPlatform.FACEBOOK,
        post_type=PostType.POST,
        content_text="بوست مستحق النشر التلقائي فوراً",
        status=ContentStatus.SCHEDULED,
        scheduled_for=past_time,
    )
    post = content_service.create_post(post_in)

    mock_publisher = MagicMock()
    mock_publisher.publish_content = AsyncMock(return_value={
        "success": True,
        "published_ids": {"facebook": "fb_due_123"},
        "errors": {}
    })

    scheduler = ContentScheduler(service=content_service, publisher=mock_publisher)
    results = await scheduler.check_and_publish_due_posts()

    assert len(results) >= 1
    found = next((r for r in results if r["post_id"] == post.id), None)
    assert found is not None
    assert found["status"] == "published"

    # Verify DB record updated
    updated_db_post = content_service.get_post(post.id)
    assert updated_db_post.status == ContentStatus.PUBLISHED
    assert updated_db_post.published_at is not None


# -------------------------------------------------------------
# 5. REST API Integration Tests
# -------------------------------------------------------------
def test_api_generate_content(test_client):
    """Test POST /api/content/generate endpoint."""
    res = test_client.post("/api/content/generate", json={
        "topic": "كيف تنشئ إعلانات ناجحة",
        "post_type": "post",
        "platform": "both",
        "cta_keyword": "ابدأ"
    })
    assert res.status_code == 200
    data = res.json()
    assert "generated_text" in data
    assert data["post_type"] == "post"


def test_api_create_and_list_posts(test_client, monkeypatch):
    """Test POST and GET /api/content/posts.

    Wave 9.8: posts are stamped with the session user_id. This test runs against
    the REAL Supabase with a conftest fake user, so the session is pinned to the
    real owner row (FK-valid)."""
    import src.core.auth as core_auth
    OWNER_ID = "8d0ab6c3-544d-4a14-84c9-d021acf26ddf"
    real_verify = core_auth.verify_session_token
    monkeypatch.setattr(core_auth, "verify_session_token",
                        lambda token: {"sub": OWNER_ID, "role": "admin"} if token else None)

    create_res = test_client.post("/api/content/posts", json={
        "platform": "both",
        "post_type": "post",
        "content_text": "منشور من خلال واجهة برمجة التطبيقات API",
        "status": "draft",
        "media_urls": ["https://example.com/photo.jpg"]
    })
    assert create_res.status_code == 200
    post_data = create_res.json()
    post_id = post_data["id"]

    # List
    list_res = test_client.get("/api/content/posts")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["id"] == post_id for item in items)

    # Delete
    del_res = test_client.delete(f"/api/content/posts/{post_id}")
    assert del_res.status_code == 200
