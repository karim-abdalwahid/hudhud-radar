"""
Content Studio Service: CRUD and State Management for Content Posts.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import json

from src.core.supabase_client import supabase_db
from src.core.logger import logger
from .models import (
    ContentPostCreate,
    ContentPostUpdate,
    ContentPostResponse,
    ContentStatus,
    ContentPlatform,
    PostType,
)


class ContentStudioService:
    """Service handling storage and lifecycle of posts, reels, and stories."""

    def __init__(self, db=None):
        self.db = db or supabase_db
        self.table = "content_posts"

    def create_post(self, post_in: ContentPostCreate, user_id: Optional[str] = None) -> ContentPostResponse:
        """Create a new post/reel/story record (owned by the session user — Wave 9.8)."""
        if not user_id:
            raise ValueError("A tenant owner is required to create content")
        now = datetime.now(timezone.utc).isoformat()
        row_id = str(uuid.uuid4())
        
        row_data = {
            "id": row_id,
            "platform": post_in.platform.value if hasattr(post_in.platform, 'value') else post_in.platform,
            "post_type": post_in.post_type.value if hasattr(post_in.post_type, 'value') else post_in.post_type,
            "content_text": post_in.content_text,
            "media_urls": post_in.media_urls,
            "status": post_in.status.value if hasattr(post_in.status, 'value') else post_in.status,
            "scheduled_for": post_in.scheduled_for.isoformat() if post_in.scheduled_for else None,
            "creation_mode": post_in.creation_mode.value if hasattr(post_in.creation_mode, 'value') else post_in.creation_mode,
            "generation_prompt": post_in.generation_prompt,
            "performance_metrics": {},
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
        }

        inserted = self.db.insert(self.table, row_data)
        logger.info("Content post created successfully", extra={"post_id": row_id, "platform": row_data["platform"]})
        return ContentPostResponse(**inserted)

    def get_post(self, post_id: str, user_id: Optional[str] = None) -> Optional[ContentPostResponse]:
        """Fetch a single post, optionally restricted to its tenant owner."""
        filters = {"id": post_id}
        if user_id:
            filters["user_id"] = user_id
        rows = self.db.select(self.table, filters)
        if rows:
            return ContentPostResponse(**rows[0])
        return None

    def list_posts(self, status: Optional[ContentStatus] = None, platform: Optional[ContentPlatform] = None, limit: int = 50, user_id: Optional[str] = None) -> List[ContentPostResponse]:
        """List posts with optional filters (per-user scoped when user_id provided — Wave 9.8)."""
        filters = {}
        if status:
            filters["status"] = status.value if hasattr(status, 'value') else status
        if platform:
            filters["platform"] = platform.value if hasattr(platform, 'value') else platform
        if user_id:
            filters["user_id"] = user_id

        rows = self.db.select(self.table, filters if filters else None)
        # Sort descending by created_at
        rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [ContentPostResponse(**r) for r in rows[:limit]]

    def update_post(self, post_id: str, updates: ContentPostUpdate,
                    user_id: Optional[str] = None) -> Optional[ContentPostResponse]:
        """Update a post, rejecting an id outside the caller's tenant when scoped."""
        if user_id and not self.get_post(post_id, user_id=user_id):
            return None
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        if "status" in update_data and hasattr(update_data["status"], "value"):
            update_data["status"] = update_data["status"].value
        if "scheduled_for" in update_data and isinstance(update_data["scheduled_for"], datetime):
            update_data["scheduled_for"] = update_data["scheduled_for"].isoformat()
        if "published_at" in update_data and isinstance(update_data["published_at"], datetime):
            update_data["published_at"] = update_data["published_at"].isoformat()
            
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated = self.db.update(self.table, post_id, update_data)
        if updated:
            return ContentPostResponse(**updated)
        return None

    def delete_post(self, post_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a post, rejecting an id outside the caller's tenant when scoped."""
        if user_id and not self.get_post(post_id, user_id=user_id):
            return False
        return self.db.delete(self.table, post_id)
