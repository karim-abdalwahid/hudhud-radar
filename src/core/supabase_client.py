"""
Supabase PostgreSQL Client Wrapper with development/in-memory fallback mode.
"""
from typing import Optional, Dict, Any, List
import base64
import json
import uuid
from datetime import datetime, timezone
from src.config import settings
from src.core.logger import logger
from src.core.exceptions import DatabaseConnectionError

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = Any


class InMemoryDatabase:
    """Mock store simulating Supabase tables for local testing and initial setup."""
    def __init__(self):
        self.tables = {
            "leads": [],
            "messages": [],
            "identity_verification_queue": [],
            "activity_logs": [],
            "page_performance_metrics": [],
            "campaigns": [],
            "content_posts": [],
            "app_settings": [],
        }

    def insert(self, table: str, row: Dict[str, Any]) -> Dict[str, Any]:
        if table not in self.tables:
            self.tables[table] = []
        record = dict(row)
        if "id" not in record or not record["id"]:
            record["id"] = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if "created_at" not in record:
            record["created_at"] = now
        if "updated_at" not in record:
            record["updated_at"] = now
        self.tables[table].append(record)
        return record

    def select(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        rows = self.tables.get(table, [])
        if not filters:
            return [dict(r) for r in rows]
        filtered = []
        for r in rows:
            match = True
            for k, v in filters.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                filtered.append(dict(r))
        return filtered

    def update(self, table: str, record_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rows = self.tables.get(table, [])
        for r in rows:
            if r.get("id") == record_id:
                r.update(updates)
                r["updated_at"] = datetime.now(timezone.utc).isoformat()
                return dict(r)
        return None

    def delete(self, table: str, record_id: str) -> bool:
        rows = self.tables.get(table, [])
        initial_len = len(rows)
        self.tables[table] = [r for r in rows if r.get("id") != record_id]
        return len(self.tables[table]) < initial_len


class SupabaseManager:
    """Manages connection to Supabase or routes to InMemoryDatabase in development/testing."""

    def __init__(self):
        self.client: Optional[Client] = None
        self.is_connected = False
        self.memory_db = InMemoryDatabase()
        self._initialize()

    def _initialize(self):
        service_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if settings.TESTING:
            logger.info("TESTING mode enabled. Using isolated in-memory database.")
            return
        if service_key and not self._is_service_role_key(service_key):
            message = (
                "SUPABASE_SERVICE_ROLE_KEY is not a service-role key. "
                "Use the server-side service_role/secret key; never use the anon key here."
            )
            if settings.APP_ENV.lower() == "production":
                raise DatabaseConnectionError(message)
            logger.warning(message + " Using in-memory database.")
            return
        if SUPABASE_AVAILABLE and settings.SUPABASE_URL and service_key:
            try:
                self.client = create_client(settings.SUPABASE_URL, service_key)
                self.is_connected = True
                logger.info("Successfully connected to Supabase cloud instance.")
            except Exception as e:
                logger.warning(f"Failed to connect to Supabase: {e}. Falling back to in-memory store.")
                self.is_connected = False
        else:
            if settings.APP_ENV.lower() == "production":
                logger.error(
                    "PRODUCTION WITHOUT SUPABASE: writes would vanish on serverless recycle. "
                    "InMemoryDatabase will serve reads but REJECT writes (fail-loud, no silent data loss)."
                )
            else:
                logger.info("Supabase credentials not fully configured. Using local in-memory store for development/testing.")
            self.is_connected = False

    @staticmethod
    def _is_service_role_key(key: str) -> bool:
        """Accept modern secret keys and legacy JWT keys carrying the service_role claim."""
        if key.startswith("sb_secret_"):
            return True
        try:
            payload_segment = key.split(".")[1]
            payload_segment += "=" * (-len(payload_segment) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_segment))
            return payload.get("role") == "service_role"
        except (IndexError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return False

    def _reject_production_memory_write(self, table: str, op: str):
        """ZERO-FABRICATION: in production without Supabase, writes to the
        in-memory DB would 'succeed' then evaporate on cold start. Fail loud
        instead of silently losing data."""
        if settings.APP_ENV.lower() == "production":
            raise DatabaseConnectionError(
                f"Production write rejected: Supabase is not connected; "
                f"in-memory {op} on '{table}' would silently lose data on serverless."
            )

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row into the specified table."""
        if self.is_connected and self.client:
            try:
                res = self.client.table(table).insert(data).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
                return data
            except Exception as e:
                logger.error(f"Error inserting into Supabase table {table}: {e}")
                raise DatabaseConnectionError(f"Insert failed on table {table}: {e}")
        self._reject_production_memory_write(table, "insert")
        return self.memory_db.insert(table, data)

    def upsert(self, table: str, data: Dict[str, Any], on_conflict: str) -> Dict[str, Any]:
        """Upsert a row keyed on one or more conflict columns (comma-separated)."""
        if self.is_connected and self.client:
            try:
                res = (
                    self.client.table(table)
                    .upsert(data, on_conflict=on_conflict)
                    .execute()
                )
                if res.data and len(res.data) > 0:
                    return res.data[0]
                return data
            except Exception as e:
                logger.error(f"Error upserting into Supabase table {table}: {e}")
                raise DatabaseConnectionError(f"Upsert failed on table {table}: {e}")
        self._reject_production_memory_write(table, "upsert")
        return self.memory_db.insert(table, data)

    def select(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Query rows from the specified table with equality filters."""
        if self.is_connected and self.client:
            try:
                query = self.client.table(table).select("*")
                if filters:
                    for k, v in filters.items():
                        query = query.eq(k, v)
                res = query.execute()
                return res.data or []
            except Exception as e:
                logger.error(f"Error selecting from Supabase table {table}: {e}")
                raise DatabaseConnectionError(f"Query failed on table {table}: {e}")
        return self.memory_db.select(table, filters)

    def update(self, table: str, record_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a row in the specified table by ID."""
        if self.is_connected and self.client:
            try:
                res = self.client.table(table).update(updates).eq("id", record_id).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0]
                return None
            except Exception as e:
                logger.error(f"Error updating Supabase table {table}: {e}")
                raise DatabaseConnectionError(f"Update failed on table {table}: {e}")
        self._reject_production_memory_write(table, "update")
        return self.memory_db.update(table, record_id, updates)

    def delete(self, table: str, record_id: str) -> bool:
        """Delete a row from the specified table by ID."""
        if self.is_connected and self.client:
            try:
                self.client.table(table).delete().eq("id", record_id).execute()
                return True
            except Exception as e:
                logger.error(f"Error deleting from Supabase table {table}: {e}")
        self._reject_production_memory_write(table, "delete")
        return self.memory_db.delete(table, record_id)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration setting by key from Supabase app_settings table."""
        if self.is_connected and self.client:
            try:
                res = self.client.table("app_settings").select("value").eq("key", key).execute()
                if res.data and len(res.data) > 0:
                    return res.data[0].get("value", default)
            except Exception as e:
                logger.warning(f"Error fetching setting '{key}' from Supabase: {e}")
        rows = self.memory_db.select("app_settings", {"key": key})
        if rows:
            return rows[0].get("value", default)
        return default

    def set_setting(self, key: str, value: Any) -> bool:
        """Saves or updates a setting into Supabase app_settings table."""
        now = datetime.now(timezone.utc).isoformat()
        if self.is_connected and self.client:
            try:
                self.client.table("app_settings").upsert({
                    "key": key,
                    "value": value,
                    "updated_at": now
                }).execute()
                return True
            except Exception as e:
                logger.error(f"Error saving setting '{key}' to Supabase: {e}")
        existing = self.memory_db.select("app_settings", {"key": key})
        if existing:
            self.memory_db.update("app_settings", existing[0]["id"], {"value": value, "updated_at": now})
        else:
            self.memory_db.insert("app_settings", {"key": key, "value": value, "updated_at": now})
        return True


supabase_db = SupabaseManager()

