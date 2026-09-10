"""
Phase 9.7 — per-user platform connections models (Pydantic v2).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

PLATFORMS = ("facebook", "instagram", "threads")


class ConnectionOut(BaseModel):
    """Safe view — NEVER exposes the token."""
    id: str
    platform: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    status: str = "active"
    scopes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    connected_at: Optional[datetime] = None


class ConnectionsOverview(BaseModel):
    """Everything the wizard/settings UI needs: what the user PAID for,
    what they CONNECTED, and discovered-but-locked upsell candidates."""
    user_id: str
    entitlements: List[str] = Field(default_factory=list)
    can_connect: bool = False
    connections: List[ConnectionOut] = Field(default_factory=list)
    upsell: List[Dict[str, Any]] = Field(default_factory=list)
