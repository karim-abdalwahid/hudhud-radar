"""
Entitlement & Pricing services (Phase 9.1) — the money brain.

Model (owner decisions):
- NO base plan. Pricing = sum of chosen platform addons − multi-platform
  discount (admin-editable).
- user_entitlements = THE single source of truth for what a user may use.
- Backend gates are default-deny: no entitlement → no access, regardless of UI.
- Discounts: 2 platforms −10%, 3+ −20% (read from app_settings, admin-editable).
- Trial: 3 days, ALL platforms, requires card (enforced at checkout via Polar).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.logger import logger
from src.core.supabase_client import supabase_db

MULTI_PLATFORM_DISCOUNTS = {1: 0, 2: 10, 3: 20}  # count → percent off (fallback defaults)
TRIAL_DAYS = 3
TRIAL_ENTITLEMENTS = ["platform:facebook", "platform:instagram", "platform:threads"]


class EntitlementService:
    """Reads/grants/revokes entitlements. Fail-safe: a lookup error denies
    access (fail-closed) — never grants."""

    def user_entitlements(self, user_id: str) -> List[str]:
        try:
            rows = supabase_db.select("user_entitlements", {"user_id": user_id}) or []
            now = datetime.now(timezone.utc).isoformat()
            out = []
            for r in rows:
                exp = r.get("expires_at")
                if exp and exp <= now:
                    continue
                out.append(r.get("entitlement"))
            return out
        except Exception as e:
            logger.warning(f"entitlement lookup failed → deny (fail-closed): {e}")
            return []

    def has(self, user_id: str, entitlement: str) -> bool:
        return entitlement in self.user_entitlements(user_id)

    def has_platform(self, user_id: str, platform: str) -> bool:
        return self.has(user_id, f"platform:{platform}")

    def connected_platforms(self, user_id: str) -> List[str]:
        """Platform:* entitlements owned by the user (their paid platforms)."""
        return sorted(e.split(":", 1)[1] for e in self.user_entitlements(user_id)
                      if e.startswith("platform:"))

    def grant(self, user_id: str, entitlement: str,
              source: str = "subscription", expires_at: Optional[str] = None) -> bool:
        try:
            existing = supabase_db.select("user_entitlements", {
                "user_id": user_id, "entitlement": entitlement}) or []
            if existing:
                supabase_db.update("user_entitlements", existing[0]["id"], {
                    "source": source, "expires_at": expires_at})
            else:
                supabase_db.insert("user_entitlements", {
                    "user_id": user_id, "entitlement": entitlement,
                    "source": source, "expires_at": expires_at})
            return True
        except Exception as e:
            logger.error(f"entitlement grant failed: {e}")
            return False

    def revoke(self, user_id: str, entitlement: str) -> bool:
        try:
            rows = supabase_db.select("user_entitlements", {
                "user_id": user_id, "entitlement": entitlement}) or []
            for r in rows:
                supabase_db.delete("user_entitlements", r["id"])
            return True
        except Exception as e:
            logger.error(f"entitlement revoke failed: {e}")
            return False

    def sync_from_platforms(self, user_id: str, platforms: List[str],
                            source: str = "subscription",
                            expires_at: Optional[str] = None) -> int:
        """Sets platform:* entitlements EXACTLY to the given list —
        grants/refreshes wanted rows and revokes rows not included (payment
        truth).  Refreshing matters when a trial converts: the existing
        entitlement must lose its trial expiry and become a paid entitlement.
        """
        wanted = {f"platform:{p}" for p in platforms}
        try:
            rows = supabase_db.select("user_entitlements", {"user_id": user_id}) or []
        except Exception as e:
            logger.error(f"entitlement sync failed for {user_id}: {e}")
            return 0
        current = {r.get("entitlement") for r in rows if str(r.get("entitlement") or "").startswith("platform:")}
        changed = 0
        for entitlement in wanted:
            row = next((r for r in rows if r.get("entitlement") == entitlement), None)
            if not row or row.get("source") != source or row.get("expires_at") != expires_at:
                changed += int(self.grant(user_id, entitlement, source, expires_at))
        revoked = sum(1 for e in current - wanted if self.revoke(user_id, e))
        return changed + revoked

    # ---- Subscription state ------------------------------------------------
    def get_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        rows = supabase_db.select("user_subscriptions", {"user_id": user_id}) or []
        return rows[0] if rows else None

    def upsert_subscription(self, user_id: str, **fields) -> Optional[Dict[str, Any]]:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        sub = self.get_subscription(user_id)
        if sub:
            return supabase_db.update("user_subscriptions", sub["id"], fields)
        return supabase_db.insert("user_subscriptions", {"user_id": user_id, **fields})

    def has_used_trial(self, user_id: str) -> bool:
        """Whether this user has ever received a Hudhud trial.

        ``trial_ends_at`` is deliberately retained after expiry/cancellation, so
        it is an auditable, durable one-trial marker rather than a status that
        can be reset by a later subscription update.
        """
        try:
            sub = self.get_subscription(user_id) or {}
            return bool(sub.get("trial_ends_at"))
        except Exception as e:
            # A failed ownership/payment lookup must not issue a free period.
            logger.error(f"trial eligibility lookup failed for {user_id}: {e}")
            return True

    def can_start_trial(self, user_id: str) -> bool:
        """Returns true only for a user without a current or recorded trial."""
        try:
            sub = self.get_subscription(user_id) or {}
            return (not self.has_used_trial(user_id)
                    and sub.get("status") not in ("trialing", "active"))
        except Exception as e:
            logger.error(f"trial eligibility lookup failed for {user_id}: {e}")
            return False

    def start_trial(self, user_id: str, payment_provider: Optional[str] = None,
                    provider_subscription_id: Optional[str] = None) -> bool:
        """Starts exactly one 3-day all-platforms trial after a verified webhook.

        Checkout creation alone does not grant access.  The gateway event must
        pass signature verification first, then this method persists the trial
        marker and its scoped entitlements atomically at the service boundary.
        """
        if not self.can_start_trial(user_id):
            logger.warning(f"Trial denied for {user_id}: already active or previously used")
            return False
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        trial_end = (now + timedelta(days=TRIAL_DAYS)).isoformat()
        fields: Dict[str, Any] = {"status": "trialing", "trial_ends_at": trial_end}
        if payment_provider:
            fields["payment_provider"] = payment_provider
        if provider_subscription_id:
            fields["provider_subscription_id"] = provider_subscription_id
        self.upsert_subscription(user_id, **fields)
        for e in TRIAL_ENTITLEMENTS:
            self.grant(user_id, e, source="trial", expires_at=trial_end)
        # A trial is worthless without anything to reply with. Top up (never
        # lower) so a user who already burned their signup balance still gets
        # a working trial. Local import: usage.py must not import this module
        # at load time (services.py is the more foundational of the two).
        try:
            from src.modules.billing.usage import usage_service
            usage_service.grant_trial_credits(user_id)
        except Exception as e:
            logger.error(f"trial credit top-up failed for {user_id}: {e}")
        logger.info(f"Trial started for {user_id} (ends {trial_end})")
        return True

    def subscription_status(self, user_id: str) -> Dict[str, Any]:
        sub = self.get_subscription(user_id) or {}
        status = sub.get("status", "none")
        trial_end = sub.get("trial_ends_at")
        # auto-expire trial
        if status == "trialing" and trial_end and trial_end <= datetime.now(timezone.utc).isoformat():
            self.upsert_subscription(user_id, status="canceled")
            for e in TRIAL_ENTITLEMENTS:
                self.revoke(user_id, e)
            status = "canceled"
        return {
            "status": status,
            "platforms": self.connected_platforms(user_id),
            "trial_ends_at": trial_end,
            "can_connect": status in ("trialing", "active"),
        }


def _tz_utc():
    from datetime import timezone
    return timezone


class PricingService:
    """Composable pricing: sum chosen platforms − multi-platform discount.
    Catalog & discounts are admin-editable (platform_addons_catalog / app_settings)."""

    def catalog(self) -> List[Dict[str, Any]]:
        rows = supabase_db.select("platform_addons_catalog") or []
        rows.sort(key=lambda r: r.get("sort_order") or 100)
        return [{"platform": r.get("platform"), "display_name": r.get("display_name"),
                 "price_usd": float(r.get("price_usd") or 0),
                 "is_available": r.get("is_available", True)} for r in rows]

    def _discount_percent(self, count: int) -> int:
        try:
            cfg = supabase_db.get_setting("billing_discounts") or {}
            table = cfg.get("multi_platform", {}) if isinstance(cfg, dict) else {}
            return int(table.get(str(count), table.get(str(min(count, 3))), 0) or
                       MULTI_PLATFORM_DISCOUNTS.get(min(count, 3), 0))
        except Exception:
            return MULTI_PLATFORM_DISCOUNTS.get(min(count, 3), 0)

    def quote(self, platforms: List[str], coupon: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cat = {c["platform"]: c for c in self.catalog()}
        lines, total = [], 0.0
        for p in platforms:
            c = cat.get(p)
            if not c or not c["is_available"]:
                continue
            lines.append({"platform": p, "display_name": c["display_name"],
                          "price_usd": c["price_usd"]})
            total += c["price_usd"]
        count = len(lines)
        discount_pct = self._discount_percent(count)
        discount_usd = round(total * discount_pct / 100, 2)
        subtotal = round(total - discount_usd, 2)
        coupon_discount = 0.0
        if coupon:
            if coupon.get("kind") == "percent":
                coupon_discount = round(subtotal * float(coupon.get("value", 0)) / 100, 2)
            elif coupon.get("kind") == "fixed":
                coupon_discount = round(float(coupon.get("value", 0)), 2)
        coupon_discount = min(coupon_discount, subtotal)
        final = round(subtotal - coupon_discount, 2)
        return {
            "platforms": [l["platform"] for l in lines],
            "lines": lines,
            "platforms_count": count,
            "subtotal_usd": round(total, 2),
            "multi_platform_discount_percent": discount_pct,
            "multi_platform_discount_usd": discount_usd,
            "coupon_discount_usd": coupon_discount,
            "total_usd": final,
        }


entitlement_service = EntitlementService()
pricing_service = PricingService()
