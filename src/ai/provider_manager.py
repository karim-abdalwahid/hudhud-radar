"""
AI Provider & Model Management (Phase 8 — opencode-style).

Admin connects providers:
- OFFICIAL (built-in registry with logos): Google AI, Anthropic, OpenAI, OpenRouter
- CUSTOM: any OpenAI-compatible endpoint (base URL + optional API key +
  optional custom headers + manual model list)

AUTO-DISCOVERY: on save / "refresh connection" → fetch the provider's model
list and record what the credentials can actually access. Unavailable models
are hidden from clients. Enabled+available = visible in the Brain selector.

API keys are stored in Supabase (service-role only) and NEVER returned raw
to the frontend (masked previews only).
"""
import time
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db

# Official provider registry (logos rendered client-side via logo_key)
OFFICIAL_PROVIDERS = {
    "google": {
        "display_name": "Google AI",
        "logo_key": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "auth": "api_key",  # x-goog-api-key
    },
    "anthropic": {
        "display_name": "Anthropic",
        "logo_key": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "auth": "bearer",  # x-api-key + anthropic-version headers
    },
    "openai": {
        "display_name": "OpenAI",
        "logo_key": "openai",
        "base_url": "https://api.openai.com/v1",
        "auth": "bearer",
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "logo_key": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "auth": "bearer",
    },
}


def _mask(key: Optional[str]) -> str:
    if not key:
        return ""
    return f"{key[:6]}…{key[-4:]}" if len(key) > 12 else "•••"


