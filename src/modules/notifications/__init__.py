"""
Notifications module — in-app notification system (WS-F).

User-facing: list mine / unread count / mark read / mark all read.
Admin-facing: broadcast to all users or a specific user (owner requirement).

Job hooks (publish, automations, syncs, AI replies) call
notification_service.create() at their completion points.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
from src.core.modules import module_registry
from src.modules.notifications.service import notification_service


class BroadcastPayload(BaseModel):
    title: str
    body: str = ""
    target_user_id: Optional[str] = None  # None = all active users


def register(app: FastAPI) -> None:
    @app.get("/api/notifications", tags=["Notifications"])
    async def my_notifications(request: Request, unread_only: bool = False, limit: int = 30, lang: Optional[str] = None):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session:
            raise HTTPException(status_code=401, detail="غير مصرح")
        target_lang = lang or request.cookies.get("hudhud_lang") or "en"
        rows = notification_service.list_for_user(
            session["sub"], limit=min(max(limit, 1), 100), unread_only=unread_only, lang=target_lang
        )
        return {"status": "success", "notifications": rows,
                "unread": notification_service.unread_count(session["sub"])}

    @app.get("/api/notifications/unread-count", tags=["Notifications"])
    async def unread_count(request: Request):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session:
            raise HTTPException(status_code=401, detail="غير مصرح")
        cnt = notification_service.unread_count(session["sub"])
        return {
            "status": "success",
            "unread": cnt,
            "count": cnt,
            "unread_count": cnt,
        }

    @app.post("/api/notifications/{notification_id}/read", tags=["Notifications"])
    async def mark_one_read(notification_id: str, request: Request):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session:
            raise HTTPException(status_code=401, detail="غير مصرح")
        ok = notification_service.mark_read(session["sub"], notification_id)
        return {"status": "success" if ok else "error"}

    @app.post("/api/notifications/read-all", tags=["Notifications"])
    async def mark_all_read(request: Request):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session:
            raise HTTPException(status_code=401, detail="غير مصرح")
        return {"status": "success", "marked": notification_service.mark_all_read(session["sub"])}

    @app.post("/api/admin/notifications/broadcast", tags=["Notifications"])
    async def broadcast_notification(payload: BroadcastPayload, request: Request):
        token = request.cookies.get(SESSION_COOKIE_NAME)
        session = verify_session_token(token) if token else None
        if not session or session.get("role") != "admin":
            raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
        sent = notification_service.broadcast(
            payload.title, payload.body,
            target_user_id=payload.target_user_id,
        )
        return {"status": "success", "delivered": sent}


module_registry.register_module(
    name="notifications",
    description="In-app notifications: user bell (list/read) + admin broadcast; job hooks create events",
    register_router=register,
)
