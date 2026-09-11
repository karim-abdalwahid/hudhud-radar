# 🔍 Static Audit Report — 2026-09-11

## WS-A: Deployment Drift (local vs hudhd.com)

| Asset | Local hash | Production hash | Status |
|---|---|---|---|
| saas.js | `c754426f61f2` | `ed37987c07c7` | **DRIFT** |
| saas.css | `e011a0e846b6` | `f1cd59a2285f` | **DRIFT** |
| i18n.js | `9ab98d9c8360` | `d434a0ee1efd` | **DRIFT** |

## WS-B: CSS Classes & Variables

### Classes used but NEVER defined in any CSS (18)

- `'active'`
- `'badge-fb'}`
- `'badge-ig'`
- `'badge-muted'}`
- `'badge-neutral'}`
- `'badge-pending'}`
- `'badge-success'`
- `'instagram'`
- `'published'`
- `card-thumb-wrap`
- `cc-item${i===0?`
- `connection-line`
- `d.filename`
- `hero-content`
- `hero-mockup-wrap`
- `metrics-pill-group`
- `set-tab`
- `thumb-fallback`

### CSS variables USED but never DEFINED (0)


## WS-E2: JS-generated HTML with hardcoded user-facing Arabic strings (no data-i18n)

### Suspicious hardcoded Arabic in JS templates (0)


## WS-K (static part): scheduler double-run + env collisions

- main.py lifespan starts in-process scheduler: `True`
- Vercel cron configured (vercel.json): `True`
- cron_admin has its own scheduler tick: `True`
- .env duplicate keys: `none`
