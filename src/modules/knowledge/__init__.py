"""
Knowledge Base, Meta Scraping & RAG Management module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.knowledge.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="knowledge",
    description="Knowledge Base, Meta Scraping & RAG Management",
    register_router=register,
)
