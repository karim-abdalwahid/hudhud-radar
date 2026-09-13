import asyncio
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from src.content_studio.models import ContentPostCreate, ContentPlatform, PostType, ContentStatus
from src.content_studio.service import ContentStudioService
from src.core.supabase_client import InMemoryDatabase
from src.agent.scheduler import ContentScheduler


class FakeDB(InMemoryDatabase):
    is_connected = False


service = ContentStudioService(db=FakeDB())
post = service.create_post(ContentPostCreate(
    platform=ContentPlatform.FACEBOOK, post_type=PostType.POST,
    content_text="عالق", status=ContentStatus.PUBLISHING))
service.db.update("content_posts", post.id, {
    "status": "publishing",
    "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()})

posts = service.list_posts(limit=100)
for p in posts:
    print("row:", p.status, p.updated_at, "| age-min:", (datetime.now(timezone.utc) - p.updated_at).total_seconds() / 60)

sched = ContentScheduler(service=service, publisher=MagicMock())
sched._claim_for_publish = lambda pid: True
res = asyncio.run(sched.check_and_publish_due_posts())
print("check results:", res)
print("after:", service.get_post(post.id).status)
