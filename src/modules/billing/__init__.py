"""
Billing & Entitlements module (Phase 9.1) — the money brain.

Endpoints:
  GET  /api/billing/quote?platforms=facebook,instagram[&coupon=CODE]   → composable quote
  GET  /api/billing/subscription                                        → my subscription status
  GET  /api/admin/billing/catalog                                       → addon catalog (admin)
  PUT  /api/admin/billing/catalog/{platform}                            → edit price/availability
  GET  /api/admin/billing/settings                                      → discounts + trial config
  PUT  /api/admin/billing/settings                                      → update discounts/trial

Gates: platform routes/pages use require_entitlement via the service
(default-deny). Checkout creation arrives in 9.2 (Polar).
"""
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
from src.core.logger import logger
from src.core.modules import module_registry
from src.modules.billing.services import entitlement_service, pricing_service
from src.core.supabase_client import supabase_db


def _me(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    session = verify_session_token(token) if token else None
    if not session:
        raise HTTPException(status_code=401, detail="غير مصرح")
    return session


def _require_admin(request: Request):
    session = _me(request)
    if session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    return session


class CatalogUpdatePayload(BaseModel):
    price_usd: Optional[float] = None
    is_available: Optional[bool] = None


class BillingSettingsPayload(BaseModel):
    multi_platform_discounts: Optional[dict] = None   # {"2": 10, "3": 20}
    trial_days: Optional[int] = None


def register(app: FastAPI) -> None:
    @app.get("/api/billing/quote", tags=["Billing"])
    async def get_quote(request: Request, platforms: str, coupon: str = ""):
        """Composable quote for chosen platforms (public display is fine —
        no secrets; prices come from the catalog)."""
        plats = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        coupon_row = None
        if coupon:
            rows = supabase_db.select("coupons", {"code": coupon.strip().upper()}) or []
            if rows and rows[0].get("is_active"):
                coupon_row = rows[0]
        return {"status": "success", **pricing_service.quote(plats, coupon_row)}

    @app.get("/api/billing/subscription", tags=["Billing"])
    async def my_subscription(request: Request):
        session = _me(request)
        return {"status": "success",
                **entitlement_service.subscription_status(session["sub"])}

    @app.get("/api/admin/billing/catalog", tags=["Billing"])
    async def admin_catalog(request: Request):
        _require_admin(request)
        return {"status": "success", "catalog": pricing_service.catalog()}

    @app.put("/api/admin/billing/catalog/{platform}", tags=["Billing"])
    async def update_catalog(platform: str, payload: CatalogUpdatePayload, request: Request):
        _require_admin(request)
        rows = supabase_db.select("platform_addons_catalog", {"platform": platform}) or []
        if not rows:
            raise HTTPException(status_code=404, detail="المنصة غير موجودة في الكتالوج")
        updates = {k: v for k, v in payload.model_dump().items() if v is not None}
        from datetime import datetime, timezone
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = supabase_db.update("platform_addons_catalog", rows[0]["id"], updates)
        return {"status": "success", "addon": updated}

    @app.get("/api/admin/billing/settings", tags=["Billing"])
    async def get_billing_settings(request: Request):
        _require_admin(request)
        discounts = supabase_db.get_setting("billing_discounts") or {"multi_platform": {"2": 10, "3": 20}}
        return {"status": "success", "discounts": discounts, "trial_days": 3}

    @app.put("/api/admin/billing/settings", tags=["Billing"])
    async def update_billing_settings(payload: BillingSettingsPayload, request: Request):
        _require_admin(request)
        if payload.multi_platform_discounts is not None:
            supabase_db.set_setting("billing_discounts", payload.multi_platform_discounts)
        return {"status": "success"}


    @app.post("/api/payments/webhook/{provider}", tags=["Payments"])
    async def payment_webhook(provider: str, request: Request):
        """Payment gateway webhooks — VERIFIED, IDEMPOTENT, fail-closed.
        Flow: signature check → dedup (payment_events) → normalize → sync
        entitlements from payment truth. Any failure = 400/500 (provider
        retries automatically per its own policy)."""
        import json as _json

        from src.core.event_dedup import event_deduplicator
        from src.core.logger import logger
        from src.payments.registry import get_gateway

        gateway = get_gateway(provider)
        if not gateway:
            raise HTTPException(status_code=404, detail="Unknown payment provider")

        raw = await request.body()
        headers = dict(request.headers)
        if not gateway.verify_webhook(headers, raw):
            logger.warning(f"{provider} webhook signature INVALID — rejected")
            raise HTTPException(status_code=400, detail="Invalid signature")

        try:
            payload = _json.loads(raw.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

        event = gateway.parse_event(headers, payload)
        event_id = f"{provider}:{event['event_id']}" if event.get("event_id") else ""
        if not event_id or not event_deduplicator.claim(event_id, f"payment:{provider}"):
            return {"status": "duplicate_ignored"}

        # Audit log FIRST (idempotent record even if later steps fail)
        supabase_db.insert("payment_events", {
            "provider": provider, "event_id": event["event_id"] or "unknown",
            "event_type": event["event_type"], "user_id": None,
            "payload": event.get("raw", {}),
        })

        # Resolve local user by email (Google/Email accounts share the table)
        user_email = (event.get("user_email") or "").strip().lower()
        target_user = None
        if user_email:
            try:
                from src.core.auth import user_store
                target_user = user_store.get_by_email(user_email)
            except Exception:
                target_user = None

        # Apply payment truth
        from src.modules.billing.services import entitlement_service
        kind = event.get("kind")
        if kind == "subscription_activated" and target_user:
            platforms = event.get("platforms") or []
            if platforms:
                entitlement_service.sync_from_platforms(target_user["id"], platforms,
                                                        source="subscription")
            entitlement_service.upsert_subscription(
                target_user["id"], status="active",
                payment_provider=provider,
                provider_subscription_id=event.get("subscription_ref"))
            try:
                from src.modules.notifications.service import notification_service
                notification_service.create(target_user["id"],
                    "✅ تم تفعيل اشتراكك",
                    f"المنصات المفعلة: {', '.join(platforms) if platforms else 'أصبحت نشطة'}",
                    "success", {"job": "payment"})
            except Exception:
                pass
        elif kind == "subscription_canceled" and target_user:
            entitlement_service.upsert_subscription(target_user["id"], status="canceled")
            entitlement_service.sync_from_platforms(target_user["id"], [],
                                                    source="subscription")
            try:
                from src.modules.notifications.service import notification_service
                notification_service.create(target_user["id"],
                    "⚠️ تم إلغاء اشتراكك",
                    "المنصات المتوقفة — فعّل اشتراكاً لاستئناف الخدمة",
                    "warning", {"job": "payment"})
            except Exception:
                pass

        logger.info(f"{provider} webhook processed: {event['event_type']} kind={kind}")
        return {"status": "received", "kind": kind}


module_registry.register_module(
    name="billing",
    description="Entitlements & composable pricing: quote, subscription status, admin catalog/settings, payment webhooks",
    register_router=register,
)
