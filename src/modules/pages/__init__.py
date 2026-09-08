"""
Dashboard pages module — the dedicated multi-page SaaS web application.

Serves every dashboard page template with:
  - language-aware initial tags (?lang= or hudhud_lang cookie)
  - canonical origin injection (window.HUDHUD_BASE_URL) — templates never
    hardcode the domain (single source of truth: settings.APP_BASE_URL).

Migrated verbatim from main.py (WS0.3). Page access stays enforced by the
central middleware + ADMIN_PAGE_PATHS (settings/identity/analytics).
"""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.config import settings
from src.core.http_utils import TEMPLATES_DIR
from src.core.modules import module_registry


def _render_page_template(filename: str, request: Optional[Request] = None) -> HTMLResponse:
    """Reads and serves dedicated SaaS page template with language-aware initial tags."""
    target = TEMPLATES_DIR / filename
    if target.exists():
        content = target.read_text(encoding="utf-8")
        lang = "en"
        if request:
            lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
        if lang == "ar":
            content = content.replace('<html lang="en" dir="ltr">', '<html lang="ar" dir="rtl">')
        else:
            content = content.replace('<html lang="ar" dir="rtl">', '<html lang="en" dir="ltr">')
        # Canonical origin injection: templates never hardcode the domain —
        # window.HUDHUD_BASE_URL is the single source of truth for absolute URLs.
        content = content.replace(
            "<head>",
            f"<head>\n    <script>window.HUDHUD_BASE_URL = \"{settings.APP_BASE_URL.rstrip('/')}\";</script>",
            1,
        )
        return HTMLResponse(content=content)
    return HTMLResponse(content=f"<h1>Page template '{filename}' not found</h1>", status_code=404)


def register(app: FastAPI) -> None:
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def page_landing(request: Request):
        """SendRad-style World-Class Marketing & Feature Landing Page."""
        return _render_page_template("landing.html", request)

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def page_overview(request: Request):
        """Executive Overview Dashboard."""
        return _render_page_template("overview.html", request)

    @app.get("/leads", response_class=HTMLResponse, include_in_schema=False)
    async def page_leads(request: Request):
        """Leads CRM & Contact Management Workspace."""
        return _render_page_template("leads.html", request)

    @app.get("/studio", response_class=HTMLResponse, include_in_schema=False)
    async def page_studio(request: Request):
        """AI Content Studio, Post Composer & Scheduler Workspace."""
        return _render_page_template("studio.html", request)

    @app.get("/knowledge", response_class=HTMLResponse, include_in_schema=False)
    async def page_knowledge(request: Request):
        """Knowledge Base, Markdown Editor & LEANN Semantic Search Studio."""
        return _render_page_template("knowledge.html", request)

    @app.get("/identity", response_class=HTMLResponse, include_in_schema=False)
    async def page_identity(request: Request):
        """Identity Verification & Human-in-the-Loop Review Queue."""
        return _render_page_template("identity.html", request)

    @app.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
    async def page_analytics(request: Request):
        """Analytics, Root Cause Analysis (RCA) & Executive Reports."""
        return _render_page_template("analytics.html", request)

    @app.get("/onboarding", response_class=HTMLResponse, include_in_schema=False)
    async def page_onboarding(request: Request):
        """SendRad-style 3-Step Setup Wizard for Business Knowledge, Agent Persona & Channels."""
        return _render_page_template("onboarding.html", request)

    @app.get("/inbox", response_class=HTMLResponse, include_in_schema=False)
    async def page_inbox(request: Request):
        """Unified Live Messaging Inbox with Human Takeover & Lead Qualification."""
        return _render_page_template("inbox.html", request)

    @app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
    async def page_settings(request: Request):
        """Meta Platforms Connection, Webhooks & System Settings."""
        return _render_page_template("settings.html", request)

    @app.get("/automations", response_class=HTMLResponse, include_in_schema=False)
    async def page_automations(request: Request):
        """Visual Automation & Workflows Canvas Builder Workspace."""
        return _render_page_template("automations.html", request)


module_registry.register_module(
    name="pages",
    description="Dashboard HTML pages (landing, overview, leads, studio, knowledge, identity, analytics, onboarding, inbox, settings, automations)",
    register_router=register,
)
