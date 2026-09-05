"""
Pydantic Models for Content Studio: Posts, Reels, Stories, and Generation.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field


class ContentPlatform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    BOTH = "both"


class PostType(str, Enum):
    POST = "post"
    REEL = "reel"
    STORY = "story"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class CreationMode(str, Enum):
    AI_GENERATED = "ai_generated"
    MANUAL = "manual"


class ContentPostBase(BaseModel):
    platform: ContentPlatform = ContentPlatform.BOTH
    post_type: PostType = PostType.POST
    content_text: str = Field(..., min_length=1, description="Post text, Reel script/caption, or Story copy")
    media_urls: List[str] = Field(default_factory=list, description="List of image or video URLs")
    status: ContentStatus = ContentStatus.DRAFT
    scheduled_for: Optional[datetime] = None
    creation_mode: CreationMode = CreationMode.MANUAL
    generation_prompt: Optional[str] = None


class ContentPostCreate(ContentPostBase):
    pass


class ContentPostUpdate(BaseModel):
    content_text: Optional[str] = None
    media_urls: Optional[List[str]] = None
    status: Optional[ContentStatus] = None
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    meta_post_id: Optional[str] = None
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None


class ContentPostResponse(ContentPostBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    published_at: Optional[datetime] = None
    meta_post_id: Optional[str] = None
    error_message: Optional[str] = None
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContentGenerationRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="The marketing topic or objective")
    post_type: PostType = Field(default=PostType.POST, description="post, reel, or story")
    platform: ContentPlatform = Field(default=ContentPlatform.BOTH)
    tone: Optional[str] = Field(default="enthusiastic_egyptian", description="Marketing tone")
    cta_keyword: Optional[str] = Field(default="ابدأ", description="Call to action keyword to trigger bot")
    target_audience: Optional[str] = Field(default="رواد أعمال ومبتدئين في التسويق")


class ContentGenerationResponse(BaseModel):
    topic: str
    post_type: PostType
    platform: ContentPlatform
    generated_text: str
    suggested_hook: Optional[str] = None
    suggested_hashtags: List[str] = Field(default_factory=list)
    script_breakdown: Optional[Dict[str, str]] = None
    cta: str
    model_used: str = "HudhudRadar Content Studio Engine"
