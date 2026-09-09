"""Replace platform emoji placeholders with official brand SVGs across templates.

Strategy per file: targeted, surgical replacements (never blind) — the emoji
column of known platform contexts becomes the inline brand mark via a small
JS-friendly helper or direct SVG injection.

Also injects the shared helper into every dashboard page: window.platformIcon(p)
so dynamic JS renders (inbox threads, badges) use brand marks too.
"""
from pathlib import Path

TPL = Path("src/templates")

# 1) Shared helper injection (into static JS, loaded on all dashboard pages)
HELPER_JS = """

// ---- Official platform brand icons (S-B) — from platform registry ----
window.PLATFORM_ICON_SVG = {
    facebook: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.025 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971H15.83c-1.491 0-1.956.93-1.956 1.886v2.264h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>',
    instagram: '<svg viewBox="0 0 24 24" width="100%" height="100%"><defs><radialGradient id="igg__ID__" cx="30%" cy="107%" r="150%"><stop offset="0%" stop-color="#fdf497"/><stop offset="5%" stop-color="#fdf497"/><stop offset="45%" stop-color="#fd5949"/><stop offset="60%" stop-color="#d6249f"/><stop offset="90%" stop-color="#285AEB"/></radialGradient></defs><rect x="1.5" y="1.5" width="21" height="21" rx="5.5" fill="url(#igg__ID__)"/><circle cx="12" cy="12" r="4.7" fill="none" stroke="#fff" stroke-width="1.9"/><circle cx="17.6" cy="6.4" r="1.35" fill="#fff"/></svg>',
    threads: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#000" d="M17.09 11.33c-.1-.05-.2-.1-.3-.14-.18-3.28-1.95-5.16-4.93-5.18h-.04c-1.78 0-3.26.76-4.17 2.14l1.63 1.12c.68-1.03 1.74-1.25 2.54-1.25h.03c.98.01 1.72.29 2.2.84.35.4.58.95.7 1.64-.87-.15-1.82-.19-2.83-.14-2.85.16-4.68 1.82-4.55 4.13.06 1.17.64 2.18 1.63 2.83.84.55 1.92.82 3.04.76 1.48-.08 2.64-.64 3.45-1.68.62-.78 1.01-1.8 1.18-3.07.71.43 1.24 1 1.53 1.68.5 1.15.53 3.05-1.02 4.6-1.35 1.35-2.98 1.94-5.44 1.96-2.72-.02-4.78-.89-6.11-2.59C3.86 17.4 3.2 15.1 3.18 12c.02-3.1.68-5.4 1.96-6.92 1.33-1.7 3.39-2.57 6.11-2.59 2.74.02 4.84.89 6.24 2.6.68.82 1.19 1.86 1.53 3.06l1.9-.51c-.42-1.53-1.06-2.85-1.96-3.93C17.27 1.63 14.75.54 11.26.51h-.01C7.77.54 5.19 1.63 3.5 3.75 1.98 5.65 1.19 8.36 1.17 11.99v.02c.02 3.63.81 6.34 2.33 8.24 1.69 2.12 4.27 3.21 7.75 3.24h.01c2.99-.02 5.09-.81 6.8-2.52 2.23-2.22 2.16-5 1.43-6.72-.53-1.25-1.54-2.26-2.9-2.92zm-4.9 5.02c-1.25.07-2.55-.49-2.61-1.71-.05-.9.64-1.91 2.7-2.03.24-.01.47-.02.7-.02.75 0 1.45.07 2.09.21-.24 2.94-1.62 3.48-2.88 3.55z"/></svg>',
    whatsapp: '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>',
};

window.platformIcon = function (platform, size = 20) {
    const key = (platform || '').toLowerCase();
    const raw = window.PLATFORM_ICON_SVG[key] ||
        '<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="11" fill="#64748b"/><circle cx="12" cy="12" r="4" fill="#fff"/></svg>';
    const svg = raw.replace(/__ID__/g, 'ig' + key + size + Math.floor(Math.random() * 99999));
    return '<span class="platform-brand-icon" style="display:inline-flex;width:' + size +
        'px;height:' + size + 'px;border-radius:6px;overflow:hidden;flex-shrink:0;vertical-align:middle;">' +
        svg + '</span>';
};
"""