class AIProviderManager:
    """CRUD + model discovery for AI providers (admin-managed)."""

    # ------------------------------------------------------------------
    # Discovery per provider kind
    # ------------------------------------------------------------------
    def discover_models(self, provider: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetches the model list from the provider API. Returns [{model_id, display_name}]."""
        kind = provider.get("kind", "official")
        key = (provider.get("provider_key") or "").lower()
        pkey = provider.get("api_key")
        base = (provider.get("base_url") or "").rstrip("/")
        headers: Dict[str, str] = {}
        try:
            if kind == "official" and key == "google":
                if not pkey:
                    return []
                r = httpx.get(f"{base}/models", headers={"X-goog-api-key": pkey}, timeout=15)
                if r.status_code != 200:
                    logger.warning(f"Google model list failed: {r.status_code} {r.text[:150]}")
                    return []
                out = []
                for m in r.json().get("models", []):
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        mid = m.get("name", "").replace("models/", "")
                        if mid and ("flash" in mid or "pro" in mid or "gemini" in mid):
                            out.append({"model_id": mid, "display_name": mid})
                return out

            # OpenAI-compatible discovery (official openai/openrouter/anthropic/custom)
            if not base:
                return []
            if kind == "official" and key == "anthropic":
                if not pkey:
                    return []
                headers = {"x-api-key": pkey, "anthropic-version": "2023-06-01"}
            else:
                if not pkey:
                    return []
                headers = {"Authorization": f"Bearer {pkey}"}
                # custom headers from provider config
                for h in (provider.get("custom_headers") or []):
                    if h.get("header") and h.get("value"):
                        headers[h["header"]] = h["value"]

            r = httpx.get(f"{base}/models", headers=headers, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Model list failed ({r.status_code}): {r.text[:150]}")
                return []
            data = r.json().get("data", [])
            out = []
            for m in data:
                mid = m.get("id") or m.get("name")
                if mid:
                    out.append({"model_id": mid, "display_name": mid})
            return out
        except Exception as e:
            logger.warning(f"Model discovery error for {provider.get('provider_key')}: {e}")
            return []

    def sync_provider_models(self, provider_id: str) -> Dict[str, Any]:
        """Re-discovers models for a provider; marks availability; preserves admin toggles."""
        prov = self._get_provider_row(provider_id)
        if not prov:
            return {"status": "error", "detail": "Provider not found"}

        discovered = self.discover_models(prov)
        now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())

        existing = {m["model_id"]: m for m in (supabase_db.select("ai_models", {"provider_id": provider_id}) or [])}
        seen = set()
        for m in discovered:
            mid = m["model_id"]
            seen.add(mid)
            if mid in existing:
                supabase_db.update("ai_models", existing[mid]["id"], {"available": True, "updated_at": now})
            else:
                supabase_db.insert("ai_models", {
                    "provider_id": provider_id, "model_id": mid,
                    "display_name": m["display_name"], "available": True, "source": "discovered",
                })
        # Models no longer returned (or provider broken) → unavailable for
        # discovered rows; manual rows keep their availability (admin's explicit choice).
        for mid, row in existing.items():
            if mid not in seen and row.get("source") == "discovered":
                supabase_db.update("ai_models", row["id"], {"available": False, "updated_at": now})

        supabase_db.update("ai_providers", provider_id, {"last_synced_at": now})
        models = supabase_db.select("ai_models", {"provider_id": provider_id}) or []
        return {
            "status": "success",
            "discovered": len(discovered),
            "available": sum(1 for m in models if m.get("available")),
            "models": models,
        }

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def list_providers(self) -> List[Dict[str, Any]]:
        provs = supabase_db.select("ai_providers") or []
        out = []
        for p in provs:
            models = supabase_db.select("ai_models", {"provider_id": p["id"]}) or []
            out.append({
                "id": p["id"],
                "kind": p["kind"],
                "provider_key": p["provider_key"],
                "display_name": p["display_name"],
                "logo_key": p["logo_key"],
                "base_url": p.get("base_url"),
                "custom_headers": p.get("custom_headers", []),
                "status": p["status"],
                "api_key_masked": _mask(p.get("api_key")),
                "last_synced_at": p.get("last_synced_at"),
                "models_count": len(models),
                "enabled_models": sum(1 for m in models if m.get("enabled") and m.get("available")),
            })
        return out

    def create_provider(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        kind = payload.get("kind", "official")
        key = (payload.get("provider_key") or "").strip().lower()
        if kind == "official":
            if key not in OFFICIAL_PROVIDERS:
                raise ValueError("مزود رسمي غير معروف")
            reg = OFFICIAL_PROVIDERS[key]
            row = {
                "kind": "official",
                "provider_key": key,
                "display_name": reg["display_name"],
                "logo_key": reg["logo_key"],
                "base_url": reg["base_url"],
                "api_key": (payload.get("api_key") or "").strip() or None,
                "status": "active",
            }
        else:
            key = key or f"custom-{int(time.time())}"
            row = {
                "kind": "custom",
                "provider_key": key,
                "display_name": payload.get("display_name") or key,
                "logo_key": "custom",
                "base_url": (payload.get("base_url") or "").strip(),
                "api_key": (payload.get("api_key") or "").strip() or None,
                "custom_headers": payload.get("custom_headers") or [],
                "status": "active",
            }
            if not row["base_url"]:
                raise ValueError("Base URL مطلوب للمزود المخصص")

        created = supabase_db.insert("ai_providers", row)
        return {"status": "success", "provider_id": created["id"]}

    def update_provider(self, provider_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {}
        if "api_key" in updates and updates["api_key"]:
            allowed["api_key"] = updates["api_key"].strip()
        if "base_url" in updates:
            allowed["base_url"] = updates["base_url"]
        if "custom_headers" in updates:
            allowed["custom_headers"] = updates["custom_headers"]
        if "status" in updates and updates["status"] in ("active", "disabled"):
            allowed["status"] = updates["status"]
        if "display_name" in updates and updates["display_name"]:
            allowed["display_name"] = updates["display_name"]
        supabase_db.update("ai_providers", provider_id, allowed)
        return {"status": "success"}

    def delete_provider(self, provider_id: str) -> bool:
        try:
            supabase_db.delete("ai_providers", provider_id)  # cascades models
            return True
        except Exception as e:
            logger.error(f"Provider delete failed: {e}")
            return False

    def _get_provider_row(self, provider_id: str) -> Optional[Dict[str, Any]]:
        rows = supabase_db.select("ai_providers", {"id": provider_id})
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # Model toggles (admin) + client brain selection
    # ------------------------------------------------------------------
    def list_models(self, provider_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if provider_id:
            models = supabase_db.select("ai_models", {"provider_id": provider_id}) or []
        else:
            models = supabase_db.select("ai_models") or []
        provs = {p["id"]: p for p in (supabase_db.select("ai_providers") or [])}
        out = []
        for m in models:
            p = provs.get(m["provider_id"], {})
            out.append({
                "id": m["id"],
                "provider_id": m["provider_id"],
                "provider_key": p.get("provider_key"),
                "provider_name": p.get("display_name"),
                "logo_key": p.get("logo_key"),
                "model_id": m["model_id"],
                "display_name": m["display_name"],
                "enabled": m.get("enabled", True),
                "available": m.get("available", False),
                "source": m.get("source", "discovered"),
            })
        return out

    def set_model_toggle(self, model_id: str, enabled: bool) -> Dict[str, Any]:
        supabase_db.update("ai_models", model_id, {"enabled": bool(enabled)})
        return {"status": "success", "model_id": model_id, "enabled": enabled}

    def add_manual_model(self, provider_id: str, model_id: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        created = supabase_db.insert("ai_models", {
            "provider_id": provider_id,
            "model_id": model_id.strip(),
            "display_name": (display_name or model_id).strip(),
            "available": True,
            "source": "manual",
        })
        return {"status": "success", "model": created}

    def enabled_brain_options(self) -> List[Dict[str, Any]]:
        """Client-facing: enabled + available models from active providers."""
        provs = {p["id"]: p for p in (supabase_db.select("ai_providers") or []) if p.get("status") == "active"}
        models = supabase_db.select("ai_models") or []
        out = []
        for m in models:
            p = provs.get(m["provider_id"])
            if not p or not m.get("enabled", True) or not m.get("available", False):
                continue
            out.append({
                "ref": f"{p['provider_key']}/{m['model_id']}",
                "provider_name": p["display_name"],
                "logo_key": p["logo_key"],
                "model_id": m["model_id"],
                "display_name": m["display_name"],
            })
        return out


ai_provider_manager = AIProviderManager()
