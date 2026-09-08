"""
Content Studio (AI Generation, Publishing & Scheduling) module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.content.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="content",
    description="Content Studio (AI Generation, Publishing & Scheduling)",
    register_router=register,
)
