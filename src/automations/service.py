from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

import httpx
from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db
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
            "status": "paused",
            "target_type": "all_posts",
            "target_post_id": None,
            "target_post_title": "All Reels & Posts",
            "keywords": ["سوشيال", "كورس", "تفاصيل", "سعر", "مهتم"],
            "like_comment": True,
            "reply_comment": True,
            "reply_comment_text": "تم إرسال كافة التفاصيل في رسالة خاصة لحضرتك على الدايركت فوراً 🚀",
            "send_dm": True,
            "dm_text": "أهلاً بحضرتك! إليك تفاصيل الكورس والعرض الخاص لليوم:",
            "dm_link": "",
            "dm_image": "",
            "executions_count": 0,
            "last_executed_at": None,
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
                        "include_offer": False,
                        "discount_code": ""
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
                        "calendar_link": ""
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
            "status": "paused",
            "target_type": "all_posts",
            "target_post_id": None,
            "target_post_title": "All Facebook Posts & Reels",
            "keywords": ["تفاصيل", "سعر", "مهتم", "خدمات", "عرض"],
            "like_comment": True,
            "reply_comment": True,
            "reply_comment_text": "أهلاً بك! تم إرسال كافة التفاصيل في رسالة خاصة لحضرتك فوراً 🚀",
            "send_dm": True,
            "dm_text": "مرحباً بحضرتك! استفسارك بخصوص الخدمة محل اهتمامنا، تفضل بالاطلاع على التفاصيل:",
            "dm_link": "",
            "dm_image": "",
            "executions_count": 0,
            "last_executed_at": None,
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
            "description": "Dispatches qualified high-intent social conversations to external n8n HTTP Request API nodes or Make.com webhooks. Configure a real webhook URL before activating.",
            "platform": "both",
            "trigger_type": "webhook",
            "status": "paused",
            "executions_count": 0,
            "last_executed_at": None,
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
# ----------------------------------------------------------------------
# Wave 9.8: automations_workflows table (source of truth) — pure helpers
# (db injected for testability; class methods delegate to these).
# ----------------------------------------------------------------------
def db_load_workflows(db, user_id: Optional[str] = None) -> Optional[List[Workflow]]:
    """Rebuild one tenant's workflows from the authoritative table.

    A missing owner is never interpreted as "all workspaces".  That former
    global query was the route by which legacy workflows could cross tenant
    boundaries.
    """
    if not user_id or db is None or not getattr(db, "is_connected", False):
        return None
    try:
        rows = db.select("automations_workflows", {"user_id": user_id}) or []
        if not rows:
            return None
        wfs: List[Workflow] = []
        for r in rows:
            cfg = r.get("config") or {}
            try:
                wfs.append(Workflow(**cfg))
            except Exception as e:
                logger.warning(f"Skipping malformed automation row {r.get('id')}: {e}")
        return wfs or None
    except Exception as e:
        logger.warning(f"Automations DB load failed (legacy fallback): {e}")
        return None


def _workflow_row(wf: "Workflow", owner_user_id: str) -> Dict[str, Any]:
    """Serialize one workflow with its immutable tenant owner."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": wf.id,
        "user_id": owner_user_id,
        "name": wf.name,
        "platform": wf.platform,
        "status": wf.status,
        "keywords": wf.keywords or [],
        "target_type": wf.target_type,
        "target_post_id": wf.target_post_id,
        "like_comment": wf.like_comment,
        "reply_comment": wf.reply_comment,
        "reply_comment_text": wf.reply_comment_text,
        "send_dm": wf.send_dm,
        "dm_text": wf.dm_text,
        "last_executed_at": getattr(wf, "last_executed_at", None),
        "execution_count": getattr(wf, "execution_count", 0) or 0,
        "config": wf.model_dump(mode="json"),
        "updated_at": now,
    }


def db_get_workflow(db, wf_id: str, user_id: str) -> Optional[Workflow]:
    if not user_id or db is None or not getattr(db, "is_connected", False):
        return None
    try:
        rows = db.select("automations_workflows", {"id": wf_id, "user_id": user_id}) or []
        config = (rows[0].get("config") or {}) if rows else {}
        return Workflow(**config) if config else None
    except Exception as e:
        logger.warning("Automation lookup failed for tenant %s: %s", user_id, e)
        return None


def db_upsert_workflow(db, wf: "Workflow", user_id: str) -> bool:
    """Persist exactly one workflow without pruning another tenant's rows."""
    if not user_id or db is None or not getattr(db, "is_connected", False):
        return False
    try:
        payload = _workflow_row(wf, user_id)
        existing = db.select("automations_workflows", {"id": wf.id, "user_id": user_id}) or []
        if existing:
            db.update("automations_workflows", wf.id, payload)
        else:
            db.insert("automations_workflows", payload)
        return True
    except Exception as e:
        logger.warning("Automation save failed for tenant %s: %s", user_id, e)
        return False


