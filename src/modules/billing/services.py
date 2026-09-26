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
# Fallback USD prices for CREDIT_PACKS (usage.py), used when no admin
# override exists in the "credit_packs_pricing" setting. Volume-discounted
# per-credit (larger packs cost less per credit) — a starting point, not a
# committed price; tune via PUT /api/admin/site-settings.
DEFAULT_CREDIT_PACK_PRICES_USD = {"credits_500": 9.0, "credits_2000": 29.0, "credits_5000": 59.0}
TRIAL_DAYS = 3
TRIAL_ENTITLEMENTS = ["platform:facebook", "platform:instagram", "platform:threads"]

PLAN_CONFIG = {
    "free": {
        "platforms": [],
        "min_credits": 100,
        "name_ar": "باقة مجانية (Free)",
        "name_en": "Free Plan",
    },
    "starter": {
        "platforms": ["facebook", "instagram"],
        "min_credits": 1000,
        "name_ar": "باقة البداية (Starter)",
        "name_en": "Starter Plan",
    },
    "growth": {
        "platforms": ["facebook", "instagram", "threads"],
        "min_credits": 5000,
        "name_ar": "باقة النمو (Growth Pro)",
        "name_en": "Growth Pro Plan",
    },
    "scale": {
        "platforms": ["facebook", "instagram", "threads"],
        "min_credits": 25000,
        "name_ar": "باقة الشركات (Scale Agency)",
        "name_en": "Scale Agency Plan",
    },
}


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
        if sub and sub.get("id"):
            return supabase_db.update("user_subscriptions", sub["id"], fields)
        if sub:
            return supabase_db.update("user_subscriptions", user_id, fields)
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

    def apply_plan(self, user_id: str, plan: str, _from_heal: bool = False) -> Dict[str, Any]:
        """Applies a plan to a user: syncs users.plan, user_subscriptions,
        and platform entitlements. Used by admin manual changes & auto-healing."""
        cfg = PLAN_CONFIG.get(plan, PLAN_CONFIG["free"])
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            supabase_db.update("users", user_id, {
                "plan": plan,
                "plan_updated_at": now_iso,
            })
        except Exception as e:
            logger.warning(f"users table plan update failed: {e}")

        try:
            if plan == "free":
                self.upsert_subscription(user_id, status="canceled")
                self.sync_from_platforms(user_id, [], source="admin")
            else:
                self.upsert_subscription(
                    user_id,
                    status="active",
                    payment_provider="admin_manual",
                    provider_subscription_id=f"manual_{plan}_{user_id[:8]}",
                )
                self.sync_from_platforms(user_id, cfg["platforms"], source="admin")
                try:
                    from src.modules.billing.usage import usage_service
                    usage_service.ensure_minimum_credits(user_id, cfg["min_credits"])
                except Exception as e:
                    logger.warning(f"ensure_minimum_credits failed: {e}")
        except Exception as e:
            logger.warning(f"subscription/entitlement sync failed in apply_plan: {e}")

        if plan != "free" and not _from_heal:
            try:
                from src.modules.notifications.service import notification_service
                plan_name_en = cfg.get("name_en", plan.title())
                plan_name_ar = cfg.get("name_ar", plan)
                platforms_str = ", ".join(cfg.get("platforms", []))
                title_ar = f"✅ تم تفعيل {plan_name_ar}"
                body_ar = f"المنصات المشمولة في خطتك: {platforms_str}. رصيد الردود تم تحديثه."
                title_en = f"✅ Plan activated: {plan_name_en}"
                body_en = f"Included platforms: {platforms_str}. AI credits have been updated."
                notification_service.create(
                    user_id,
                    title_ar,
                    body_ar,
                    "success",
                    {
                        "job": "plan_assigned",
                        "plan": plan,
                        "title_ar": title_ar,
                        "body_ar": body_ar,
                        "title_en": title_en,
                        "body_en": body_en,
                    },
                )
            except Exception:
                pass

        return self.subscription_status(user_id, _auto_heal=False)

    def subscription_status(self, user_id: str, _auto_heal: bool = True) -> Dict[str, Any]:
        sub = self.get_subscription(user_id) or {}
        status = sub.get("status", "none")
        trial_end = sub.get("trial_ends_at")

        # auto-expire trial
        if status == "trialing" and trial_end and trial_end <= datetime.now(timezone.utc).isoformat():
            self.upsert_subscription(user_id, status="canceled")
            for e in TRIAL_ENTITLEMENTS:
                self.revoke(user_id, e)
            status = "canceled"

        # Check assigned plan in users table
        user_plan = "free"
        try:
            user_rows = supabase_db.select("users", {"id": user_id}) or []
            if user_rows:
                user_plan = user_rows[0].get("plan") or "free"
            else:
                from src.core.auth import user_store
                u = user_store.get_by_id(user_id)
                if u:
                    user_plan = u.get("plan") or "free"
        except Exception as e:
            logger.warning(f"user plan lookup failed for {user_id}: {e}")

        # Auto-heal: If an admin assigned a paid plan (starter, growth, scale)
        # but user_subscriptions is not active or platform entitlements are missing:
        if _auto_heal and user_plan in ("starter", "growth", "scale"):
            platforms = self.connected_platforms(user_id)
            if status not in ("active", "trialing") or not platforms:
                self.apply_plan(user_id, user_plan, _from_heal=True)
                sub = self.get_subscription(user_id) or {}
                status = sub.get("status", "active")

        effective_status = status
        if effective_status not in ("active", "trialing") and user_plan in ("starter", "growth", "scale"):
            effective_status = "active"

        effective_platforms = self.connected_platforms(user_id)
        if not effective_platforms and user_plan in ("starter", "growth", "scale"):
            effective_platforms = PLAN_CONFIG.get(user_plan, {}).get("platforms", [])

        effective_plan = user_plan if user_plan != "free" else (sub.get("plan_id") or effective_status)
        sub_payload = {
            "status": effective_status,
            "platforms": effective_platforms,
            "trial_ends_at": trial_end,
            "can_connect": effective_status in ("trialing", "active"),
            "plan": effective_plan,
            "plan_display": PLAN_CONFIG.get(effective_plan, {}).get("name_ar", "باقة مجانية"),
            "plan_display_en": PLAN_CONFIG.get(effective_plan, {}).get("name_en", "Free Plan"),
        }
        return {
            **sub_payload,
            "subscription": sub_payload,
        }

    def reconcile_active_subscriptions(self) -> Dict[str, Any]:
        """Daily safety net: checks all active Polar subscriptions against upstream API.

        If a renewal occurred on Polar but the webhook was dropped or missed:
        - Detects that current_period_end has advanced.
        - Updates local current_period_end.
        - Grants renewed monthly platform credits automatically.
        Never raises: failures land in returned outcomes and logs.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        outcomes: List[Dict[str, Any]] = []
        try:
            from src.payments.polar import polar_gateway
            from src.modules.billing.usage import usage_service
            rows = supabase_db.select("user_subscriptions", {"status": "active"}) or []
            polar_subs = [r for r in rows if r.get("payment_provider") == "polar" and r.get("provider_subscription_id")]
            for sub in polar_subs:
                user_id = sub.get("user_id")
                sub_ref = sub.get("provider_subscription_id")
                period_end = sub.get("current_period_end")
                if not (user_id and sub_ref):
                    continue
                # If period has expired or is unrecorded, query Polar truth
                if not period_end or period_end <= now_iso:
                    remote = polar_gateway.get_subscription(sub_ref)
                    if not remote:
                        outcomes.append({"user_id": user_id, "status": "gateway_unreachable"})
                        continue
                    remote_status = str(remote.get("status") or "").lower()
                    remote_period_end = remote.get("current_period_end")
                    if remote_status == "active":
                        if remote_period_end and remote_period_end > (period_end or ""):
                            # Advanced to new billing cycle! Reconcile credits & date
                            self.upsert_subscription(user_id, current_period_end=remote_period_end)
                            platforms = self.connected_platforms(user_id)
                            usage_service.grant_platform_credits(user_id, len(platforms) or 1)
                            logger.info(f"Reconciled renewal for user {user_id}: new period ending {remote_period_end}")
                            outcomes.append({"user_id": user_id, "status": "reconciled_renewed", "period_end": remote_period_end})
                        else:
                            outcomes.append({"user_id": user_id, "status": "still_current"})
                    elif remote_status in ("canceled", "revoked", "past_due"):
                        self.upsert_subscription(user_id, status=remote_status)
                        if remote_status in ("canceled", "revoked"):
                            self.sync_from_platforms(user_id, [], source="subscription")
                        logger.warning(f"Reconciled subscription termination for {user_id}: status={remote_status}")
                        outcomes.append({"user_id": user_id, "status": f"synced_{remote_status}"})
            return {"status": "success", "checked": len(polar_subs), "outcomes": outcomes}
        except Exception as e:
            logger.error(f"Subscription reconciliation failed: {e}")
            return {"status": "partial_error", "error": str(e)[:200], "outcomes": outcomes}


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

    def credit_pack_catalog(self) -> List[Dict[str, Any]]:
        """Self-serve AI-credit top-up packs.

        Deliberately settings-backed with a coded fallback rather than a new
        database table (same shape as _discount_percent below): pack sizes
        change rarely, unlike per-platform pricing, so a new migration would
        be more ceremony than the feature warrants for v1. Admin overrides via
        PUT /api/admin/site-settings {"credit_packs_pricing": {"credits_500": 7.99, ...}}.
        """
        from src.modules.billing.usage import CREDIT_PACKS
        try:
            overrides = supabase_db.get_setting("credit_packs_pricing") or {}
        except Exception:
            overrides = {}
        out = []
        for key, credits in CREDIT_PACKS.items():
            price = float(overrides.get(key, DEFAULT_CREDIT_PACK_PRICES_USD.get(key, 0)))
            out.append({"pack": key, "credits": credits, "price_usd": price})
        return out

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
            # The Polar discount reference driving checkout — null means the
            # coupon advertises a discount with no gateway discount behind it.
            "coupon_polar_id": (coupon or {}).get("polar_discount_id") or None,
            "total_usd": final,
        }


entitlement_service = EntitlementService()
pricing_service = PricingService()
