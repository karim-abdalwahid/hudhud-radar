from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

import httpx
from src.config import settings
from src.core.logger import logger
from src.automations.models import Workflow, WorkflowCreate, WorkflowUpdate, NodeData, NodePosition, Connection

STORE_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "automations_store.json"


def _get_default_workflows() -> List[Dict[str, Any]]:
    return [
        {
            "id": "wf_ig_reel_sales",
            "name": "Instagram Reel Viral Comment-to-DM Sales Closer",
            "description": "Monitors Reel comments for keywords [سوشيال, كورس, تفاصيل], delivers immediate DM pitch, and auto-qualifies the lead in CRM.",
            "platform": "instagram",
            "trigger_type": "comment_to_dm",
            "status": "active",
            "target_type": "all_posts",
            "target_post_id": None,
            "target_post_title": "All Reels & Posts",
            "keywords": ["سوشيال", "كورس", "تفاصيل", "سعر", "مهتم"],
            "like_comment": True,
            "reply_comment": True,
            "reply_comment_text": "تم إرسال كافة التفاصيل في رسالة خاصة لحضرتك على الدايركت فوراً 🚀",
            "send_dm": True,
            "dm_text": "أهلاً بحضرتك! إليك تفاصيل الكورس والعرض الخاص لليوم:",
            "dm_link": "https://hudhud.ai/social-course",
            "dm_image": "",
            "executions_count": 142,
            "last_executed_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [
                {
                    "id": "node_trig_1",
                    "category": "trigger",
                    "type": "ig_comment_trigger",
                    "label": "Instagram Reel Comment",
                    "platform": "instagram",
                    "icon": "📸",
                    "config": {
                        "keywords": ["سوشيال", "كورس", "تفاصيل", "سعر", "مهتم"],
                        "match_type": "any"
                    },
                    "position": {"x": 100, "y": 220}
                },
                {
                    "id": "node_cond_1",
                    "category": "condition",
                    "type": "keyword_filter",
                    "label": "Intent & Keyword Filter",
                    "platform": "general",
                    "icon": "🔍",
                    "config": {
                        "filter_mode": "contains_commercial_intent",
                        "exclude_spam": True
                    },
                    "position": {"x": 420, "y": 220}
                },
                {
                    "id": "node_act_1",
                    "category": "action",
                    "type": "ai_reply_action",
                    "label": "Gemini Sales Pitch Synthesizer",
                    "platform": "general",
                    "icon": "🤖",
                    "config": {
                        "tone": "egyptian_professional",
                        "include_offer": True,
                        "discount_code": "HUDHUD20"
                    },
                    "position": {"x": 750, "y": 140}
                },
                {
                    "id": "node_act_2",
                    "category": "action",
                    "type": "meta_dm_action",
                    "label": "Send Instagram Direct Message",
                    "platform": "instagram",
                    "icon": "💬",
                    "config": {
                        "cta_button": "Book Free 15-min Call",
                        "calendar_link": "https://calendar.app.google/hudhud-meeting"
                    },
                    "position": {"x": 1080, "y": 140}
                },
                {
                    "id": "node_act_3",
                    "category": "action",
                    "type": "crm_lead_action",
                    "label": "Capture & Qualify in CRM",
                    "platform": "general",
                    "icon": "🎯",
                    "config": {
                        "stage": "qualified",
                        "deal_value": 250,
                        "tag": "Reels_Lead"
                    },
                    "position": {"x": 750, "y": 340}
                }
            ],
            "connections": [
                {"id": "c1", "from_node": "node_trig_1", "from_port": "output", "to_node": "node_cond_1", "to_port": "input"},
                {"id": "c2", "from_node": "node_cond_1", "from_port": "output", "to_node": "node_act_1", "to_port": "input"},
                {"id": "c3", "from_node": "node_act_1", "from_port": "output", "to_node": "node_act_2", "to_port": "input"},
                {"id": "c4", "from_node": "node_cond_1", "from_port": "output", "to_node": "node_act_3", "to_port": "input"}
            ],
            "created_at": "2026-09-01T10:00:00Z",
            "updated_at": "2026-09-04T12:00:00Z"
        },
        {
            "id": "wf_fb_comment_responder",
            "name": "Facebook Post & Reel Public + DM Responder",
            "description": "Engages Facebook Page post and video reel comments with a public acknowledgement and an automated Messenger inquiry.",
            "platform": "facebook",
            "trigger_type": "comment_to_dm",
            "status": "active",
            "target_type": "all_posts",
            "target_post_id": None,
            "target_post_title": "All Facebook Posts & Reels",
            "keywords": ["تفاصيل", "سعر", "مهتم", "خدمات", "عرض"],
            "like_comment": True,
            "reply_comment": True,
            "reply_comment_text": "أهلاً بك! تم إرسال كافة التفاصيل في رسالة خاصة لحضرتك فوراً 🚀",
            "send_dm": True,
            "dm_text": "مرحباً بحضرتك! استفسارك بخصوص الخدمة محل اهتمامنا، تفضل بالاطلاع على التفاصيل:",
            "dm_link": "https://hudhud.ai/services",
            "dm_image": "",
            "executions_count": 89,
            "last_executed_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [
                {
                    "id": "node_fb_trig",
                    "category": "trigger",
                    "type": "fb_comment_trigger",
                    "label": "Facebook Post / Reel Comment",
                    "platform": "facebook",
                    "icon": "📘",
                    "config": {
                        "pages": ["1108892288983475"],
                        "trigger_on": "all_comments"
                    },
                    "position": {"x": 100, "y": 200}
                },
                {
                    "id": "node_fb_pub_reply",
                    "category": "action",
                    "type": "fb_public_reply",
                    "label": "Reply to Public Comment",
                    "platform": "facebook",
                    "icon": "📢",
                    "config": {
                        "reply_template": "أهلاً بك! تم إرسال كافة التفاصيل في رسالة خاصة لحضرتك فوراً 🚀"
                    },
                    "position": {"x": 450, "y": 120}
                },
                {
                    "id": "node_fb_messenger_dm",
                    "category": "action",
                    "type": "fb_send_message",
                    "label": "Send Messenger Private Message",
                    "platform": "facebook",
                    "icon": "💬",
                    "config": {
                        "message_text": "مرحباً بحضرتك! استفسارك بخصوص الخدمة محل اهتمامنا، تفضل بالاطلاع على التفاصيل:",
                        "attach_booking_link": True
                    },
                    "position": {"x": 450, "y": 300}
                }
            ],
            "connections": [
                {"id": "cfb1", "from_node": "node_fb_trig", "from_port": "output", "to_node": "node_fb_pub_reply", "to_port": "input"},
                {"id": "cfb2", "from_node": "node_fb_trig", "from_port": "output", "to_node": "node_fb_messenger_dm", "to_port": "input"}
            ],
            "created_at": "2026-09-02T11:00:00Z",
            "updated_at": "2026-09-04T13:00:00Z"
        },
        {
            "id": "wf_n8n_http_bridge",
            "name": "n8n / External Webhook Lead Forwarder",
            "description": "Dispatches qualified high-intent social conversations to external n8n HTTP Request API nodes or Make.com webhooks.",
            "platform": "both",
            "trigger_type": "webhook",
            "status": "active",
            "executions_count": 34,
            "last_executed_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [
                {
                    "id": "node_lead_trig",
                    "category": "trigger",
                    "type": "lead_qualified_trigger",
                    "label": "Lead Form / Phone Confirmed",
                    "platform": "both",
                    "icon": "⭐",
                    "config": {"min_deal_value": 100},
                    "position": {"x": 120, "y": 200}
                },
                {
                    "id": "node_http_n8n",
                    "category": "action",
                    "type": "n8n_http_action",
                    "label": "HTTP Request Node (n8n API format)",
                    "platform": "general",
                    "icon": "🌐",
                    "config": {
                        "method": "POST",
                        "url": "https://n8n.webhook.internal/webhook/hudhud-leads",
                        "headers": {"Content-Type": "application/json", "Authorization": "Bearer n8n_sec_token"},
                        "retry_count": 3
                    },
                    "position": {"x": 500, "y": 200}
                }
            ],
            "connections": [
                {"id": "cn8n1", "from_node": "node_lead_trig", "from_port": "output", "to_node": "node_http_n8n", "to_port": "input"}
            ],
            "created_at": "2026-09-03T14:00:00Z",
            "updated_at": "2026-09-04T14:00:00Z"
        }
    ]


