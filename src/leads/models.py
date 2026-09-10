"""
Pydantic Models for Leads, Messages, and Provenance.
Strict validation with zero assumptions.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
import uuid
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator


class PlatformSource(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    MANUAL = "manual"
    OTHER = "other"


class SenderType(str, Enum):
    LEAD = "lead"
    AGENT = "agent"
    ADMIN = "admin"


class VerificationMethod(str, Enum):
    DIRECT = "direct"
    MANUALLY_CONFIRMED = "manually_confirmed"
    PENDING_REVIEW = "pending_review"


class DataProvenance(BaseModel):
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_platform: PlatformSource = Field(default=PlatformSource.OTHER)
    verification_method: VerificationMethod = Field(default=VerificationMethod.DIRECT)
    source_account_id: Optional[str] = None
    provenance_notes: List[str] = Field(default_factory=list)


class LeadBase(BaseModel):
    source: PlatformSource = PlatformSource.OTHER
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    facebook_account_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    threads_account_id: Optional[str] = None
    linked_account_id: Optional[str] = None
    is_verified_link: bool = False
    data_provenance: DataProvenance = Field(default_factory=DataProvenance)


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    facebook_account_id: Optional[str] = None
    instagram_account_id: Optional[str] = None
    threads_account_id: Optional[str] = None
    linked_account_id: Optional[str] = None
    is_verified_link: Optional[bool] = None
    data_provenance: Optional[DataProvenance] = None


class LeadInDB(LeadBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageCreate(BaseModel):
    lead_id: str
    platform: PlatformSource
    platform_message_id: Optional[str] = None
    sender_type: SenderType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageInDB(MessageCreate):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationQueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    primary_lead_id: str
    candidate_lead_id: str
    match_reason: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    status: str = "pending"  # pending, approved, rejected
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