def db_delete_workflow(db, wf_id: str, user_id: str) -> bool:
    if not db_get_workflow(db, wf_id, user_id):
        return False
    try:
        return bool(db.delete("automations_workflows", wf_id))
    except Exception as e:
        logger.warning("Automation delete failed for tenant %s: %s", user_id, e)
        return False


def db_save_workflows(db, workflows: Dict[str, "Workflow"],
                      owner_user_id: Optional[str] = None) -> bool:
    """Upserts one tenant's workflows; ownerless writes are forbidden."""
    if not owner_user_id or db is None or not getattr(db, "is_connected", False):
        return False
    now = datetime.now(timezone.utc).isoformat()
    ok = False
    # prune rows that no longer exist in the authoritative in-memory set
    try:
        existing = db.select("automations_workflows", {"user_id": owner_user_id}) or []
        live_ids = set(workflows.keys())
        for row in existing:
            if row.get("id") and row["id"] not in live_ids:
                try:
                    db.delete("automations_workflows", row["id"])
                except Exception as e:
                    logger.warning(f"Automations prune failed for {row['id']}: {e}")
    except Exception as e:
        logger.warning(f"Automations prune check failed: {e}")
    for wf in workflows.values():
        payload = _workflow_row(wf, owner_user_id)
        try:
            existing = db.select(
                "automations_workflows", {"id": wf.id, "user_id": owner_user_id}) or []
            if existing:
                db.update("automations_workflows", wf.id, payload)
            else:
                db.insert("automations_workflows", payload)
            ok = True
        except Exception as e:
            logger.warning(f"Automations DB upsert failed for {wf.id}: {e}")
    return ok


