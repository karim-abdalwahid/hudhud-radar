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

    @staticmethod
    def _matches_recipient_account(row: Dict[str, Any], platform: str,
                                   account_id: str) -> bool:
        """Whether an active connection owns a Meta webhook recipient.

        Instagram messaging/comment webhooks can identify the IG business
        account while the customer connected through Facebook Login.  That
        connection stores the linked IG id in metadata, so it is also a valid
        owner/token source for the Instagram recipient.
        """
        if row.get("platform") == platform and str(row.get("account_id") or "") == account_id:
            return True
        if platform == "instagram" and row.get("platform") == "facebook":
            metadata = row.get("metadata") or {}
            return str(metadata.get("linked_ig_id") or "") == account_id
        return False

    def _active_recipient_connections(self, platform: str, account_id: str,
                                      user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find exact active connections for a recipient business account.

        The filtering deliberately happens in one place so webhook ownership,
        outbound messaging, comments, and publishing cannot silently choose a
        different customer's token.
        """
        if not account_id:
            return []
        try:
            rows = supabase_db.select("platform_connections", {"status": "active"}) or []
            return [
                row for row in rows
                if (not user_id or str(row.get("user_id")) == str(user_id))
                and self._matches_recipient_account(row, platform, str(account_id))
            ]
        except Exception as e:
            logger.warning("recipient connection lookup failed → empty: %s", e)
            return []

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

    def owner_for_account(self, platform: str, account_id: Optional[str]) -> Optional[str]:
        """Return the sole active SaaS owner of an inbound recipient account.

        Webhook sender IDs belong to the end customer; the recipient business
        account identifies the tenant. Missing or ambiguous ownership returns
        None so the caller can fail closed rather than route a conversation to
        another tenant.
        """
        if platform not in ("facebook", "instagram", "threads") or not account_id:
            return None
        try:
            rows = self._active_recipient_connections(platform, str(account_id))
            owners = {str(row.get("user_id")) for row in rows if row.get("user_id")}
            if len(owners) == 1:
                return owners.pop()
            if len(owners) > 1:
                logger.error("Ambiguous active connection owner for %s account %s", platform, account_id)
        except Exception as e:
            logger.warning("connection owner lookup failed → None (fail-closed): %s", e)
        return None

    def get_active_token_for_account(self, user_id: str, platform: str,
                                     account_id: Optional[str]) -> Optional[str]:
        """Resolve the entitled user's token for exactly this recipient account."""
        if not account_id or not self.assert_entitled(user_id, platform, raise_http=False):
            return None
        try:
            rows = self._active_recipient_connections(platform, str(account_id), user_id=user_id)
            if len(rows) != 1:
                return None
            row = rows[0]
            exp = row.get("token_expires_at")
            if exp and exp <= datetime.now(timezone.utc).isoformat():
                return None
            return decrypt_token(row.get("access_token_encrypted") or "")
        except Exception as e:
            logger.warning("account token lookup failed → None (fail-closed): %s", e)
            return None

    def get_publish_credentials(self, user_id: str, platform: str) -> Optional[Dict[str, str]]:
        """Return one entitled user's exact publishing credentials.

        The caller receives only the decrypted token and destination account
        required for one outbound Graph request.  A missing/ambiguous
        connection returns ``None``; there is intentionally no legacy global
        token fallback in the SaaS path.
        """
        if platform not in ("facebook", "instagram"):
            return None
        if not self.assert_entitled(user_id, platform, raise_http=False):
            return None
        try:
            rows = supabase_db.select("platform_connections", {
                "user_id": user_id, "status": "active",
            }) or []
            candidates: List[tuple[Dict[str, Any], str]] = []
            for row in rows:
                if platform == "facebook" and row.get("platform") == "facebook":
                    candidates.append((row, str(row.get("account_id") or "")))
                elif platform == "instagram":
                    if row.get("platform") == "instagram":
                        candidates.append((row, str(row.get("account_id") or "")))
                    elif row.get("platform") == "facebook":
                        linked_ig_id = str((row.get("metadata") or {}).get("linked_ig_id") or "")
                        if linked_ig_id:
                            candidates.append((row, linked_ig_id))
            if len(candidates) != 1:
                return None
            row, account_id = candidates[0]
            if not account_id:
                return None
            expires_at = row.get("token_expires_at")
            if expires_at and expires_at <= datetime.now(timezone.utc).isoformat():
                return None
            token = decrypt_token(row.get("access_token_encrypted") or "")
            return {"access_token": token, "account_id": account_id}
        except Exception as e:
            logger.warning("publish credential lookup failed → None (fail-closed): %s", e)
            return None

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
            # Ambiguous connections must never select an arbitrary tenant
            # token/account.  The caller must use the exact-account helper.
            if len(rows) != 1:
                return None
            row = rows[0]
            exp = row.get("token_expires_at")
            if exp and exp <= datetime.now(timezone.utc).isoformat():
                return None
            return decrypt_token(row.get("access_token_encrypted") or "")
        except Exception as e:
            logger.warning("token resolve failed → None (fail-closed): %s", e)
            return None

    def get_connection_metadata(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Return metadata from one exact active tenant connection.

        This deliberately never falls back to deployment settings. It is used
        for account IDs (such as a customer's Meta ad account), not tokens.
        """
        try:
            rows = supabase_db.select("platform_connections", {
                "user_id": user_id, "platform": platform, "status": "active"}) or []
            if len(rows) != 1:
                return {}
            return dict(rows[0].get("metadata") or {})
        except Exception as e:
            logger.warning("connection metadata lookup failed → empty: %s", e)
            return {}

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
