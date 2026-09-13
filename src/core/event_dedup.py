"""
Webhook Event Deduplication (Idempotency Guard).

Meta retries webhook deliveries when it doesn't receive an instant 200, and
at-least-once delivery can duplicate events. Without dedup, the agent would
send duplicate replies/DMs — a spam risk that can get accounts restricted.

Primary store: Supabase `processed_events` (unique event_key).
Fallback: in-process LRU set (local dev / serverless cold instances).
"""
from collections import OrderedDict
from typing import Optional

from src.core.logger import logger

MEMORY_MAX_KEYS = 5000


class EventDeduplicator:
    """Check-and-claim idempotency for webhook events.

    Includes a circuit breaker: after the first DB failure (e.g. missing table),
    it stops contacting the DB and operates purely in-memory to avoid latency
    from repeated failing round-trips.
    """

    def __init__(self):
        self._memory_seen: OrderedDict = OrderedDict()
        self._db_disabled: bool = False

    def _remember_memory(self, event_key: str):
        self._memory_seen[event_key] = True
        while len(self._memory_seen) > MEMORY_MAX_KEYS:
            self._memory_seen.popitem(last=False)

    def _db_ready(self) -> bool:
        if self._db_disabled:
            return False
        try:
            from src.core.supabase_client import supabase_db
            return bool(supabase_db.is_connected)
        except Exception:
            self._db_disabled = True
            return False

    def already_processed(self, event_key: str) -> bool:
        """Returns True if this exact event was already processed."""
        if not event_key:
            return False
        if event_key in self._memory_seen:
            return True
        if self._db_ready():
            try:
                from src.core.supabase_client import supabase_db
                rows = supabase_db.select("processed_events", {"event_key": event_key}) or []
                if rows:
                    self._remember_memory(event_key)
                    return True
            except Exception as e:
                logger.warning(f"Dedup DB check failed — disabling DB dedup (memory-only): {e}")
                self._db_disabled = True
        return False

    def mark_processed(self, event_key: str, event_type: str = "message") -> bool:
        """Records an event as processed. Returns True if newly recorded."""
        if not event_key:
            return False
        self._remember_memory(event_key)
        if self._db_ready():
            try:
                from src.core.supabase_client import supabase_db
                supabase_db.insert(
                    "processed_events",
                    {"event_key": event_key, "event_type": event_type},
                )
                return True
            except Exception as e:
                msg = str(e).lower()
                if "duplicate" in msg or "unique" in msg or "409" in msg:
                    # another worker inserted it first = already processed.
                    return False
                logger.warning(f"Dedup DB mark failed — disabling DB dedup (memory-only): {e}")
                self._db_disabled = True
        return False

    def claim(self, event_key: str, event_type: str = "message") -> bool:
        """Atomically claims an event: True if this caller should process it."""
        if not event_key or self.already_processed(event_key):
            return False
        self.mark_processed(event_key, event_type)
        return True


event_deduplicator = EventDeduplicator()
