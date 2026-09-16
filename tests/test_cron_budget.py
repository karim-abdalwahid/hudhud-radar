"""Regression: cron budget state machine — short ticks, container resume,
stuck requeue, per-tick cap, and always-200 cron routes."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.content_studio.models import (ContentPlatform, ContentPostCreate,
                                       ContentStatus, ContentPostUpdate, PostType)
from src.content_studio.service import ContentStudioService
from src.core.supabase_client import InMemoryDatabase
from src.agent.scheduler import ContentScheduler


class FakeDB(InMemoryDatabase):
    is_connected = False


TEST_OWNER = "tenant-cron"


def make_service():
    return ContentStudioService(db=FakeDB())


def scheduled_ig(service):
    return service.create_post(ContentPostCreate(
        platform=ContentPlatform.INSTAGRAM, post_type=PostType.POST,
        content_text="منشور اختبار كرون", status=ContentStatus.SCHEDULED,
        media_urls=["https://cdn.example.com/i.jpg"],
        scheduled_for=datetime.now(timezone.utc) - timedelta(minutes=5)),
        user_id=TEST_OWNER)


def make_scheduler(service, publisher):
    s = ContentScheduler(service=service, publisher=publisher)
    s._claim_for_publish = lambda pid: True
    return s


@pytest.fixture
def compliant(monkeypatch):
    import src.content_studio.compliance_agent as ca
    v = MagicMock(is_compliant=True, warnings=[], quality_score=95)
    monkeypatch.setattr(ca.compliance_gatekeeper, "audit_content", lambda **k: v)
    return v


def test_ig_container_queues_then_resumes(compliant):
    service = make_service()
    post = scheduled_ig(service)
    pub = MagicMock()
    pub.create_instagram_container = AsyncMock(return_value="cid-1")
    polls = [False, True]
    pub.wait_for_instagram_container_ready = AsyncMock(side_effect=lambda *a, **k: polls.pop(0))
    pub.publish_instagram_container = AsyncMock(return_value={"id": "ig-99"})
    sched = make_scheduler(service, pub)

    r1 = _run(sched.check_and_publish_due_posts())
    assert r1[0]["status"] == "ig_container_queued"
    cur = service.get_post(post.id)
    assert cur.status == ContentStatus.PUBLISHING
    assert (cur.performance_metrics or {}).get("ig_container_id") == "cid-1"
    assert pub.wait_for_instagram_container_ready.await_count == 0  # no blocking wait

    r2 = _run(sched.check_and_publish_due_posts())  # not ready yet
    assert r2[0]["status"] == "awaiting_container"
    assert service.get_post(post.id).status == ContentStatus.PUBLISHING

    r3 = _run(sched.check_and_publish_due_posts())  # ready -> publish
    assert r3[0]["status"] == "published"
    final = service.get_post(post.id)
    assert final.status == ContentStatus.PUBLISHED
    assert "ig-99" in (final.meta_post_id or "")


def test_stuck_publishing_requeued(compliant):
    service = make_service()
    post = service.create_post(ContentPostCreate(
        platform=ContentPlatform.FACEBOOK, post_type=PostType.POST,
        content_text="بوست عالق", status=ContentStatus.PUBLISHING),
        user_id=TEST_OWNER)
    # age it beyond the stuck window (patch the raw row: the memory-store
    # update() helper always re-stamps updated_at itself)
    for row in service.db.tables["content_posts"]:
        if row["id"] == post.id:
            row["updated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    sched = make_scheduler(service, MagicMock())
    _run(sched.check_and_publish_due_posts())
    assert service.get_post(post.id).status == ContentStatus.SCHEDULED


def test_tick_caps_new_starts(compliant):
    service = make_service()
    for i in range(4):
        scheduled_ig(service)
    pub = MagicMock()
    pub.create_instagram_container = AsyncMock(return_value="c")
    pub.wait_for_instagram_container_ready = AsyncMock(return_value=False)
    sched = make_scheduler(service, pub)
    results = _run(sched.check_and_publish_due_posts())
    assert len([r for r in results if r.get("status") == "ig_container_queued"]) == sched.MAX_STARTS_PER_TICK
    # remaining due posts untouched for next tick
    pub.create_instagram_container.assert_called()


def test_cron_route_always_200_on_failure(client, monkeypatch):
    from src.config import settings
    import src.agent.scheduler as sch_mod
    async def boom():
        raise RuntimeError("simulated timeout crash")
    monkeypatch.setattr(sch_mod.content_scheduler, "check_and_publish_due_posts", boom)
    r = client.get(f"/api/cron/scheduler-tick?key={settings.CRON_SECRET}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "partial"
    assert "simulated" in body.get("error", "")


def _run(coro):
    import asyncio
    return asyncio.run(coro)
