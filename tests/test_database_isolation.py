import base64
import json

from src.core.supabase_client import SupabaseManager, supabase_db


def test_suite_uses_isolated_in_memory_database():
    """Protect the live CRM/content database from fixtures and test writes."""
    assert supabase_db.is_connected is False
    assert "app_settings" in supabase_db.memory_db.tables


def test_service_role_key_validation_rejects_anon_jwt():
    """An anon key must never be accepted just because its env-var name is wrong."""
    def jwt_with_role(role: str) -> str:
        payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
        return f"header.{payload}.signature"

    assert SupabaseManager._is_service_role_key(jwt_with_role("service_role")) is True
    assert SupabaseManager._is_service_role_key(jwt_with_role("anon")) is False
    assert SupabaseManager._is_service_role_key("not-a-key") is False
