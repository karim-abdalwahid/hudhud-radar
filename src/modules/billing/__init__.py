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

    # ---------------- Checkout (9.2) ----------------
    class CheckoutPayload(BaseModel):
        platforms: List[str]
        coupon: Optional[str] = None

    @app.post("/api/billing/checkout", tags=["Billing"])
    async def create_checkout(payload: CheckoutPayload, request: Request):
        """Creates a gateway checkout for the chosen platforms (coupon applied)."""
        session = _me(request)
        plats = [p.strip().lower() for p in payload.platforms if p.strip()]
        if not plats:
            raise HTTPException(status_code=400, detail="اختر منصة واحدة على الأقل")
        coupon_row = None
        if payload.coupon:
            rows = supabase_db.select("coupons", {"code": payload.coupon.strip().upper()}) or []
            if not rows or not rows[0].get("is_active"):
                raise HTTPException(status_code=400, detail="الكوبون غير صالح أو منتهي")
            coupon_row = rows[0]
            if coupon_row.get("applies_to_user"):
                target = coupon_row["applies_to_user"].strip().lower()
                me_email = session.get("email", "").strip().lower()
                if target not in (me_email, session.get("sub")):
                    raise HTTPException(status_code=403, detail="هذا الكوبون مخصص لحساب آخر")
        quote = pricing_service.quote(plats, coupon_row)
        if not quote.get("platforms"):
            raise HTTPException(status_code=400, detail="لا توجد منصات متاحة في الاختيار")
        user = {"id": session["sub"], "email": session["email"]}
        from src.payments.registry import active_gateway
        gateway = active_gateway()
        if not gateway:
            raise HTTPException(status_code=503, detail="بوابة الدفع غير مهيأة — تواصل معنا")
        from src.config import settings
        return_url = f"{settings.APP_BASE_URL.rstrip('/')}/billing/success"
        try:
            result = gateway.create_checkout(user, quote, return_url)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"status": "success", "quote": quote, **result}

    @app.get("/api/admin/billing/polar-diag", tags=["Billing"])
    async def polar_diagnostics(request: Request):
        """Admin-only: verifies Polar config presence + live API reachability.
        Never exposes the token itself."""
        _require_admin(request)
        from src.config import settings
        token = settings.POLAR_ACCESS_TOKEN or ""
        org = settings.POLAR_ORGANIZATION_ID or ""
        out = {
            "token_set": bool(token),
            "token_prefix": (token[:12] + "...") if token else None,
            "org_id_set": bool(org),
        }
        # live API probe (follow_redirects — Polar 307s unauthenticated probes)
        try:
            import httpx as _hx
            r = _hx.get("https://sandbox-api.polar.sh/v1/products/?limit=1",
                        headers={"Authorization": f"Bearer {token}"}, timeout=20,
                        follow_redirects=True)
            out["sandbox_api_status"] = r.status_code
            out["sandbox_reachable"] = r.status_code == 200
            if r.status_code == 401:
                out["hint"] = "TOKEN مرفوض — تأكد أنه من نفس الـ Organization (sandbox)"
        except Exception as e:
            out["sandbox_api_error"] = str(e)[:200]
        # live checkout dry-test with the mapped products (sandbox only)
        try:
            mapping = supabase_db.get_setting("polar_product_ids") or {}
            products = [mapping.get(p) for p in ("facebook", "instagram", "threads")]
            products = [p for p in products if p]
            if products and token:
                r2 = _hx.post("https://sandbox-api.polar.sh/v1/checkouts/",
                              headers={"Authorization": f"Bearer {token}"},
                              json={"products": products,
                                    "customer_email": "diag@hudhd.com"},
                              timeout=30, follow_redirects=True)
                out["checkout_test_status"] = r2.status_code
                if r2.status_code in (200, 201):
                    out["checkout_test_url"] = (r2.json().get("url") or "")[:70]
                else:
                    out["checkout_test_error"] = r2.text[:400]
            else:
                out["checkout_test_error"] = "missing products or token"
        except Exception as e:
            out["checkout_test_error"] = str(e)[:300]
        return {"status": "success", "diag": out}

    @app.post("/api/billing/trial", tags=["Billing"])
    async def start_trial_checkout(request: Request):
        """3-day all-platforms trial — requires card capture via the gateway."""
        session = _me(request)
        user = {"id": session["sub"], "email": session["email"]}
        from src.payments.registry import active_gateway
        gateway = active_gateway()
        if not gateway:
            raise HTTPException(status_code=503, detail="بوابة الدفع غير مهيأة")
        from src.config import settings
        return_url = f"{settings.APP_BASE_URL.rstrip('/')}/billing/success"
        try:
            result = gateway.start_trial(user, return_url)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"status": "success", **result}

    # ---------------- Coupons (9.3) ----------------
    class CouponCreatePayload(BaseModel):
        code: str
        kind: str = "percent"                      # percent|fixed|platform_unlock|credits
        value: float = 0
        platform: Optional[str] = None             # for platform_unlock
        applies_to_user: Optional[str] = None      # email; None = anyone
        max_total_uses: Optional[int] = None
        max_uses_per_user: int = 1
        expires_at: Optional[str] = None

    @app.get("/api/admin/billing/coupons", tags=["Billing"])
    async def list_coupons(request: Request):
        _require_admin(request)
        rows = supabase_db.select("coupons") or []
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return {"status": "success", "coupons": rows}

    @app.post("/api/admin/billing/coupons", tags=["Billing"])
    async def create_coupon(payload: CouponCreatePayload, request: Request):
        _require_admin(request)
        code = payload.code.strip().upper()
        if not code or len(code) < 4:
            raise HTTPException(status_code=400, detail="الكود قصير جداً")
        if payload.kind not in ("percent", "fixed", "platform_unlock", "credits"):
            raise HTTPException(status_code=400, detail="نوع كوبون غير معروف")
        if payload.kind == "percent" and not (0 < payload.value <= 100):
            raise HTTPException(status_code=400, detail="نسبة الخصم يجب أن تكون بين 1 و 100")
        existing = supabase_db.select("coupons", {"code": code}) or []
        if existing:
            raise HTTPException(status_code=400, detail="هذا الكود مستخدم بالفعل")
        applies_user_id = None
        if payload.applies_to_user:
            from src.core.auth import user_store
            target = user_store.get_by_email(payload.applies_to_user.strip().lower())
            if not target:
                raise HTTPException(status_code=404, detail="المستخدم المحدد غير موجود")
            applies_user_id = target["id"]
        created = supabase_db.insert("coupons", {
            "code": code, "kind": payload.kind, "value": payload.value,
            "platform": payload.platform, "applies_to_user": applies_user_id,
            "max_total_uses": payload.max_total_uses,
            "max_uses_per_user": payload.max_uses_per_user,
            "expires_at": payload.expires_at, "is_active": True,
        })
        return {"status": "success", "coupon": created}

    @app.delete("/api/admin/billing/coupons/{coupon_id}", tags=["Billing"])
    async def delete_coupon(coupon_id: str, request: Request):
        _require_admin(request)
        supabase_db.delete("coupons", coupon_id)
        return {"status": "success"}

    # ---------------- Site settings (9.3 — everything in one place) ----------------
    ALLOWED_SETTING_KEYS = (
        "payment_gateway", "payment_mode", "multi_platform_discounts",
        "pricing_usd", "currency_table", "theme_default", "registration_cap",
        "polar_product_ids",
    )

    class SiteSettingsPayload(BaseModel):
        payment_gateway: Optional[str] = None
        payment_mode: Optional[str] = None         # sandbox|live
        multi_platform_discounts: Optional[dict] = None
        pricing_usd: Optional[dict] = None          # {platform: price}
        currency_table: Optional[dict] = None       # {EG: {currency, rate, round_to}}
        theme_default: Optional[str] = None
        registration_cap: Optional[int] = None

    @app.get("/api/admin/site-settings", tags=["Admin Console"])
    async def get_site_settings(request: Request):
        _require_admin(request)
        out = {k: supabase_db.get_setting(k) for k in ALLOWED_SETTING_KEYS}
        return {"status": "success", "settings": out}

    @app.put("/api/admin/site-settings", tags=["Admin Console"])
    async def update_site_settings(payload: SiteSettingsPayload, request: Request):
        _require_admin(request)
        data = payload.model_dump(exclude_none=True)
        for k, v in data.items():
            if k not in ALLOWED_SETTING_KEYS:
                raise HTTPException(status_code=400, detail=f"مفتاح غير مسموح: {k}")
            supabase_db.set_setting(k, v)
        return {"status": "success", "updated": list(data.keys())}


module_registry.register_module(
    name="billing",
    description="Entitlements & composable pricing: quote, subscription status, admin catalog/settings, payment webhooks",
    register_router=register,
)