class AutomationsService:
    """Manages storage, lifecycle, and execution of visual automation workflows.

    The tenant-owned ``automations_workflows`` table is the only production
    source of truth.  The historic shared app_settings/disk stores are never
    imported because their rows have no workspace owner.
    """

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._load()

    def _load(self):
        # Deliberately do not pre-load all database rows: callers must always
        # ask through list_workflows(user_id=...).  This makes an accidental
        # ownerless/global query impossible at startup.
        self._workflows = {}

    def _sanitize_legacy_fabrications(self):
        """One-time cleanup of previously-shipped fabricated defaults that
        could DM real customers a fake booking link / discount code.
        Nodes may be pydantic NodeData or raw dicts (legacy stores)."""
        dirty = False
        for wf in self._workflows.values():
            for node in (wf.nodes or []):
                if isinstance(node, dict):
                    cfg = node.get("config") or {}
                else:
                    cfg = getattr(node, "config", None) or {}
                if not isinstance(cfg, dict):
                    continue
                changed = False
                if cfg.get("discount_code") == "HUDHUD20":
                    cfg["discount_code"] = ""
                    cfg["include_offer"] = False
                    changed = True
                if cfg.get("calendar_link") == "https://calendar.app.google/hudhud-meeting":
                    cfg["calendar_link"] = ""
                    cfg["cta_button"] = ""
                    changed = True
                if changed:
                    if isinstance(node, dict):
                        node["config"] = cfg
                    else:
                        node.config = cfg
                    dirty = True
        if dirty:
            logger.warning("Sanitized legacy fabricated automation defaults (HUDHUD20 / fake calendar link).")
            self._save()

    def _save(self):
        """Compatibility no-op for ownerless unit-test workflows.

        Production calls always provide ``user_id`` and persist through the
        scoped helpers above; no shared cache is written.
        """
        return None

    def list_workflows(self, user_id: Optional[str] = None) -> List[Workflow]:
        if user_id:
            return db_load_workflows(supabase_db, user_id=user_id) or []
        return list(self._workflows.values())

    def get_workflow(self, wf_id: str, user_id: Optional[str] = None) -> Optional[Workflow]:
        if user_id:
            return db_get_workflow(supabase_db, wf_id, user_id)
        return self._workflows.get(wf_id)

    def create_workflow(self, payload: WorkflowCreate, user_id: Optional[str] = None) -> Workflow:
        if user_id and not getattr(supabase_db, "is_connected", False):
            raise ValueError("قاعدة البيانات غير متصلة؛ لا يمكن حفظ Workflow العميل بأمان")
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
                    icon="🔍",
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
        if user_id:
            if not db_upsert_workflow(supabase_db, wf, user_id):
                raise ValueError("تعذر حفظ Workflow العميل")
        else:
            self._workflows[wf_id] = wf
            self._save()
        return wf

    def update_workflow(self, wf_id: str, payload: WorkflowUpdate,
                        user_id: Optional[str] = None) -> Optional[Workflow]:
        wf = self.get_workflow(wf_id, user_id=user_id)
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
        if user_id:
            if not db_upsert_workflow(supabase_db, wf, user_id):
                return None
        else:
            self._workflows[wf_id] = wf
            self._save()
        return wf

    def delete_workflow(self, wf_id: str, user_id: Optional[str] = None) -> bool:
        if user_id:
            return db_delete_workflow(supabase_db, wf_id, user_id)
        if wf_id in self._workflows:
            del self._workflows[wf_id]
            self._save()
            return True
        return False

    def toggle_status(self, wf_id: str, user_id: Optional[str] = None) -> Optional[Workflow]:
        wf = self.get_workflow(wf_id, user_id=user_id)
        if not wf:
            return None
        wf.status = "paused" if wf.status == "active" else "active"
        wf.updated_at = datetime.now(timezone.utc).isoformat()
        if user_id:
            if not db_upsert_workflow(supabase_db, wf, user_id):
                return None
        else:
            self._save()
        return wf

    def simulate_execution(self, wf_id: str, sample_payload: Optional[Dict[str, Any]] = None,
                           user_id: Optional[str] = None) -> Dict[str, Any]:
        """Simulates step-by-step execution across nodes in the workflow for testing."""
        wf = self.get_workflow(wf_id, user_id=user_id)
        if not wf:
            return {"status": "error", "message": f"Workflow {wf_id} not found"}

        wf.executions_count += 1
        wf.last_executed_at = datetime.now(timezone.utc).isoformat()
        if user_id:
            if not db_upsert_workflow(supabase_db, wf, user_id):
                return {"status": "error", "message": "Workflow could not be saved"}
        else:
            self._save()

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
        platform_str = platform.value if hasattr(platform, "value") else str(platform).lower()
        recipient_account_id = str(event.get("account_id") or "")
        from src.modules.connections.service import connection_service
        owner_user_id = connection_service.owner_for_account(platform_str, recipient_account_id)
        if not owner_user_id:
            logger.warning("Automation ignored: no unique owner for comment recipient %s", recipient_account_id)
            return None
        token = connection_service.get_active_token_for_account(
            owner_user_id, platform_str, recipient_account_id)
        if not token:
            logger.warning("Automation ignored: no entitled token for comment recipient %s", recipient_account_id)
            return None

        # Human Takeover / AI Pause guards: the human owns the conversation —
        # automations must stay silent. (Takeover = per-conversation; AI pause
        # = the owner's global switch, Wave 9.8.)
        try:
            sender_id = event.get("sender_id")
            if sender_id:
                id_field = "instagram_account_id" if platform_str == "instagram" else "facebook_account_id"
                matches_lead = supabase_db.select("leads", {
                    id_field: sender_id, "user_id": owner_user_id}) or []
                lead_row = matches_lead[0] if matches_lead else None
                from src.ai.pause import is_ai_paused
                if lead_row and (lead_row.get("human_takeover")
                                 or is_ai_paused(lead_row.get("user_id"))):
                    logger.info(
                        f"Automation skipped for commenter {sender_id}: "
                        f"{'Human Takeover' if lead_row.get('human_takeover') else 'AI paused'}.")
                    return None
        except Exception as e:
            logger.warning(f"Takeover/pause check skipped (non-blocking): {e}")

        # Policy guard: outbound API bursts must respect the shared rate limiter
        from src.meta_api.rate_limiter import rate_limiter
        from src.core.exceptions import RateLimitExceededError

        for wf in self.list_workflows(user_id=owner_user_id):
            if wf.status != "active":
                continue
            # FIX B1: 'both'/'omnichannel' both mean all-platform workflows
            if wf.platform not in ("both", "omnichannel", "all") and wf.platform != platform_str:
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

            step_results = {"like": None, "reply": None, "dm": None}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # 1. Like comment
                    if wf.like_comment and comment_id:
                        try:
                            rate_limiter.check_and_acquire(platform_str)
                            if "instagram" in platform_str and recipient_account_id:
                                resp = await client.post(
                                    f"{settings.META_GRAPH_API_BASE_URL}/{recipient_account_id}/likes",
                                    data={"comment_id": comment_id, "access_token": token}
                                )
                            else:
                                resp = await client.post(
                                    f"{settings.META_GRAPH_API_BASE_URL}/{comment_id}/likes",
                                    data={"access_token": token}
                                )
                            step_results["like"] = resp.status_code == 200
                            if resp.status_code != 200:
                                logger.warning(f"Like failed for comment {comment_id}: HTTP {resp.status_code} {resp.text[:150]}")
                        except RateLimitExceededError:
                            logger.warning(f"Automation like skipped (rate limit) for comment {comment_id}")
                        except Exception as e:
                            logger.warning(f"Failed to like comment {comment_id}: {e}")

                    # 2. Public reply to comment
                    if wf.reply_comment and wf.reply_comment_text and comment_id:
                        try:
                            rate_limiter.check_and_acquire(platform_str)
                            resp = await client.post(
                                f"{settings.META_GRAPH_API_BASE_URL}/{comment_id}/replies",
                                data={"message": wf.reply_comment_text, "access_token": token}
                            )
                            step_results["reply"] = resp.status_code == 200
                            if resp.status_code != 200:
                                logger.warning(f"Reply failed for comment {comment_id}: HTTP {resp.status_code} {resp.text[:150]}")
                        except RateLimitExceededError:
                            logger.warning(f"Automation reply skipped (rate limit) for comment {comment_id}")
                        except Exception as e:
                            logger.warning(f"Failed to reply to comment {comment_id}: {e}")

                    # 3. Private reply / DM (policy-safe: private replies are allowed
                    #    within 7 days of the comment even outside the 24h window)
                    if wf.send_dm and wf.dm_text and comment_id:
                        try:
                            rate_limiter.check_and_acquire(platform_str)
                            target_id = recipient_account_id
                            if target_id:
                                msg_payload = {"text": wf.dm_text}
                                if wf.dm_link:
                                    msg_payload["text"] += f"\n{wf.dm_link}"
                                resp = await client.post(
                                    f"{settings.META_GRAPH_API_BASE_URL}/{target_id}/messages?access_token={token}",
                                    json={"recipient": {"comment_id": comment_id}, "message": msg_payload}
                                )
                                step_results["dm"] = resp.status_code == 200
                                if resp.status_code != 200:
                                    logger.warning(f"DM failed for comment {comment_id}: HTTP {resp.status_code} {resp.text[:150]}")
                        except RateLimitExceededError:
                            logger.warning(f"Automation DM skipped (rate limit) for comment {comment_id}")
                        except Exception as e:
                            logger.warning(f"Failed to send private reply for comment {comment_id}: {e}")
            except Exception as e:
                logger.error(f"Automation execution error for comment {comment_id}: {e}")

            # ZERO-FABRICATION: executions_count increments only when at least
            # one step REALLY succeeded; failures are surfaced in the result.
            any_success = any(v is True for v in step_results.values())
            attempted = [k for k, v in step_results.items() if v is not None]
            if any_success:
                wf.executions_count += 1
                wf.last_executed_at = datetime.now(timezone.utc).isoformat()
                db_upsert_workflow(supabase_db, wf, owner_user_id)
            else:
                logger.error(f"Automation '{wf.name}' completed with NO successful steps for comment {comment_id}: {step_results}")

            return {
                "status": "executed" if any_success else "failed",
                "workflow_id": wf.id,
                "steps": step_results,
                "steps_attempted": attempted,
            }
        return None


automations_service = AutomationsService()