saas_js = Path("src/templates/static/saas.js")
txt = saas_js.read_text(encoding="utf-8")
if "window.platformIcon" not in txt:
    saas_js.write_text(txt + HELPER_JS, encoding="utf-8")
    print("saas.js: helper injected")
else:
    print("saas.js: helper already present")


# 2) landing.html — integration icons → brand SVGs (static, unique gradient ids)
landing = TPL / "landing.html"
c = landing.read_text(encoding="utf-8")
IG = '<svg viewBox="0 0 24 24" width="100%" height="100%"><defs><radialGradient id="igL" cx="30%" cy="107%" r="150%"><stop offset="0%" stop-color="#fdf497"/><stop offset="5%" stop-color="#fdf497"/><stop offset="45%" stop-color="#fd5949"/><stop offset="60%" stop-color="#d6249f"/><stop offset="90%" stop-color="#285AEB"/></radialGradient></defs><rect x="1.5" y="1.5" width="21" height="21" rx="5.5" fill="url(#igL)"/><circle cx="12" cy="12" r="4.7" fill="none" stroke="#fff" stroke-width="1.9"/><circle cx="17.6" cy="6.4" r="1.35" fill="#fff"/></svg>'
FB = '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#1877F2" d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073C0 18.1 4.388 23.094 10.125 24v-8.437H7.078v-3.49h3.047v-2.66c0-3.025 1.792-4.697 4.533-4.697 1.313 0 2.686.236 2.686.236v2.971H15.83c-1.491 0-1.956.93-1.956 1.886v2.264h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.1 24 12.073z"/></svg>'
WA = '<svg viewBox="0 0 24 24" width="100%" height="100%"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>'

c = c.replace(
    '<div class="integration-icon" title="Instagram Direct">📸</div>',
    f'<div class="integration-icon" title="Instagram Direct">{IG}</div>')
c = c.replace(
    '<div class="integration-icon" title="Facebook Messenger">💬</div>',
    f'<div class="integration-icon" title="Facebook Messenger">{FB}</div>')
c = c.replace(
    '<div class="integration-icon" title="WhatsApp Cloud">📱</div>',
    f'<div class="integration-icon" title="WhatsApp Cloud">{WA}</div>')
landing.write_text(c, encoding="utf-8")
print("landing.html: integration icons → brand SVGs")

# 3) onboarding.html — platform circles
onb = TPL / "onboarding.html"
c = onb.read_text(encoding="utf-8")
c = c.replace('<div class="platform-icon-circle" style="color: #e1306c;">📸</div>',
              f'<div class="platform-icon-circle">{IG}</div>')
c = c.replace('<div class="platform-icon-circle" style="color: #0084ff;">💬</div>',
              f'<div class="platform-icon-circle">{FB}</div>')
onb.write_text(c, encoding="utf-8")
print("onboarding.html: platform circles → brand SVGs")

# 4) inbox.html — JS channel-dot: use platformIcon() helper
inbox = TPL / "inbox.html"
c = inbox.read_text(encoding="utf-8")
c = c.replace(
    "<span class=\"channel-dot ${c.channel}\">${c.channel === 'instagram' ? '📸' : c.channel === '",
    "<span class=\"channel-dot ${c.channel}\" style=\"display:inline-flex;overflow:hidden;border-radius:6px;\">${window.platformIcon(c.channel, 18)}</span><span style=\"display:none;\">${c.channel === 'instagram' ? '📸' : c.channel === '")
inbox.write_text(c, encoding="utf-8")
print("inbox.html: channel dots → brand icons")

print("DONE — platform emojis replaced with official brand marks")
