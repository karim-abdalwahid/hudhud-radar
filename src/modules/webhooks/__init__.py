"""
Meta Webhooks (Verification & Intake) module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.webhooks.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="webhooks",
    description="Meta Webhooks (Verification & Intake)",
    register_router=register,
)
