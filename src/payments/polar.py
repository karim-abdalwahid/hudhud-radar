"""
Polar.sh payment gateway (sandbox first) — implements PaymentProvider.

Polar specifics:
  - API: https://sandbox-api.polar.sh (test) / https://api.polar.sh (live)
  - Webhooks use Svix signature scheme:
      headers: svix-id, svix-timestamp, svix-signature
      signed content: "{id}.{timestamp}.{raw_body}"
      signature: base64(HMAC-SHA256(webhook_secret, signed_content))
  - Checkout: POST /v1/checkouts with products or products+metadata
  - Products are pre-created in the Polar dashboard (sandbox) — one per
    platform addon; product ids come from env/settings (PricingService).
"""
import base64
import hashlib
import hmac
import time
from typing import Any, Dict, Optional

import httpx

from src.core.logger import logger
from src.core.modules import module_registry
from src.core.supabase_client import supabase_db
from src.payments.base import PaymentProvider

SANDBOX_API = "https://sandbox-api.polar.sh"
LIVE_API = "https://api.polar.sh"


class PolarGateway(PaymentProvider):
    name = "polar"

    def __init__(self):
        self.mode = self._env_mode()
        self.api = SANDBOX_API if self.mode == "sandbox" else LIVE_API

    @staticmethod
    def _env_mode() -> str:
        try:
            return (supabase_db.get_setting("payment_mode") or "sandbox")
        except Exception:
            return "sandbox"

    def _headers(self) -> Dict[str, str]:
        token = self._token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    @staticmethod
    def _token() -> str:
        from src.config import settings
        return settings.POLAR_ACCESS_TOKEN or ""

    @staticmethod
    def _webhook_secret() -> str:
        from src.config import settings
        return settings.POLAR_WEBHOOK_SECRET or ""

    @staticmethod
    def _org_id() -> str:
        from src.config import settings
        return settings.POLAR_ORGANIZATION_ID or ""

    def _product_ids(self) -> Dict[str, str]:
        """platform → polar product id (admin-editable mapping)."""
        try:
            return supabase_db.get_setting("polar_product_ids") or {}
        except Exception:
            return {}

    # ------------------------------------------------------------------
    def create_checkout(self, user: Dict[str, Any], quote: Dict[str, Any],
                        return_url: str) -> Dict[str, Any]:
        """One checkout containing the product for EACH chosen platform."""
        if not self._token():
            raise RuntimeError("POLAR_ACCESS_TOKEN غير مضبوط")
        mapping = self._product_ids()
        products = []
        for p in quote.get("platforms", []):
            pid = mapping.get(p)
            if not pid:
                raise RuntimeError(f"لا يوجد منتج Polar مربوط للمنصة: {p} — أضفه من إعدادات الأدمن")
            products.append(pid)
        payload: Dict[str, Any] = {
            "products": products,
            "success_url": return_url,
            "customer_email": user.get("email"),
            # Polar metadata values MUST be strings (nested/list values → 422)
            "metadata": {"user_id": str(user.get("id") or ""),
                         "platforms": ",".join(quote.get("platforms", []))},
        }
        if quote.get("coupon_discount_usd"):
            payload["discount_id"] = quote.get("coupon_polar_id")
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.post(f"{self.api}/v1/checkouts/", headers=self._headers(), json=payload)
            if r.status_code not in (200, 201):
                logger.error(f"Polar checkout failed: {r.status_code} {r.text[:300]}")
                # TEMP diag: passthrough error body to identify exact API rejection
                raise RuntimeError(f"Polar {r.status_code}: {r.text[:200]}")
            data = r.json()
        return {"checkout_url": data.get("url"), "provider_ref": data.get("id")}

    def start_trial(self, user: Dict[str, Any], return_url: str) -> Dict[str, Any]:
        """Trial = checkout over the TRIAL products (3-day free period configured
        per product in the Polar dashboard, card required). Falls back to normal
        products if trial mapping is absent."""
        mapping = self._product_ids()
        trial_ids = [mapping.get(f"trial-{p}") for p in ("facebook", "instagram", "threads")]
        trial_ids = [t for t in trial_ids if t]
        if not trial_ids:
            logger.warning("No trial product mapping — falling back to regular products")
            return self.create_checkout(
                user, {"platforms": ["facebook", "instagram", "threads"],
                       "coupon_discount_usd": 0}, return_url)
        payload = {
            "products": trial_ids,
            "success_url": return_url,
            "customer_email": user.get("email"),
            "metadata": {"user_id": str(user.get("id") or ""),
                         "platforms": "facebook,instagram,threads",
                         "trial": "true"},
        }
        with httpx.Client(timeout=30, follow_redirects=True) as c:
            r = c.post(f"{self.api}/v1/checkouts/", headers=self._headers(), json=payload)
            if r.status_code not in (200, 201):
                logger.error(f"Polar trial checkout failed: {r.status_code} {r.text[:300]}")
                raise RuntimeError("تعذر إنشاء تجربة الدفع — حاول مجدداً")
            data = r.json()
        return {"checkout_url": data.get("url"), "provider_ref": data.get("id")}

    # ------------------------------------------------------------------
    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Svix scheme, fail-closed, 5-minute timestamp tolerance."""
        secret = self._webhook_secret()
        if not secret:
            logger.error("POLAR_WEBHOOK_SECRET missing — webhook rejected (fail-closed)")
            return False
        svix_id = headers.get("svix-id") or headers.get("webhook-id")
        svix_ts = headers.get("svix-timestamp") or headers.get("webhook-timestamp")
        svix_sig = headers.get("svix-signature") or headers.get("webhook-signature")
        if not (svix_id and svix_ts and svix_sig):
            return False
        try:
            if abs(time.time() - int(svix_ts)) > 300:
                logger.warning("Polar webhook timestamp outside tolerance — rejected")
                return False
        except ValueError:
            return False
        secret_bytes = base64.b64decode(secret.removeprefix("whsec_"))
        signed = f"{svix_id}.{svix_ts}.".encode("utf-8") + raw_body
        expected = base64.b64encode(
            hmac.new(secret_bytes, signed, hashlib.sha256).digest()).decode()
        provided = svix_sig.split(" ")[-1]  # "v1,<sig>" format takes last
        provided = provided.split(",")[-1] if "," in provided else provided
        if not hmac.compare_digest(expected, provided):
            logger.warning("Polar webhook signature INVALID — rejected")
            return False
        return True

    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        event_type = payload.get("type", "")
        data = payload.get("data", {}) or {}
        meta = data.get("metadata") or {}
        user_email = (data.get("customer", {}) or {}).get("email") or meta.get("email")
        platforms = meta.get("platforms") or []
        if isinstance(platforms, str):
            import json as _json
            try:
                platforms = _json.loads(platforms)
            except Exception:
                platforms = [p.strip() for p in platforms.split(",") if p.strip()]
        # checkout.created carries NO metadata — resolve platforms from the
        # product_id(s) via our product mapping (order/subscription events too)
        if not platforms:
            def _resolve(obj: Any) -> List[str]:
                found = []
                mapping = self._product_ids()
                pid = (obj or {}).get("product_id")
                if pid:
                    for plat, prod_id in mapping.items():
                        if prod_id == pid and not plat.startswith("trial-"):
                            found.append(plat)
                for pp in (obj or {}).get("products", []) or []:
                    for plat, prod_id in mapping.items():
                        if prod_id == pp.get("id") and not plat.startswith("trial-") and plat not in found:
                            found.append(plat)
                return found
            platforms = _resolve(data) or _resolve(data.get("subscription") or {})
        kind = "other"
        if event_type in ("subscription.active", "subscription.created", "order.paid"):
            kind = "subscription_activated"
        elif event_type in ("subscription.canceled", "subscription.revoked"):
            kind = "subscription_canceled"
        elif event_type == "subscription.past_due":
            kind = "subscription_past_due"
        return {
            "event_id": payload.get("id", ""),
            "event_type": event_type,
            "kind": kind,
            "user_email": user_email,
            "platforms": platforms,
            "subscription_ref": data.get("subscription_id") or data.get("id"),
            "raw": payload,
        }


polar_gateway = PolarGateway()

module_registry.register_module(
    name="polar_gateway",
    description="Polar.sh payment gateway (sandbox/live) — checkout, svix webhooks",
)
