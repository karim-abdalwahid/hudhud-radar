"""
WS0.3 mechanical migration script — extracts route sections from main.py
into src/modules/<name>/routes.py with APIRouter, preserving handler code
VERBATIM. Run once from project root:  python scripts/_ws03_migrate.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "src" / "main.py"
text = MAIN.read_text(encoding="utf-8")
lines = text.split("\n")

# ------------------------------------------------------------------
# Section definitions: (module_name, start_marker_line_prefix, end_marker_line_prefix)
# Boundaries are the section comment banners identified by inspection.
# ------------------------------------------------------------------
def find_line(pred, start=0):
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    return -1

def banner_line(text_fragment):
    return lambda l: text_fragment in l

# line indexes (0-based) of section start banners
marks = {
    "health_banner": find_line(lambda l: "# 1. System Health & Info" in l),
    "webhooks_banner": find_line(lambda l: "# 2. Meta Webhooks" in l),
    "leads_banner": find_line(lambda l: "# 3. Leads and Conversations APIs" in l),
    "identity_banner": find_line(lambda l: "# 4. Identity Resolution Manual Review Queue" in l),
    "analytics_banner": find_line(lambda l: "# 5. Analytics & Performance Reports" in l),
    "meta_banner": find_line(lambda l: "# 5.1 Meta Platform & Social Connection Management" in l),
    "content_banner": find_line(lambda l: "# 6. Content Studio (AI Generation, Publishing & Scheduling)" in l),
    "cron_banner": find_line(lambda l: "# Cron Endpoints (Vercel Cron / external cron-job.org)" in l),
    "ai_banner": find_line(lambda l: "# AI Providers & Models (Phase 8" in l),
    "debug_note": find_line(lambda l: "# Extended Meta APIs: Threads & Marketing" in l),
    "knowledge_banner": find_line(lambda l: "# 6.5 Knowledge Base, Meta Scraping & RAG Management" in l),
    "pages_banner": find_line(lambda l: "# 7. Dedicated Multi-Page SaaS Web Application Routes" in l),
    "automations_banner": find_line(lambda l: "# 10.5 Visual Automations & Workflows API Endpoints" in l),
    "inbox_banner": find_line(lambda l: "# 11. SendRad Onboarding & Live Inbox Endpoints" in l),
}
for k, v in marks.items():
    assert v >= 0, f"marker not found: {k}"

# banner lines are the middle of a 3-line banner; the block starts at banner_top = i-1
def top(i):
    return i - 1

# Sections and their [start, end) line ranges (0-based, start inclusive, end exclusive)
sections = [
    ("health",     top(marks["health_banner"]),    top(marks["webhooks_banner"])),
    ("webhooks",   top(marks["webhooks_banner"]),  top(marks["leads_banner"])),
    ("leads",      top(marks["leads_banner"]),     top(marks["identity_banner"])),
    ("identity",   top(marks["identity_banner"]),  top(marks["analytics_banner"])),
    ("analytics",  top(marks["analytics_banner"]), top(marks["meta_banner"])),
    ("meta",       top(marks["meta_banner"]),      top(marks["content_banner"])),
    ("content",    top(marks["content_banner"]),   top(marks["cron_banner"])),
    ("cron_admin", top(marks["cron_banner"]),      top(marks["ai_banner"])),
    ("ai",         top(marks["ai_banner"]),        top(marks["debug_note"] - 1)),  # skip trailing blank
    ("threads_marketing", top(marks["debug_note"]), top(marks["knowledge_banner"])),
    ("knowledge",  top(marks["knowledge_banner"]), top(marks["pages_banner"])),
    ("automations", top(marks["automations_banner"]), top(marks["inbox_banner"])),
]

HEADER = '''"""
{title} — migrated verbatim from main.py (WS0.3).

Owned by module '{name}'. Registered via src/modules/{name}/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from src.modules.context import *  # noqa: F401,F403 — shared kernel (services, settings, caches)
from src.modules.context import (  # explicit for readability
    settings, logger, supabase_db, httpx, safe_error, _safe_error,
    content_studio_service, knowledge_base, webhook_handler,
    automations_service, agent_orchestrator, lead_service,
    identity_review_queue, statistics_engine, report_generator,
    meta_feed_sync, meta_token_manager, meta_insights_sync,
    threads_publisher, marketing_leads_sync, threads_oauth_manager,
    ai_provider_manager, content_scheduler, _verify_cron_secret,
    _meta_status_cache, META_STATUS_CACHE_TTL, _llm_status_probe,
    collect_alerts, TEMPLATES_DIR,
)

router = APIRouter()

'''

INIT = '''"""
{title} module — self-contained vertical slice (modular architecture WS0.3).
"""
from src.core.modules import module_registry
from src.modules.{name}.routes import router


def register(app) -> None:
    app.include_router(router)


module_registry.register_module(
    name="{name}",
    description="{title}",
    register_router=register,
)
'''

created = []
spans = []
for name, s, e in sections:
    block = "\n".join(lines[s:e]).rstrip() + "\n"
    # @app.* -> @router.*
    block = block.replace("@app.", "@router.")
    mod_dir = ROOT / "src" / "modules" / name
    (mod_dir / "routes.py").parent.mkdir(parents=True, exist_ok=True)
    title = {
        "health": "System Health & Info",
        "webhooks": "Meta Webhooks (Verification & Intake)",
        "leads": "Leads & Conversations API",
        "identity": "Identity Resolution Review Queue",
        "analytics": "Analytics & Performance Reports",
        "meta": "Meta Platform & Social Connection Management",
        "content": "Content Studio (AI Generation, Publishing & Scheduling)",
        "cron_admin": "Cron Endpoints + Admin Alerts + Debug Diagnostics",
        "ai": "AI Providers & Models (Phase 8)",
        "threads_marketing": "Threads & Marketing Extended APIs",
        "knowledge": "Knowledge Base, Meta Scraping & RAG Management",
        "automations": "Visual Automations & Workflows API",
    }[name]
    (mod_dir / "routes.py").write_text(HEADER.format(name=name, title=title) + block, encoding="utf-8")
    (mod_dir / "__init__.py").write_text(INIT.format(name=name, title=title), encoding="utf-8")
    created.append(name)
    spans.append((s, e))

# Remove migrated sections from main.py (from bottom up to keep indexes valid)
new_lines = lines[:]
for s, e in sorted(spans, key=lambda x: -x[0]):
    del new_lines[s:e]
MAIN.write_text("\n".join(new_lines), encoding="utf-8")

print("Migrated modules:", ", ".join(created))
print(f"main.py lines: {len(lines)} -> {len(new_lines)}")
