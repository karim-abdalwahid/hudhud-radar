import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from src.core.auth import create_session_token, SESSION_COOKIE_NAME
from src.modules.meta.tenant_feed_service import TenantFeedService


@pytest.fixture
def client():
    return TestClient(app)


def test_meta_posts_requires_auth(client):
    """GET /api/meta/posts requires session authentication."""
    resp = client.get("/api/meta/posts")
    assert resp.status_code == 401


def test_meta_sync_posts_requires_auth(client):
    """POST /api/meta/sync-posts requires session authentication."""
    resp = client.post("/api/meta/sync-posts")
    assert resp.status_code == 401


def test_meta_posts_empty_when_no_connections(client):
    """Returns empty posts list gracefully when user has no connected accounts."""
    token = create_session_token("user_no_conn_123", "user", "user_test@hudhd.test")
    client.cookies.set(SESSION_COOKIE_NAME, token)

    with patch("src.modules.connections.service.connection_service.get_publish_credentials", return_value=None), \
         patch("src.modules.connections.service.connection_service.get_active_token", return_value=None):
        resp = client.get("/api/meta/posts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["posts"] == []


def test_meta_sync_posts_for_tenant(client):
    """POST /api/meta/sync-posts succeeds for normal tenant users."""
    token = create_session_token("user_normal_456", "user", "normal@hudhd.test")
    client.cookies.set(SESSION_COOKIE_NAME, token)

    with patch("src.modules.connections.service.connection_service.get_publish_credentials", return_value=None), \
         patch("src.modules.connections.service.connection_service.get_active_token", return_value=None):
        resp = client.post("/api/meta/sync-posts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["synced"] == 0


@pytest.mark.asyncio
async def test_tenant_feed_service_facebook():
    """Verifies TenantFeedService correctly normalizes Facebook posts."""
    service = TenantFeedService()

    fb_creds = {"access_token": "fake_fb_token", "account_id": "page_999"}
    mock_fb_response = MagicMock()
    mock_fb_response.status_code = 200
    mock_fb_response.json.return_value = {
        "data": [
            {
                "id": "page_999_post_1",
                "message": "Welcome to our Facebook Page!",
                "created_time": "2026-09-20T12:00:00+0000",
                "full_picture": "https://example.com/pic.jpg",
                "permalink_url": "https://facebook.com/post_1",
                "shares": {"count": 5},
                "reactions": {"summary": {"total_count": 42}},
                "comments": {"summary": {"total_count": 8}},
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_fb_response

    with patch("src.modules.connections.service.connection_service.get_publish_credentials", return_value=fb_creds):
        posts = await service._fetch_facebook_posts(mock_client, "user_1", limit=10)
        assert len(posts) == 1
        p = posts[0]
        assert p["id"] == "page_999_post_1"
        assert p["platform"] == "facebook"
        assert p["post_type"] == "post"
        assert p["content_text"] == "Welcome to our Facebook Page!"
        assert p["likes_count"] == 42
        assert p["comments_count"] == 8
        assert p["shares_count"] == 5
        assert p["thumbnail_url"] == "https://example.com/pic.jpg"


@pytest.mark.asyncio
async def test_tenant_feed_service_instagram_reel():
    """Verifies TenantFeedService identifies reels vs posts on Instagram."""
    service = TenantFeedService()

    ig_creds = {"access_token": "fake_ig_token", "account_id": "ig_123"}
    mock_ig_response = MagicMock()
    mock_ig_response.status_code = 200
    mock_ig_response.json.return_value = {
        "data": [
            {
                "id": "media_reel_1",
                "caption": "Check out our new reel!",
                "media_type": "VIDEO",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "media_url": "https://example.com/video.mp4",
                "permalink": "https://instagram.com/reel/1",
                "timestamp": "2026-09-21T15:00:00+0000",
                "like_count": 120,
                "comments_count": 15,
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_ig_response

    with patch("src.modules.connections.service.connection_service.get_publish_credentials", return_value=ig_creds):
        posts = await service._fetch_instagram_media(mock_client, "user_1", limit=10)
        assert len(posts) == 1
        p = posts[0]
        assert p["id"] == "media_reel_1"
        assert p["platform"] == "instagram"
        assert p["post_type"] == "reel"
        assert p["content_text"] == "Check out our new reel!"
        assert p["likes_count"] == 120
        assert p["comments_count"] == 15
        assert p["thumbnail_url"] == "https://example.com/thumb.jpg"


@pytest.mark.asyncio
async def test_tenant_feed_service_threads():
    """Verifies TenantFeedService correctly normalizes Threads."""
    service = TenantFeedService()

    mock_th_response = MagicMock()
    mock_th_response.status_code = 200
    mock_th_response.json.return_value = {
        "data": [
            {
                "id": "thread_abc_1",
                "text": "Hello Threads from Hudhud!",
                "timestamp": "2026-09-22T08:00:00+0000",
                "media_url": "https://example.com/th_pic.jpg",
                "permalink": "https://threads.net/t/1",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_th_response

    with patch("src.modules.connections.service.connection_service.get_active_token", return_value="th_token_val"):
        posts = await service._fetch_threads_posts(mock_client, "user_1", limit=10)
        assert len(posts) == 1
        p = posts[0]
        assert p["id"] == "thread_abc_1"
        assert p["platform"] == "threads"
        assert p["post_type"] == "post"
        assert p["content_text"] == "Hello Threads from Hudhud!"
