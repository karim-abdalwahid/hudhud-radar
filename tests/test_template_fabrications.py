"""
Site-wide dashboard template zero-fabrication sweep (Entry 027).
The authenticated dashboard pages must NEVER ship hardcoded demo personas,
invented KPI numbers, or fake response-time stats. Marketing demos on PUBLIC
pages (landing/auth) are intentional product showcases and are excluded.
"""
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "templates"

# Dashboard pages (authenticated) — every one must be free of demo content
DASHBOARD_PAGES = [
    "overview.html", "leads.html", "studio.html", "knowledge.html",
    "identity.html", "analytics.html", "onboarding.html", "inbox.html",
    "settings.html", "automations.html",
]

# Known demo personas / fabricated values that must never return
FORBIDDEN_SNIPPETS = [
    "Alex Johnson", "alex_agency", "Sarah M.", "Hot Lead (94% Intent)",
    "annual agency growth tier", "mid.simulated", "HUDHUD20",
    "hudhud-meeting", "hudhud.ai/offer", "hudhud.ai/booking",
    # fabricated claim descriptions (state asserted without measurement)
    "100% grounded", "Zero 24h window violations recorded",
    "No rate limiting detected",
]


def test_no_demo_personas_in_any_dashboard_page():
    for page in DASHBOARD_PAGES:
        src = (TEMPLATES / page).read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            assert snippet not in src, f"Fabricated content '{snippet}' found in {page}"


def test_no_hardcoded_percent_kpis_in_dashboard_pages():
    """Static percentage KPIs in dashboard HTML are fabricated until proven
    by real data — they must start as 0/— and be filled from the API.
    (UI controls like the canvas zoom indicator are excluded.)"""
    import re
    for page in DASHBOARD_PAGES:
        src = (TEMPLATES / page).read_text(encoding="utf-8")
        for m in re.finditer(r'class="metric-val[^"]*"[^>]*id="([^"]+)"[^>]*>(\d{1,3}%)', src):
            val = m.group(2)
            assert val == "0%", f"{page}: static KPI '{val}' in #{m.group(1)} must not be hardcoded"


def test_automations_kpis_start_at_zero():
    src = (TEMPLATES / "automations.html").read_text(encoding="utf-8")
    for kpi_id in ("kpi-total-wf", "kpi-active-wf", "kpi-total-exec"):
        import re
        m = re.search(rf'id="{kpi_id}"[^>]*>([^<]+)<', src)
        assert m, f"{kpi_id} missing in automations.html"
        assert m.group(1).strip() == "0", f"{kpi_id} must default to 0, got {m.group(1)!r}"


def test_analytics_compliance_and_agent_rate_start_honest():
    src = (TEMPLATES / "analytics.html").read_text(encoding="utf-8")
    for kpi_id in ("stat-compliance", "stat-agent-rate"):
        import re
        m = re.search(rf'id="{kpi_id}"[^>]*>([^<]+)<', src)
        assert m, f"{kpi_id} missing in analytics.html"
        assert m.group(1).strip() in ("—", "-", ""), f"{kpi_id} must start empty/honest, got {m.group(1)!r}"


def test_onboarding_trial_button_starts_verified_checkout_not_a_success_page():
    src = (TEMPLATES / "onboarding.html").read_text(encoding="utf-8")
    assert "billing/success?trial=1" not in src
    assert "async function startTrial()" in src
    assert "fetch('/api/billing/trial', { method: 'POST' })" in src


def test_identity_thresholds_rendered_from_backend_not_hardcoded():
    src = (TEMPLATES / "identity.html").read_text(encoding="utf-8")
    assert "≥ 70% Confidence" not in src  # actual prod threshold is 60% — drift caught
    assert 'id="stat-threshold-val"' in src  # filled from /api/identity/queue policy


def test_settings_dev_console_has_coupon_management_panel():
    """Dev console must expose the discount coupon manager (2026-09-26) —
    wired to the admin-only /api/admin/billing/coupons endpoints."""
    src = (TEMPLATES / "settings.html").read_text(encoding="utf-8")
    assert "cp-code" in src              # code input
    assert "cp-polar-id" in src          # Polar discount id input (H1 wiring)
    assert "cp-kind" in src              # kind select
    assert "loadCouponsTable(" in src    # table loader wired
    assert "saveCoupon(" in src          # create handler
    assert "deleteCoupon(" in src        # delete handler
    assert "fetch('/api/admin/billing/coupons'" in src


def test_coupon_table_escapes_rows_and_never_uses_inline_onclick():
    """Coupon codes/ids are admin-managed but must never be interpolated raw
    into innerHTML or inline handlers (XSS hardening, 2026-09-26)."""
    src = (TEMPLATES / "settings.html").read_text(encoding="utf-8")
    assert "function _esc(v)" in src                       # HTML-escape helper exists
    assert 'data-coupon-delete' in src                     # handler wired via data-attributes
    assert "data-coupon-id=\"${_esc(c.id)}\"" in src       # id escaped into attribute
    assert "data-coupon-code=\"${_esc(c.code)}\"" in src   # code escaped into attribute
    assert 'onclick="deleteCoupon(' not in src             # no raw inline handler remains