class AutomationsService:
    """Manages storage, lifecycle, and execution of visual automation workflows."""

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Loads workflows from JSON file or initializes defaults."""
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        if STORE_PATH.exists():
            try:
                data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
                for item in data.get("workflows", []):
                    wf = Workflow(**item)
                    self._workflows[wf.id] = wf
                logger.info(f"Loaded {len(self._workflows)} workflows from {STORE_PATH}")
                return
            except Exception as e:
                logger.error(f"Error loading automations store: {e}")

        # Initialize defaults
        defaults = _get_default_workflows()
        for item in defaults:
            wf = Workflow(**item)
            self._workflows[wf.id] = wf
        self._save_to_disk()

    def _save_to_disk(self):
        """Saves workflows to disk."""
        try:
            try:
                STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total_count": len(self._workflows),
                "workflows": [wf.model_dump() for wf in self._workflows.values()]
            }
            STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist automations store to disk (ephemeral/serverless environment): {e}")

    def list_workflows(self) -> List[Workflow]:
        return list(self._workflows.values())

    def get_workflow(self, wf_id: str) -> Optional[Workflow]:
        return self._workflows.get(wf_id)

    def create_workflow(self, payload: WorkflowCreate) -> Workflow:
        now = datetime.now(timezone.utc).isoformat()
        wf_id = f"wf_{uuid.uuid4().hex[:8]}"
        
        nodes = payload.nodes
        connections = payload.connections

        # Auto-generate visual nodes if not provided
        if not nodes:
            platform_icon = "📸" if payload.platform == "instagram" else ("📘" if payload.platform == "facebook" else "⚡")
            nodes = [
                NodeData(
                    id=f"node_trig_{wf_id[:6]}",
                    category="trigger",
                    type="comment_trigger",
                    label=f"{payload.platform.capitalize()} Reel / Post Comment",
                    platform=payload.platform,
                    icon=platform_icon,
                    config={
                        "target_type": payload.target_type,
                        "target_post_id": payload.target_post_id,
                        "target_post_title": payload.target_post_title,
                        "keywords": payload.keywords
                    },
                    position=NodePosition(x=100, y=200)
                ),
                NodeData(
                    id=f"node_filter_{wf_id[:6]}",
                    category="condition",
                    type="keyword_filter",
                    label="Keywords & Intent Filter",
                    platform="general",
                    icon="🔍",
                    config={"keywords": payload.keywords},
                    position=NodePosition(x=420, y=200)
                )
            ]
            connections = [
                Connection(
                    id=f"conn_1_{wf_id[:6]}",
                    from_node=nodes[0].id,
                    from_port="output",
                    to_node=nodes[1].id,
                    to_port="input"
                )
            ]

            if payload.reply_comment or payload.like_comment:
                nodes.append(NodeData(
                    id=f"node_reply_{wf_id[:6]}",
                    category="action",
                    type="comment_reply_action",
                    label="Public Comment Reply & Like",
                    platform=payload.platform,
                    icon="📢",
                    config={
                        "like_comment": payload.like_comment,
                        "reply_text": payload.reply_comment_text
                    },
                    position=NodePosition(x=750, y=140)
                ))
                connections.append(Connection(
                    id=f"conn_2_{wf_id[:6]}",
                    from_node=nodes[1].id,
                    from_port="output",
                    to_node=nodes[-1].id,
                    to_port="input"
                ))

            if payload.send_dm:
                nodes.append(NodeData(
                    id=f"node_dm_{wf_id[:6]}",
                    category="action",
                    type="meta_dm_action",
                    label=f"Send {payload.platform.capitalize()} Direct Message",
                    platform=payload.platform,
                    icon="💬",
                    config={
                        "dm_text": payload.dm_text,
                        "dm_link": payload.dm_link,
                        "dm_image": payload.dm_image
                    },
                    position=NodePosition(x=750 if not payload.reply_comment else 1050, y=260 if payload.reply_comment else 200)
                ))
                connections.append(Connection(
                    id=f"conn_3_{wf_id[:6]}",
                    from_node=nodes[1].id,
                    from_port="output",
                    to_node=nodes[-1].id,
                    to_port="input"
                ))

        wf = Workflow(
            id=wf_id,
            name=payload.name,
            description=payload.description or "",
            platform=payload.platform,
            trigger_type=payload.trigger_type or "comment_to_dm",
            status=payload.status,
            target_type=payload.target_type,
            target_post_id=payload.target_post_id,
            target_post_title=payload.target_post_title,
            keywords=payload.keywords,
            like_comment=payload.like_comment,
            reply_comment=payload.reply_comment,
            reply_comment_text=payload.reply_comment_text,
            send_dm=payload.send_dm,
            dm_text=payload.dm_text,
            dm_link=payload.dm_link,
            dm_image=payload.dm_image,
            nodes=nodes,
            connections=connections,
            executions_count=0,
            created_at=now,
            updated_at=now
        )
        self._workflows[wf_id] = wf
        self._save_to_disk()
        return wf

    def update_workflow(self, wf_id: str, payload: WorkflowUpdate) -> Optional[Workflow]:
        wf = self._workflows.get(wf_id)
        if not wf:
            return None
        
        if payload.name is not None:
            wf.name = payload.name
        if payload.description is not None:
            wf.description = payload.description
        if payload.platform is not None:
            wf.platform = payload.platform
        if payload.trigger_type is not None:
            wf.trigger_type = payload.trigger_type
        if payload.target_type is not None:
            wf.target_type = payload.target_type
        if payload.target_post_id is not None:
            wf.target_post_id = payload.target_post_id
        if payload.target_post_title is not None:
            wf.target_post_title = payload.target_post_title
        if payload.keywords is not None:
            wf.keywords = payload.keywords
        if payload.like_comment is not None:
            wf.like_comment = payload.like_comment
        if payload.reply_comment is not None:
            wf.reply_comment = payload.reply_comment
        if payload.reply_comment_text is not None:
            wf.reply_comment_text = payload.reply_comment_text
        if payload.send_dm is not None:
            wf.send_dm = payload.send_dm
        if payload.dm_text is not None:
            wf.dm_text = payload.dm_text
        if payload.dm_link is not None:
            wf.dm_link = payload.dm_link
        if payload.dm_image is not None:
            wf.dm_image = payload.dm_image
        if payload.status is not None:
            wf.status = payload.status
        if payload.nodes is not None:
            wf.nodes = payload.nodes
        if payload.connections is not None:
            wf.connections = payload.connections

        wf.updated_at = datetime.now(timezone.utc).isoformat()
        self._workflows[wf_id] = wf
        self._save_to_disk()
        return wf

    def delete_workflow(self, wf_id: str) -> bool:
        if wf_id in self._workflows:
            del self._workflows[wf_id]
            self._save_to_disk()
            return True
        return False

    def toggle_status(self, wf_id: str) -> Optional[Workflow]:
        wf = self._workflows.get(wf_id)
        if not wf:
            return None
        wf.status = "paused" if wf.status == "active" else "active"
        wf.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_to_disk()
        return wf

    def simulate_execution(self, wf_id: str, sample_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Simulates step-by-step execution across nodes in the workflow for testing."""
        wf = self._workflows.get(wf_id)
        if not wf:
            return {"status": "error", "message": f"Workflow {wf_id} not found"}

        wf.executions_count += 1
        wf.last_executed_at = datetime.now(timezone.utc).isoformat()
        self._save_to_disk()

        steps = []
        for i, node in enumerate(wf.nodes):
            steps.append({
                "step": i + 1,
                "node_id": node.id,
                "node_label": node.label,
                "category": node.category,
                "type": node.type,
                "status": "success",
                "output": f"Executed successfully at {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
                "execution_ms": 15 + (i * 12)
            })

        return {
            "status": "success",
            "workflow_id": wf.id,
            "workflow_name": wf.name,
            "executed_at": wf.last_executed_at,
            "steps_count": len(steps),
            "trace": steps,
            "total_latency_ms": sum(s["execution_ms"] for s in steps)
        }

    async def process_comment_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes an incoming comment webhook from Instagram or Facebook."""
        platform = event.get("platform")
        text = (event.get("text") or "").lower()
        comment_id = event.get("comment_id")
        media_id = event.get("media_id") or event.get("post_id")
        token = settings.META_PAGE_ACCESS_TOKEN
        if not token:
            logger.warning("Cannot process automation: META_PAGE_ACCESS_TOKEN not configured.")
            return None

        platform_str = platform.value if hasattr(platform, "value") else str(platform).lower()

        for wf in self._workflows.values():
            if wf.status != "active":
                continue
            if wf.platform != "omnichannel" and wf.platform != platform_str:
                continue
            if wf.target_type == "specific" and wf.target_post_id and str(wf.target_post_id) != str(media_id):
                continue

            keywords = [k.lower().strip() for k in (wf.keywords or []) if k.strip()]
            matches = True
            if keywords:
                matches = any(k in text for k in keywords)
            if not matches:
                continue

            logger.info(f"Live Automation Triggered: Workflow '{wf.name}' for comment '{comment_id}'")
            wf.executions_count += 1
            wf.last_executed_at = datetime.now(timezone.utc).isoformat()
            self._save_to_disk()

            # 1. Like comment
            if wf.like_comment and comment_id:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        if "instagram" in platform_str and settings.META_INSTAGRAM_ACCOUNT_ID:
                            await client.post(
                                f"{settings.META_GRAPH_API_BASE_URL}/{settings.META_INSTAGRAM_ACCOUNT_ID}/likes",
                                data={"comment_id": comment_id, "access_token": token}
                            )
                        else:
                            await client.post(
                                f"{settings.META_GRAPH_API_BASE_URL}/{comment_id}/likes",
                                data={"access_token": token}
                            )
                except Exception as e:
                    logger.warning(f"Failed to like comment {comment_id}: {e}")

            # 2. Public reply to comment
            if wf.reply_comment and wf.reply_comment_text and comment_id:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(
                            f"{settings.META_GRAPH_API_BASE_URL}/{comment_id}/replies",
                            data={"message": wf.reply_comment_text, "access_token": token}
                        )
                except Exception as e:
                    logger.warning(f"Failed to reply to comment {comment_id}: {e}")

            # 3. Private reply / DM
            if wf.send_dm and wf.dm_text and comment_id:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        target_id = settings.META_INSTAGRAM_ACCOUNT_ID if "instagram" in platform_str else settings.META_PAGE_ID
                        if target_id:
                            msg_payload = {"text": wf.dm_text}
                            if wf.dm_link:
                                msg_payload["text"] += f"\n{wf.dm_link}"
                            await client.post(
                                f"{settings.META_GRAPH_API_BASE_URL}/{target_id}/messages?access_token={token}",
                                json={"recipient": {"comment_id": comment_id}, "message": msg_payload}
                            )
                except Exception as e:
                    logger.warning(f"Failed to send private reply for comment {comment_id}: {e}")

            return {"status": "executed", "workflow_id": wf.id}
        return None


automations_service = AutomationsService()

