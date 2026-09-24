"""
Data Privacy endpoints required for Meta App Review & platform compliance:
- /privacy           : Public privacy policy page
- /data-deletion     : Data deletion instructions page + deletion callback API

Registered explicitly via register_compliance_routes(app) to avoid circular imports.
"""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.core.supabase_client import supabase_db
from src.core.logger import logger


# Kept for backward compatibility with the JSON admin format
class DataDeletionCallback(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None




def register_compliance_routes(app: FastAPI):
    """Registers privacy & data-deletion routes on the FastAPI app."""

    # NOTE: /privacy is now served by the dedicated legal module (bilingual,
    # full policy). This module keeps the Meta-required /data-deletion page
    # and the signed callback endpoints only.

    @app.get("/data-deletion", response_class=HTMLResponse, include_in_schema=False)
    async def data_deletion_page(request: Request):
        """Data deletion instructions page (Meta App Review requirement)."""
        from src.modules.legal import render_legal_document
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        conf_id = request.query_params.get("id")
        return HTMLResponse(content=render_legal_document("data-deletion", lang=lang, confirmation_id=conf_id))

    @app.get("/api/data-deletion", response_class=HTMLResponse, include_in_schema=False)
    async def data_deletion_api_info(request: Request):
        """GET handler so Meta reviewers and users who visit this URL in a
        browser see the deletion instructions page instead of 405."""
        from src.modules.legal import render_legal_document
        lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        conf_id = request.query_params.get("id")
        return HTMLResponse(content=render_legal_document("data-deletion", lang=lang, confirmation_id=conf_id))

    @app.post("/api/data-deletion", tags=["Compliance"])
    async def data_deletion_callback(request: Request):
        """
        Meta Data Deletion Request Callback (REQUIRED by Meta platform terms —
        this exact endpoint URL goes in the Threads API "Delete data callback URL"
        field and App settings → Basic → Data deletion).

        Supports Meta's official form-encoded `signed_request` format AND our
        JSON admin format. Responds with the Meta-required schema:
        {"url": <status page>, "confirmation_code": <code>}
        """
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod
        import secrets as secrets_mod

        from src.config import settings

        content_type = request.headers.get("content-type", "")
        user_id: Optional[str] = None
        user_email: Optional[str] = None

        # SECURITY: deletion is ONLY allowed via Meta's signed_request protocol.
        # A previous unverified application/json branch allowed anyone on the
        # internet to delete any account by email — removed (fail-closed).
        if "application/json" in content_type:
            return JSONResponse(status_code=400, content={
                "error": "data deletion requires Meta signed_request (form-encoded)"
            })
        form = await request.form()
        signed_request = form.get("signed_request")
        if not signed_request:
            return JSONResponse(status_code=400, content={"error": "signed_request required"})
        # Verify against either app secret (callback may be configured on either app)
        try:
            enc_sig, enc_payload = str(signed_request).split(".", 1)
            sig = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
            raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
            data = json_mod.loads(raw)
            verified = False
            for secret in (settings.THREADS_APP_SECRET, settings.META_APP_SECRET):
                if not secret:
                    continue
                expected = hmac_mod.new(secret.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
                if hmac_mod.compare_digest(sig, expected):
                    verified = True
                    break
            if not verified:
                return JSONResponse(status_code=403, content={"error": "invalid signed_request signature"})
            user_id = str(data.get("user_id")) if data.get("user_id") else None
        except Exception as e:
            logger.error(f"Signed request parse failed: {e}")
            return JSONResponse(status_code=400, content={"error": "malformed signed_request"})

        if not user_id and not user_email:
            # Meta may send an app-scoped id we cannot map to a local user —
            # log it for manual action and still return a compliant confirmation.
            logger.warning("Data deletion request without mappable user id")

        deleted = {"users": 0}
        try:
            if user_id:
                try:
                    supabase_db.delete("users", user_id)
                    deleted["users"] += 1
                except Exception:
                    pass
            if user_email:
                rows = supabase_db.select("users", {"email": user_email.lower()}) or []
                for u in rows:
                    supabase_db.delete("users", u["id"])
                    deleted["users"] += 1
        except Exception as e:
            logger.error(f"Data deletion error: {e}")
            return JSONResponse(status_code=500, content={"error": "deletion failed"})

        confirmation_code = secrets_mod.token_hex(8)
        # The user may have just been deleted, and an app-scoped Meta id may
        # not map to a Hudhud user at all.  Do not recreate tenantless audit
        # rows after the SaaS hardening migration; the server log retains the
        # operational event instead.
        logger.info("Completed Meta data-deletion callback: deleted=%s", deleted)

        # Meta-required response schema (Data Deletion Request Callback spec)
        return JSONResponse(content={
            "url": f"{settings.APP_BASE_URL.rstrip('/')}/data-deletion?id={confirmation_code}",
            "confirmation_code": confirmation_code,
        })

    @app.post("/api/deauthorize", tags=["Compliance"])
    async def deauthorize_callback(request: Request):
        """
        Meta Deauthorization Callback (App Dashboard → Business login settings /
        Facebook Login → Deauthorize callback URL). Meta POSTs a signed_request
        when a user deauthorizes the app from their Facebook/Instagram settings.

        Verifies signature against either app secret, clears stored platform
        credentials (the deauthorizing identity's tokens are dead), and logs
        the event. Returns 200 as required.
        """
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod

        from src.config import settings

        try:
            form = await request.form()
            signed_request = form.get("signed_request")
            if not signed_request:
                return JSONResponse(status_code=400, content={"error": "signed_request required"})
            enc_sig, enc_payload = str(signed_request).split(".", 1)
            sig = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
            raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
            data = json_mod.loads(raw)
            verified = False
            for secret in (settings.THREADS_APP_SECRET, settings.META_APP_SECRET,
                           getattr(settings, "IG_APP_SECRET", None)):
                if not secret:
                    continue
                expected = hmac_mod.new(secret.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
                if hmac_mod.compare_digest(sig, expected):
                    verified = True
                    break
            if not verified:
                return JSONResponse(status_code=403, content={"error": "invalid signature"})

            # Deauthorized → matching tenant-owned platform tokens are dead.
            try:
                from src.modules.connections.service import connection_service
                pid = str(data.get("user_id", ""))
                revoked = 0
                for p in ("facebook", "instagram", "threads"):
                    revoked += connection_service.revoke_by_platform_user(p, pid)
                if not pid:
                    connection_service.revoke_by_platform_user("facebook", "")
            except Exception as rev_err:
                logger.warning(f"per-user revoke skipped: {rev_err}")
            # The callback carries a Meta app-scoped id, not necessarily a
            # Hudhud tenant id.  Keep it out of the tenant audit table rather
            # than creating an ownerless row.
            logger.info("Processed Meta deauthorization callback for platform id=%s", data.get("user_id", ""))
            return {"success": True, "revoked": True}
        except Exception as e:
            logger.error(f"Deauthorize callback error: {e}")
            return JSONResponse(status_code=400, content={"error": "callback failed"})

    @app.post("/api/threads/uninstall", tags=["Compliance"])
    async def threads_uninstall_callback(request: Request):
        """
        Threads "Uninstall Callback URL" target. Meta POSTs a signed_request
        when a user removes the app. Verifies signature, clears stored
        Threads credentials, and logs the event. Returns 200 as required.
        """
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod

        from src.config import settings

        try:
            form = await request.form()
            signed_request = form.get("signed_request")
            if not signed_request:
                return JSONResponse(status_code=400, content={"error": "signed_request required"})
            enc_sig, enc_payload = str(signed_request).split(".", 1)
            sig = base64.urlsafe_b64decode(enc_sig + "=" * (-len(enc_sig) % 4))
            raw = base64.urlsafe_b64decode(enc_payload + "=" * (-len(enc_payload) % 4))
            data = json_mod.loads(raw)
            verified = False
            for secret in (settings.THREADS_APP_SECRET, settings.META_APP_SECRET):
                if not secret:
                    continue
                expected = hmac_mod.new(secret.encode(), enc_payload.encode("ascii"), hashlib.sha256).digest()
                if hmac_mod.compare_digest(sig, expected):
                    verified = True
                    break
            if not verified:
                return JSONResponse(status_code=403, content={"error": "invalid signature"})

            # The user uninstalled → revoke their tenant-owned Threads connection.
            try:
                from src.modules.connections.service import connection_service
                connection_service.revoke_by_platform_user("threads", str(data.get("user_id", "")))
            except Exception:
                pass
            logger.info("Processed Threads uninstall callback for platform id=%s", data.get("user_id", ""))
            return {}
        except Exception as e:
            logger.error(f"Uninstall callback error: {e}")
            return JSONResponse(status_code=400, content={"error": "callback failed"})
