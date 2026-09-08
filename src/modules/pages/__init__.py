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
from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.core.modules import module_registry, NavEntry, render_sidebar_nav


def render_module_page(html: str, request: "Request") -> HTMLResponse:
    """Serves a module-provided full HTML document with the registry sidebar
    injected (shared chrome) — used by module-owned pages like /users."""
    import re as _re
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    token = request.cookies.get(SESSION_COOKIE_NAME) if request else None
    session = verify_session_token(token) if token else None
    is_admin = bool(session and session.get("role") == "admin")
    html = html.replace(
        "<head>",
        '<head>\n    <script>window.HUDHUD_BASE_URL = "' + settings.APP_BASE_URL.rstrip("/") + '";</script>',
        1,
    )
    nav_match = _re.search(r'<nav class="sidebar-nav">.*?</nav>', html, _re.DOTALL)
    if nav_match:
        rendered = render_sidebar_nav(request.url.path, is_admin)
        html = html[:nav_match.start()] + rendered + html[nav_match.end():]
    return HTMLResponse(content=html)


def _render_page_template(filename: str, request: Optional[Request] = None,
                          force_ltr_default: bool = False) -> HTMLResponse:
    """Reads and serves dedicated SaaS page template with language-aware initial tags.
    WS0.4: sidebar nav is RENDERED SERVER-SIDE from the module registry —
    the <nav class="sidebar-nav">…</nav> block in templates is legacy-only
    and gets replaced when present (zero drift between pages).
    force_ltr_default=True serves the raw EN/LTR head (auth.html manages its
    own RTL flip client-side via localStorage; server default is English — WS-D)."""
    target = TEMPLATES_DIR / filename
    if target.exists():
        content = target.read_text(encoding="utf-8")
        path = request.url.path if request else "/"
        if not force_ltr_default:
            lang = "en"
            if request:
                lang = request.query_params.get("lang") or request.cookies.get("hudhud_lang") or "en"
            if lang == "ar":
                content = content.replace('<html lang="en" dir="ltr">', '<html lang="ar" dir="rtl">')
            else:
                content = content.replace('<html lang="ar" dir="rtl">', '<html lang="en" dir="ltr">')

        # Canonical origin injection: templates never hardcode the domain.
        content = content.replace(
            "<head>",
            f"<head>\n    <script>window.HUDHUD_BASE_URL = \"{settings.APP_BASE_URL.rstrip('/')}\";</script>",
            1,
        )

        # Brand identity links (WS0.5): favicon + manifest — injected once,
        # applies to every page without per-template edits.
        content = content.replace(
            "<head>",
            "<head>\n"
            "    <link rel=\"icon\" href=\"/static/favicon.ico\" sizes=\"any\">\n"
            "    <link rel=\"icon\" type=\"image/png\" sizes=\"32x32\" href=\"/static/favicon-32.png\">\n"
            "    <link rel=\"icon\" type=\"image/png\" sizes=\"16x16\" href=\"/static/favicon-16.png\">\n"
            "    <link rel=\"apple-touch-icon\" href=\"/static/apple-touch-icon.png\">\n"
            "    <link rel=\"manifest\" href=\"/static/manifest.json\">\n"
            "    <meta name=\"theme-color\" content=\"#0f172a\">",
            1,
        )

        # Registry-driven sidebar (single source of truth for navigation)
        is_admin = False
        if request:
            from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
            token = request.cookies.get(SESSION_COOKIE_NAME)
            session = verify_session_token(token) if token else None
            is_admin = bool(session and session.get("role") == "admin")

        import re as _re
        nav_match = _re.search(r'<nav class="sidebar-nav">.*?</nav>', content, _re.DOTALL)
        if nav_match:
            rendered = render_sidebar_nav(path, is_admin)
            content = content[:nav_match.start()] + rendered + content[nav_match.end():]

        return HTMLResponse(content=content)
    return HTMLResponse(content=f"<h1>Page template '{filename}' not found</h1>", status_code=404)


def register(app: FastAPI) -> None:
    # WS-E: lightweight internal traffic log for dashboard pages only
    # (no tracking cookies, no third-party scripts — disclosed in Privacy §9)
    @app.middleware("http")
    async def _traffic_log_middleware(request: Request, call_next):
        path = request.url.path
        is_dashboard_page = not path.startswith(("/api/", "/static", "/webhooks")) \
            and "." not in path.rsplit("/", 1)[-1] \
            and path not in ("/terms", "/privacy", "/data-deletion", "/health")
        response = await call_next(request)
        if is_dashboard_page and response.status_code < 400:
            try:
                from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
                token = request.cookies.get(SESSION_COOKIE_NAME)
                session = verify_session_token(token) if token else None
                supabase_db.insert("site_traffic", {
                    "path": path,
                    "user_id": session.get("sub") if session else None,
                    "is_admin": bool(session and session.get("role") == "admin"),
                })
            except Exception as e:
                logger.debug(f"traffic log skipped: {e}")
        return response

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def page_landing(request: Request):
        """SendRad-style World-Class Marketing & Feature Landing Page."""
        return _render_page_template("landing.html", request)

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/register", response_class=HTMLResponse, include_in_schema=False)
    async def page_auth(request: Request):
        """SendRad-style login/register page (migrated from auth_module to the
        unified template pipeline: HUDHUD_BASE_URL injection + server-side
        lang/dir defaults, WS-C+D)."""
        return _render_page_template("auth.html", request, force_ltr_default=True)

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
    nav=[
        NavEntry(href="/inbox", label_key="nav.inbox", icon="💬",
                 section="nav.conversations", order=1),
        NavEntry(href="/onboarding", label_key="nav.onboarding", icon="🚀",
                 section="nav.conversations", order=2),
        NavEntry(href="/dashboard", label_key="nav.overview", icon="📊",
                 section="nav.workspaces", order=1),
        NavEntry(href="/leads", label_key="nav.leads", icon="👥",
                 section="nav.workspaces", order=2),
        NavEntry(href="/studio", label_key="nav.studio", icon="✍️",
                 section="nav.workspaces", order=3),
        NavEntry(href="/automations", label_key="nav.automations", icon="⚡",
                 section="nav.workspaces", order=4),
        NavEntry(href="/knowledge", label_key="nav.knowledge", icon="🧠",
                 section="nav.workspaces", order=5),
        NavEntry(href="/identity", label_key="nav.identity", icon="🔍",
                 section="nav.workspaces", order=6, admin_only=True),
        NavEntry(href="/analytics", label_key="nav.analytics", icon="📈",
                 section="nav.analytics_system", order=1, admin_only=True),
        NavEntry(href="/settings", label_key="nav.settings", icon="⚙️",
                 section="nav.analytics_system", order=2, admin_only=True),
    ],
)
