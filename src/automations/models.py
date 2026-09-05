from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class NodePosition(BaseModel):
    x: float
    y: float


class NodeData(BaseModel):
    id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:8]}")
    category: str  # 'trigger', 'condition', 'action'
    type: str      # e.g., 'ig_comment_trigger', 'fb_comment_trigger', 'keyword_filter', 'ai_reply_action', 'meta_dm_action', 'n8n_http_action'
    label: str
    platform: str = "both"  # 'instagram', 'facebook', 'both', 'general'
    icon: str = "⚡"
    config: Dict[str, Any] = Field(default_factory=dict)
    position: NodePosition = Field(default_factory=lambda: NodePosition(x=200, y=200))


class Connection(BaseModel):
    id: str = Field(default_factory=lambda: f"conn_{uuid.uuid4().hex[:8]}")
    from_node: str
    from_port: str = "output"
    to_node: str
    to_port: str = "input"


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    platform: str = "both"  # 'instagram', 'facebook', 'both'
    trigger_type: Optional[str] = "comment_to_dm"
    target_type: str = "all_posts"  # 'all_posts', 'specific_post'
    target_post_id: Optional[str] = None
    target_post_title: Optional[str] = None
    keywords: List[str] = Field(default_factory=lambda: ["سعر", "كورس", "تفاصيل", "مهتم"])
    like_comment: bool = True
    reply_comment: bool = True
    reply_comment_text: Optional[str] = "تم الرد في رسالة خاصة لحضرتك فوراً 🚀"
    send_dm: bool = True
    dm_text: Optional[str] = "أهلاً بك! إليك كافة التفاصيل والعرض الخاص:"
    dm_link: Optional[str] = ""
    dm_image: Optional[str] = ""
    nodes: List[NodeData] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
    status: str = "active"


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[str] = None
    trigger_type: Optional[str] = None
    target_type: Optional[str] = None
    target_post_id: Optional[str] = None
    target_post_title: Optional[str] = None
    keywords: Optional[List[str]] = None
    like_comment: Optional[bool] = None
    reply_comment: Optional[bool] = None
    reply_comment_text: Optional[str] = None
    send_dm: Optional[bool] = None
    dm_text: Optional[str] = None
    dm_link: Optional[str] = None
    dm_image: Optional[str] = None
    nodes: Optional[List[NodeData]] = None
    connections: Optional[List[Connection]] = None
    status: Optional[str] = None


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: f"wf_{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    platform: str = "both"  # 'instagram', 'facebook', 'both'
    trigger_type: str = "comment_to_dm"
    status: str = "active"  # 'active', 'paused'
    target_type: str = "all_posts"  # 'all_posts', 'specific_post'
    target_post_id: Optional[str] = None
    target_post_title: Optional[str] = None
    keywords: List[str] = Field(default_factory=lambda: ["سعر", "كورس", "تفاصيل", "مهتم"])
    like_comment: bool = True
    reply_comment: bool = True
    reply_comment_text: Optional[str] = "تم الرد في رسالة خاصة لحضرتك فوراً 🚀"
    send_dm: bool = True
    dm_text: Optional[str] = "أهلاً بك! إليك كافة التفاصيل والعرض الخاص:"
    dm_link: Optional[str] = ""
    dm_image: Optional[str] = ""
    nodes: List[NodeData] = Field(default_factory=list)
    connections: List[Connection] = Field(default_factory=list)
    executions_count: int = 0
    last_executed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
