"""
Payment provider contract — how a billing gateway plugs into Hudhud.

To add a NEW gateway (Paymob, Fawry, Stripe...):
  1. Create src/payments/<name>.py implementing PaymentProvider.
  2. Register it in src/payments/registry.py.
  3. Set ACTIVE gateway in admin settings (site_settings['payment_gateway']).
Zero changes elsewhere — checkout/webhooks route through the registry.

Owner safety requirements baked into the contract:
  - verify_webhook MUST be fail-closed (invalid/missing signature → reject)
  - map_event returns normalized (kind, user_ref, platforms, sub_ids)
  - duplicate events are neutralized by payment_events dedup (services layer)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PaymentProvider(ABC):
    name: str = ""  # registry key: polar | paymob | ...

    @abstractmethod
    def create_checkout(self, user: Dict[str, Any], quote: Dict[str, Any],
                        return_url: str) -> Dict[str, Any]:
        """Creates a checkout for the quoted platforms. Returns
        {checkout_url, provider_ref}. Must be sandbox-safe."""

    @abstractmethod
    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        """Signature check. FAIL-CLOSED: return False on any doubt."""

    @abstractmethod
    def parse_event(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes a verified webhook into:
        {event_id, event_type, kind, user_email, platforms, subscription_ref}
        kind ∈ {subscription_activated, subscription_canceled, order_paid, other}"""

    @abstractmethod
    def start_trial(self, user: Dict[str, Any], return_url: str) -> Dict[str, Any]:
        """Starts a trial WITH card capture (owner rule: card required even
        for the 3-day trial). Returns {checkout_url, provider_ref}."""
