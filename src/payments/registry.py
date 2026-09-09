"""Payment gateways registry — add a gateway = implement contract + 1 line."""
from typing import Optional

from src.core.supabase_client import supabase_db
from src.payments.base import PaymentProvider
from src.payments.polar import PolarGateway

GATEWAYS = {
    "polar": PolarGateway(),
    # "paymob": PaymobGateway(),   ← future (Phase 9.x)
}


def get_gateway(name: str) -> Optional[PaymentProvider]:
    return GATEWAYS.get(name)


def active_gateway() -> Optional[PaymentProvider]:
    """The gateway selected in admin settings (default polar)."""
    try:
        name = supabase_db.get_setting("payment_gateway") or "polar"
    except Exception:
        name = "polar"
    return GATEWAYS.get(name)
