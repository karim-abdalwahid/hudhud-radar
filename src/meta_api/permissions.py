"""
Meta Token and Permission Scope Validator.
"""
from typing import Dict, Any, List
import httpx
from src.config import settings
from src.core.logger import logger
from src.core.exceptions import MetaAPIError

REQUIRED_PAGE_PERMISSIONS = [
    "pages_messaging",
    "pages_manage_metadata",
    "pages_read_engagement"
]

REQUIRED_INSTAGRAM_PERMISSIONS = [
    "instagram_basic",
    "instagram_manage_messages"
]


class PermissionsManager:
    """Inspects and validates Meta Access Tokens and permission scopes."""

    @staticmethod
    async def inspect_token(access_token: str, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Calls the Meta debug_token endpoint to verify token validity and scopes."""
        if not access_token:
            return {"is_valid": False, "error": "Access token is missing"}

        url = f"{settings.META_GRAPH_API_BASE_URL}/debug_token"
        params = {
            "input_token": access_token,
            "access_token": f"{app_id}|{app_secret}"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return {"is_valid": False, "error": f"Debug token returned HTTP {resp.status_code}"}
                data = resp.json().get("data", {})
                return {
                    "is_valid": data.get("is_valid", False),
                    "app_id": data.get("app_id"),
                    "type": data.get("type"),
                    "expires_at": data.get("expires_at"),
                    "scopes": data.get("scopes", []),
                    "issued_at": data.get("issued_at")
                }
        except Exception as e:
            logger.error(f"Error inspecting Meta access token: {e}")
            return {"is_valid": False, "error": str(e)}

    @staticmethod
    def verify_required_scopes(granted_scopes: List[str], platform: str = "facebook") -> Dict[str, Any]:
        """Checks if all required scopes are present in granted_scopes."""
        required = REQUIRED_PAGE_PERMISSIONS if platform == "facebook" else REQUIRED_INSTAGRAM_PERMISSIONS
        missing = [scope for scope in required if scope not in granted_scopes]
        return {
            "has_all_required": len(missing) == 0,
            "missing_scopes": missing,
            "granted_scopes": granted_scopes
        }
