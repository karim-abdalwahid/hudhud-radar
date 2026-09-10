"""
Phase 9.7 — ConnectionService: per-user platform connections.

Layers (owner-approved golden rule):
  Connection layer  → what the user technically linked (tokens, encrypted at rest)
  Entitlement layer → what the user PAID for (user_entitlements — migration 009)
  Feature gate      → assert_entitled() is fail-closed 403, checked server-side
                      on EVERY sensitive action; token capability NEVER grants.

The golden upsell: a facebook connection may discover a linked Instagram account
(stored in metadata.linked_ig) — discovery is free metadata, service stays locked
until the instagram entitlement exists. Discovery = sales opportunity, not a leak.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from src.core.crypto import decrypt_token, encrypt_token
from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.modules.billing.services import entitlement_service

DISCOVERY_UPSELL_META = {
    "facebook": "linked_ig_id",     # IG account discovered via the connected page
    "instagram": "linked_page_id",  # reverse: page discovered via IG login (rare)
}


class ConnectionService:
    """Storage + retrieval + entitlement gate for per-user platform connections."""

    # ---- storage -----------------------------------------------------------
    def store(self, user_id: str, platform: str, access_token: str,
              account_id: Optional[str] = None, account_name: Optional[str] = None,
              scopes: Optional[List[str]] = None, token_expires_at: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Upserts the user's connection for (platform, account_id). Token is
        encrypted at rest — plaintext never touches the database or logs."""
        if platform not in ("facebook", "instagram", "threads"):
            raise ValueError(f"unsupported platform: {platform}")
        row = {
            "user_id": user_id,
            "platform": platform,
            "account_id": account_id or "",
            "account_name": account_name or "",
            "access_token_encrypted": encrypt_token(access_token),
            "token_expires_at": token_expires_at,
            "scopes": scopes or [],
            "metadata": metadata or {},
            "status": "active",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            existing = supabase_db.select("platform_connections", {
                "user_id": user_id, "platform": platform,
                "account_id": row["account_id"]}) or []
            if existing:
                saved = supabase_db.update("platform_connections", existing[0]["id"], row)
            else:
                saved = supabase_db.insert("platform_connections", row)
            logger.info(f"connection stored: user={user_id} platform={platform} "
                        f"account={account_name or account_id}")
            return saved
        except Exception as e:
            logger.error(f"connection store failed: {e}")
            return None

    def list_connections(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            rows = supabase_db.select("platform_connections", {"user_id": user_id}) or []
            return [r for r in rows if r.get("status") == "active"]
        except Exception as e:
            logger.warning(f"connection list failed → empty (fail-closed): {e}")
            return []

    def get_active_token(self, user_id: str, platform: str,
                         check_entitlement: bool = True) -> Optional[str]:
        """Resolves the user's decrypted token for a platform. THE gate:
        without the platform entitlement this returns None even if a
        connection exists (fail-closed — callers must treat None as denied)."""
        if check_entitlement and not self.assert_entitled(user_id, platform, raise_http=False):
            return None
        try:
            rows = supabase_db.select("platform_connections", {
                "user_id": user_id, "platform": platform, "status": "active"}) or []
            if not rows:
                return None
            row = rows[0]
            exp = row.get("token_expires_at")
            if exp and exp <= datetime.now(timezone.utc).isoformat():
                return None
            return decrypt_token(row.get("access_token_encrypted") or "")
        except Exception as e:
            logger.warning(f"token resolve failed → None (fail-closed): {e}")
            return None

    def revoke(self, user_id: str, platform: str) -> bool:
        try:
            rows = supabase_db.select("platform_connections", {
                "user_id": user_id, "platform": platform, "status": "active"}) or []
            for r in rows:
                supabase_db.update("platform_connections", r["id"], {"status": "revoked"})
            logger.info(f"connection revoked: user={user_id} platform={platform}")
            return True
        except Exception as e:
            logger.error(f"connection revoke failed: {e}")
            return False

    def revoke_by_platform_user(self, platform: str, platform_user_id: str) -> int:
        """Deauthorize/uninstall callbacks: revoke connections matching the
        app-scoped platform user id (the identity Meta reports)."""
        n = 0
        try:
            rows = supabase_db.select("platform_connections", {
                "platform": platform, "status": "active"}) or []
            for r in rows:
                meta = r.get("metadata") or {}
                if str(r.get("account_id")) == str(platform_user_id) or \
                        str(meta.get("platform_user_id", "")) == str(platform_user_id):
                    supabase_db.update("platform_connections", r["id"], {"status": "revoked"})
                    n += 1
        except Exception as e:
            logger.error(f"revoke_by_platform_user failed: {e}")
        return n

    # ---- entitlement gate (fail-closed) -------------------------------------
    def assert_entitled(self, user_id: str, platform: str,
                        raise_http: bool = True) -> bool:
        """THE feature gate: platform service requires the paid entitlement.
        Connection capability is irrelevant here by design."""
        ok = entitlement_service.has_platform(user_id, platform)
        if ok:
            return True
        if raise_http:
            raise HTTPException(
                status_code=403,
                detail=f"خدمة {platform} غير مفعّلة لاشتراكك — فعّلها من صفحة الفوترة"
                       f" / Service '{platform}' is not part of your subscription",
            )
        return False

    # ---- wizard overview (connections + entitlements + upsell) --------------
    def overview(self, user_id: str) -> Dict[str, Any]:
        ents = entitlement_service.user_entitlements(user_id)
        paid = entitlement_service.connected_platforms(user_id)
        conns = self.list_connections(user_id)
        sub = entitlement_service.subscription_status(user_id)

        connected_platforms = {c.get("platform") for c in conns}
        upsell = []
        for c in conns:
            meta = c.get("metadata") or {}
            # golden upsell: page-linked IG discovered on a facebook connection
            if c.get("platform") == "facebook" and meta.get("linked_ig_username") \
                    and "platform:instagram" not in ents:
                upsell.append({
                    "platform": "instagram",
                    "account": f"@{meta.get('linked_ig_username')}",
                    "reason": "linked_page",
                    "message": f"صفحتك عليها @{meta.get('linked_ig_username')} — "
                               f"فعّل خدمة الإنستجرام واحصل على خصم المنصات المتعددة",
                    "checkout_url": "/billing/checkout-page?add=instagram",
                })
        return {
            "user_id": user_id,
            "entitlements": ents,
            "paid_platforms": paid,
            "can_connect": sub.get("can_connect", False),
            "subscription": sub.get("status"),
            "connections": [
                {"id": c.get("id"), "platform": c.get("platform"),
                 "account_id": c.get("account_id"), "account_name": c.get("account_name"),
                 "status": c.get("status"), "scopes": c.get("scopes") or [],
                 "metadata": c.get("metadata") or {},
                 "connected_at": c.get("connected_at")} for c in conns
            ],
            "connected_platforms": sorted(connected_platforms),
            "upsell": upsell,
        }


connection_service = ConnectionService()
