# HudhudRadar — دليل المشروع الكامل وخريطة المسارات (Project Structure & Path Map)

Autonomous 24/7 AI Social Sales Agent for **Instagram, Facebook Messenger & Threads**
FastAPI · Supabase (PostgreSQL + pgvector) · Vercel Serverless · Meta/Threads Graph APIs.

> **الغرض من هذا الملف**: المرجع الوحيد لتوجيه أي تعديل — كل ميزة أو خلل أو سؤال:
> اقرأ القسم المناسب، تجد المسار الدقيق + الدور + آلية العمل، بدل البحث في كل المشروع.
> صُمّم ليكون مقروءًا بشريًا **وأتمى** (AI-agent-readable).

---

## جدول المحتويات
1. [المعمارية وسير البيانات (المستوى الأعلى)](#1-المعمارية-وسير-البيانات)
2. [سير الرد الآلي الكامل خطوة بخطوة](#2-سير-الرد-الآلي-الكامل-خطوة-بخطوة)
3. [المجلدات الجذرية](#3-المجلدات-الجذرية)
4. [سجل الموديولات (`src/core/modules.py`)](#4-سجل-الموديولات--srccoremodulespy)
5. [صفحات الواجهة وقوالب HTML](#5-صفحات-الواجهة-وقوالب-html)
6. [خريطة الـ API التفصيلية (كل موديول)](#6-خريطة-الـ-api-التفصيلية)
7. [طبقة الخدمات (أين يقع المنطق التجاري)](#7-طبقة-الخدمات)
8. [قاعدة البيانات والهجرات](#8-قاعدة-البيانات-والهجرات)
9. [الإعدادات والبيئة (`src/config.py`)](#9-الإعدادات-والبيئة)
10. [الأمان والتحقق من المسارات](#10-الأمان-والتحقق-من-المسارات)
11. [الاختبارات](#11-الاختبارات)
12. [سكربتات الجذر وscripts](#12-سكربتات-الجذر-والسكربتات-المعتمدة)
13. [جدول Quick-start التحريري](#13-جدول-quick-start-التحريري)
14. [قواعد العمل الصارمة](#14-قواعد-العمل-الصارمة)
15. [أوامر سريعة](#15-أوامر-سريعة)
16. [فهرس الأرشيف الكامل (`scripts/archive/`)](#16-فهرس-الأرشيف-الكامل)

---

## 1) المعمارية وسير البيانات

```
Vercel (api/index.py)  →  src/main.py (FastAPI app + AuthMiddleware)
                              │
        ┌─────────────────────┼──────────────────────────────────────────┐
        ▼                     ▼                                        ▼
  src/modules/*          src/core/*  (الأساس)                    src/platforms/*
  25 موديول مستقل        auth · supabase · modules               facebook / instagram
  يكلّفه module_registry crypto · event_dedup · admin_alerts    threads (adapters)
  (routes + pages + nav) http_utils · logger · exceptions
        │
        ▼
  كل API/صفحة تعبر AuthMiddleware (default-deny)
        │
        ▼
  src/core/supabase_client.py  →  Supabase Cloud (25 migrations + pgvector)
        │
        ├── الرد الآلي: webhooks → src/agent/orchestrator.py → conversation_engine (Gemini/RAG)
        └── بيلينغ: src/payments/registry.py → polar.py (Polar.sh) ← webhooks مدفوعة
```

### 1.1 Boot sequence (ترتيب الإقلاع)
1. `api/index.py` — Vercel يفحص `app` مباشرة في المستوى الأعلى؛ يستورد `src.main:app` داخل try
   (فشل الإقلاع → يعرض traceback في `/health` بدل 500 أعمى).
2. `src/config.py` — `settings = Settings()` ثم `settings.validate_security()` (output: تحذيرات
   فقط في production وليس raise — hotspot معروف، انظر §14).
3. `src/core/supabase_client.py` — `supabase_db`؛ في وضع production مع اتصال يرمي
   `DatabaseConnectionError` إن كان المفتاح غير service-role؛ وفي local/test يقع على
   `InMemoryDatabase` (`is_connected=False`).
4. `src/main.py` — يُنشئ `app = FastAPI(...)`، يركّب:
   - `uuid_segment_guard` middleware (تصفية معرّفات غير UUID → 404 بدل 500).
   - `auth_middleware` (default-deny؛ يفحص session trust ثم admin).
   - `/static` (مجلد `src/templates/static`).
   - ثم **26 استدعاء register** (كل موديول): الاستدعاءات أدناه في `src/main.py:228-269`.
5. `lifespan` عند أول إقلاع: `knowledge_base.reload()` ثم إن لم يكن Vercel → يبدأ
   `content_scheduler.start_loop(30s)` كخلفية. في Vercel يعتمد على الـ crons فقط.

### 1.2 تدفق البيانات على مستوى عالٍ
```
webhook (Meta/Threads) → src/modules/webhooks/routes.py → HMAC verify
   → parse_messaging_events / parse_comment_events → event_deduplicator.claim()
   → background_tasks → src/agent/orchestrator.py
   → owner_for_account() (connections) → إن لم يوجد owner → تجاهل
   → get_active_token_for_account() → إن لم يوجد token → تجاهل
   → profile enrichment → identity resolver (lead record/new/queue)
   → مخزن الرسالة الواردة دائمًا (مهما حدث)
   → فحوصات: human_takeover / ai_paused / credit gate (fail-closed)
   → conversation_engine.generate_response() (Gemini + RAG)
   → استخدام رصيد إن استُخدم AI فعلًا
   → إرسال (FB Page Token / IG send token) ← rate limiter + 24h window
   → مخزن الرسالة الصادرة + reply_sent/reply_error
```

---

## 2) سير الرد الآلي الكامل خطوة بخطوة

المصدر: `src/agent/orchestrator.py` (كل الخطوات هنا داخل `process_incoming_message_event`).

| # | الخطوة | الملف/الدالة | ملاحظة حرجة |
|---|---|---|---|
| 0 | إدخال webhook | `src/modules/webhooks/routes.py` | HMAC verify (Meta: `META_APP_SECRET`/`IG_APP_SECRET`; Threads: `THREADS_APP_SECRET`) — fail-closed بدون secret |
| 0ب | إزالة التكرارات | `src/core/event_dedup.py` `.claim()` | `processed_events` (DB) + LRU في الذاكرة؛ بدونها رسائل مكررة |
| 1 | مالك الحساب المستقبِل | `src/modules/connections/service.py` `owner_for_account()` | **refuses if no unique owner** — الاكتشاف التعسفي ممنوع (حماية tenant) |
| 1ب | جلب التوكن الفعّال | `connection_service.get_active_token_for_account()` | بدون توكن → تجاهل نهائي |
| 2 | إثراء الملف الشخصي | `ProfileDataExtractor` + `meta_client.get_profile()` | Facebook/Instagram Profile API (provenance كاملة) |
| 3 | مطابقة الهوية | `src/identity/resolver.py` `resolve_and_save_lead()` | Deterministic ID → cross-link score → قائمة مراجعة بشرية |
| 4 | تخزين الرسالة الواردة | `lead_svc.add_message()` | **يحدث دائمًا** قبل أي early-return (الـ inbox يبقى حيًا) |
| 4a | Human Takeover؟ | فحص `lead_record.human_takeover` | إن نعم → تخزين فقط، لا رد |
| 4b | AI Pause (عالمي/مستخدم)؟ | `src/ai/pause.py` `is_ai_paused()` | إن نعم → تخزين فقط |
| 4c | رصيد كافٍ؟ | `src/modules/billing/usage.py` `has_credits()` | **fail-closed**: خطأ بحث = "لا رصيد"، لا "بلا حدود" أبدًا |
| 5 | استخراج وسيلة تواصل من النص | `conversation_engine.extract_contact_info()` | email/هاتف → تحديث الـ lead |
| 6 | توليد الرد | `conversation_engine.generate_response()` | أولوية: أداة اتصال (رد جاهز مجاني) → Gemini+RAG (مدفوع) → heuristic fallback (مجاني) |
| 6ب | احتساب الرصيد | `usage_service.record_usage(KIND_AI_REPLY)` | فقط إن `used_ai=True` (استدعاء Gemini فعلي) |
| 7 | الإرسال | `meta_client.send_facebook_message` / `send_instagram_message` | Instagram يستخدم **send token** (`get_send_token_for_instagram`) وليس توكن IG العادي |
| 8 | تخزين الصادرة | `lead_svc.add_message(AGENT)` | فقط بعد نجاح الإرسال الفعلي |
| 9 | النتيجة | يُرجع `reply_sent` / `reply_error` | فشل إرسال = `reply_sent: None` + `reply_error: السبب` (صدقًا، وليس ادعاءً كاذبًا) |

### 2.1 محرك المحادثة (`src/agent/conversation_engine.py`) — مسارات الرد
```
generate_response(lead, msg, history):
 1) إذا شارك العميل email/هاتف  → رد تهنئة ثابت + is_converted=True  (مجاني، `used_ai=False`)
 2) gemini متوفر وGEMINI_API_KEY مضبوطة → _call_gemini_api():
       - RAG: kb.search_relevant_chunks(msg, top_k=3, user_id) + sales tactics
       - system_prompt: لا تختلق، هُوية العميل فقط، Closing tactics
       - محادثة متعددة الأدوار: آخر 8 دورات حقيقية (model/user)
       - 3 محاولات على 5xx/شبكة مع backoff (1s,2s,3s), timeout 15s
 3) fallback نصي (مجاني): "ابدأ/start" و"سعر/price" و"خدمات/services" + ردود عربية من المكتبة
 → التذاكر الثلاثة كلها `used_ai=False`.
```

---

## 3) المجلدات الجذرية

| المسار | الدور |
|---|---|
| `api/index.py` | Vercel entry point (يستورد `src.main:app`) |
| `main.py` | تشغيل محلي سريع: `python main.py` (uvicorn reload) |
| `src/` | التطبيق كله (FastAPI) — انظر §4–§9 |
| `database/` | `schema.sql` (مرجع كامل) + `migrations/001…023` (التطبيق الفعلي) |
| `tests/` | مجموعة pytest (397+ اختبارًا؛ `conftest.py` يعزل كل البيئات) |
| `scripts/` | أدوات dev/أدمن المسجلة (§12) + `scripts/archive/` لسكربتات الجلسات السابقة (§16) |
| `docs/` | Specs + App Review Meta + Session logs + KNOWLEDGE_BASE markdown |
| `.github/workflows/tests.yml` | CI: `python -m pytest tests` |
| `vercel.json` | النشر + 3 crons: `scheduler-tick` 03:00 · `threads-token-refresh` 04:00 · `instagram-token-refresh` 05:00 |
| `requirements.txt` | FastAPI, uvicorn, httpx, supabase, pydantic(-settings), cryptography, python-dotenv |
| `python-dotenv` (ضمن requirements) | تحميل `.env` |

---

## 4) سجل الموديولات — `src/core/modules.py`

النظام الذي يجعل تغيير `/src/modules` من (إنشاء موديول) إلى (استهلاك في كل مكان):
- **Access levels**: `ACCESS_PUBLIC` (بلا جلسة) · `ACCESS_USER` (أي مستخدم) · `ACCESS_ADMIN`.
- **Dataclasses**: `Module` (name/description/register_router/pages/nav/public_*) ·
  `NavEntry` (href/label_key/icon/section/admin_only/order) · `PageSpec` (path/template/access).
- **مثيل وحيد**: `module_registry` — `register_module()` يسجّل، `mount_all()` يثبّت الـ routers،
  `public_exact_paths()`/`public_prefixes()`/`admin_page_paths()` تُشتق للـ auth middleware.
- **الـ sidebar**: `render_sidebar_nav()` (`modules.py:183`) + `initial_body_class()`
  (`modules.py:230`) — يُبنى من السجل نفسيًا، **لا nav مكتوب يدويًا في القوالب**.
- **إضافة ميزة جديدة** = إنشاء package موديول + `register_module()` في نهاية `__init__.py`
  + استيراده في `src/main.py:228-269`. لا تعدّل `src/core/auth.py` إلا لموديولات legacy.

### 4.1 الموديولات الـ 25 بتفاصيلها

| الموديول | package | `register_module` في | الدور |
|---|---|---|---|
| pages | `src/modules/pages/` | `pages/__init__.py:207` | كل صفحات dashboard + nav الرئيسي |
| auth_module | `src/modules/auth_module/` | `auth_module/__init__.py:326` | register/login/logout/google/me |
| inbox_onboarding | `src/modules/inbox_onboarding/` | `inbox_onboarding/__init__.py:354` | معالج Onboarding + Inbox live |
| webhooks | `src/modules/webhooks/` | `webhooks/__init__.py` | Meta/IG/Threads webhooks |
| health | `src/modules/health/` | `health/__init__.py` | `/health` |
| leads | `src/modules/leads/` | `leads/__init__.py` | Leads API |
| identity | `src/modules/identity/` | `identity/__init__.py` | Identity Review Queue API |
| analytics | `src/modules/analytics/` | `analytics/__init__.py` | Analytics/Reports API |
| meta | `src/modules/meta/` | `meta/__init__.py` | Meta status/posts/subscribe + tenant feed |
| content | `src/modules/content/` | `content/__init__.py` | Content Studio (generate/publish/schedule) |
| cron_admin | `src/modules/cron_admin/` | `cron_admin/__init__.py` | crons + alerts + diagnostics |
| ai | `src/modules/ai/` | `ai/__init__.py:12` | AI providers/models/pause/debug |
| threads_marketing | `src/modules/threads_marketing/` | `threads_marketing/__init__.py` | Threads posts/insights/oauth + marketing |
| knowledge | `src/modules/knowledge/` | `knowledge/__init__.py` | KB/RAG management (docs CRUD, sync-meta, search) |
| automations | `src/modules/automations/` | `automations/__init__.py` | Visual workflows API |
| notifications | `src/modules/notifications/` | `notifications/__init__.py` | Bell + admin broadcast + hooks |
| admin_console | `src/modules/admin_console/` | `admin_console/__init__.py` | Admin users/credits/plan/traffic/cron trigger |
| admin_users_page | `src/modules/admin_users_page/` | `admin_users_page/__init__.py:600` | صفحة `/users` في HTML مدمج |
| templates_manager | `src/modules/templates_manager/` | end `__init__.py` | قوالب الرسائل lifecycle + صفحة `/templates` |
| billing_pages | `src/modules/billing_pages/` | `billing_pages/__init__.py` | Checkout UI + success |
| billing | `src/modules/billing/` | `billing/__init__.py` | Billing/entitlements/payments webhook/quote |
| compliance | `src/modules/compliance/` | `compliance/__init__.py:15` | Meta data-deletion/deauth + Threads uninstall |
| legal | `src/modules/legal/` | `legal/__init__.py` | `/terms` `/privacy` |
| connections | `src/modules/connections/` | `connections/__init__.py:18` | Platform connections per-user + gates |
| account_page | `src/modules/account_page/` | `account_page/__init__.py:109` | صفحة `/account` (اشتراك/pause/توكن) |

---

## 5) صفحات الواجهة وقوالب HTML

القوالب في `src/templates/`؛ تُقدَّم عبر `src/modules/pages/__init__.py`:
- `_render_page_template(filename, request)` (`pages/__init__.py:53`): لغة (lang=ar → `<html dir=rtl>`)،
  حقن `window.HUDHUD_BASE_URL`، أيقونات الموقع، manifest، وحقن الـ sidebar وrole mode server-side.
- `render_module_page(html, request)` (`pages/__init__.py:25`): لموديولات HTML المدمجة (admin_users, account, templates).

| الصفحة / المسار | القالب | مالك التوجيه | الوصول |
|---|---|---|---|
| `/` (landing) | `landing.html` | `pages/__init__.py:143` | PUBLIC |
| `/login`, `/register` | `auth.html` | `pages/__init__.py:148` | PUBLIC |
| `/dashboard` | `overview.html` | `pages/__init__.py:156` | USER |
| `/leads` | `leads.html` | `pages/__init__.py:161` | USER |
| `/studio` | `studio.html` | `pages/__init__.py:166` | USER |
| `/knowledge` | `knowledge.html` | `pages/__init__.py:171` | USER |
| `/identity` | `identity.html` | `pages/__init__.py:176` | USER |
| `/analytics` | `analytics.html` | `pages/__init__.py:181` | USER |
| `/onboarding` | `onboarding.html` | `pages/__init__.py:186` | USER |
| `/inbox` | `inbox.html` | `pages/__init__.py:191` | USER |
| `/settings` | `settings.html` | `pages/__init__.py:196` | ADMIN |
| `/automations` | `automations.html` | `pages/__init__.py:201` | USER |
| `/users` | HTML مدمج | `admin_users_page/__init__.py:594` | ADMIN |
| `/templates` | HTML مدمج | `templates_manager/__init__.py:190` | ADMIN |
| `/account` | HTML مدمج | `account_page/__init__.py:15` | USER |
| `/billing/success`, `/billing/checkout-page` | HTML مدمج | `billing_pages/__init__.py:223,227` | USER |
| `/terms`, `/privacy` | HTML مدمج | `legal/__init__.py` | PUBLIC |

**الأصول الثابتة** (`src/templates/static/`):
- `saas.css` — كل التصميم (الواجهات، البطاقات، الـ modals، المصفاة، الـ toast، الأنماط الفاتحة/الداكنة).
- `saas.js` — أدوات واجهة عامة: التبويبات، الـ modals، المصفاة، الـ toast، منسق المحادثة.
- `i18n.js` — كل الترجمة: `window.hudhudI18n.t('key')`، لغات `en`/`ar`، مفتاح `hudhud_lang`.
- `manifest.json`, `favicon*`, `icon-*.png`, `apple-touch-icon.png`.

---

## 6) خريطة الـ API التفصيلية

> قواعد عامة: كل endpoint تحت `/api/` (عدا ما هو معلن public صراحةً) يتطلب session.
> الـ admin عبر `ADMIN_PATH_PREFIXES` (`/api/ai/providers`, `/api/ai/models`, `/api/admin`,
> `/api/debug`) + صفحات `ADMIN_PAGE_PATHS` (`/settings`). التفاصيل في §10.

### 6.1 Health & System — `src/modules/health/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/health` | status/app_env/deploy_marker/threads_app_configured/cron_configured/supabase_connected/kb_documents_loaded/gates |

### 6.2 Webhooks — `src/modules/webhooks/routes.py` (المعالجات: `src/meta_api/webhooks.py`)
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/webhooks/meta`, `/api/webhook/meta`, `/api/webhook/instagram`, `/api/webhooks/meta` | Meta handshake (challenge) |
| POST | نفس الأربعة أعلاه | HMAC 256؛ يفسّر messaging + comment؛ يضيف background tasks |
| GET | `/api/webhook/threads` | Threads handshake |
| POST | `/api/webhook/threads` | HMAC بـ THREADS_APP_SECRET → capture replies كـ leads |

### 6.3 Auth — `src/modules/auth_module/__init__.py`
| الطريقة | المسار | Notes |
|---|---|---|
| POST | `/auth/register` | rate-limit 429؛ أول مستخدم admin |
| POST | `/auth/login` | rate-limit 429 |
| POST | `/auth/logout` | |
| POST | `/auth/change-password` | يتطلب الحالية، min 8 |
| GET | `/auth/google` | بدء OAuth (APP_BASE_URL على شاشة الموافقة) |
| GET | `/auth/google/callback` | |
| GET | `/auth/me` | session user |

### 6.4 Onboarding & Inbox — `src/modules/inbox_onboarding/__init__.py`
| الطريقة | المسار | Notes |
|---|---|---|
| POST | `/api/onboarding/save-all` | حفظ المعالج (KB+persona+platforms) |
| GET | `/api/inbox/conversations` | كل محادثات الـ tenant (صلاحيات) |
| GET | `/api/inbox/agent-status` | حالة الوكيل (AI pause الفعال) |
| POST | `/api/inbox/conversations/{lead_id}/takeover` | Human Takeover |
| POST | `/api/inbox/conversations/{lead_id}/send-message` | رد يدوي |
| POST | `/api/inbox/conversations/{lead_id}/send-booking-link` | رابط الحجز |

### 6.5 Leads — `src/modules/leads/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/leads` | القائمة مع الفلاتر/الترقيم |
| GET | `/api/leads/{lead_id}` | التفاصيل، UUID segment guard |

### 6.6 Identity — `src/modules/identity/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/identity/queue` | عناصر المراجعة البشرية |
| POST | `/api/identity/queue/{queue_id}/approve` | **فلتر: يتحقق من ملكية primary فقط — انتبه من candidate (cross-tenant)** |
| POST | `/api/identity/queue/{queue_id}/reject` | |

### 6.7 AI Providers & Debug — `src/modules/ai/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/ai/providers` | admin (keys مورقة) |
| POST | `/api/ai/providers` | admin؛ sync تلقائي (فشله لا يبطل الإنشاء) |
| PUT | `/api/ai/providers/{provider_id}` | admin |
| DELETE | `/api/ai/providers/{provider_id}` | admin |
| POST | `/api/ai/providers/{provider_id}/sync` | admin |
| GET | `/api/ai/models` | admin |
| GET | `/api/ai/brains` | client-facing: enabled+available brains |
| POST | `/api/ai/models/{model_id}/toggle` | admin |
| POST | `/api/ai/providers/{provider_id}/models` | admin (إضافة يدوية) |
| GET | `/api/debug/secrets-check` | admin |
| GET | `/api/debug/llm-status` | admin |
| GET | `/api/ai/pause` | حالة pause للمستخدم |
| POST | `/api/ai/pause` | toggle pause |

### 6.8 Connections — `src/modules/connections/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/connections` | الوصلات + `paid_platforms` |
| DELETE | `/api/connections/{platform}` | فصل قناة (لا يحذف البيانات) |
| GET | `/api/connections/facebook/authorize` | بدء FB Login |
| GET | `/api/connections/facebook/callback` | PUBLIC (حامل session) — توقيع state |
| GET | `/api/connections/instagram/authorize` | IG child-app OAuth |
| GET | `/api/connections/instagram/callback` | PUBLIC |
| GET | `/api/connections/threads/authorize` | |

### 6.9 Threads & Marketing — `src/modules/threads_marketing/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/threads/status` | الحالة/التكوين |
| GET | `/api/threads/oauth/authorize` | redirect، يعتمد على session (per-user) |
| GET | `/api/threads/oauth/callback` | |
| POST | `/api/threads/oauth/refresh` | |
| POST | `/api/threads/disconnect` | |
| POST | `/api/threads/publish` | نشر منشور |
| GET | `/api/threads/{thread_id}/replies` | |
| DELETE | `/api/threads/{thread_id}` | |
| GET | `/api/threads/insights` | |
| POST | `/api/threads/{thread_id}/reply` | ردًا على رد |
| GET | `/api/threads/my-posts` | |
| POST | `/api/threads/sync-replies` | |
| POST | `/api/marketing/sync-leads` | |
| POST | `/api/marketing/sync-campaigns` | |

### 6.10 Meta — `src/modules/meta/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/meta/status` | الحالة (مع كاش TTL) |
| GET | `/api/meta/posts` | |
| POST | `/api/meta/sync-posts` | |
| POST | `/api/meta/configure` | |
| POST | `/api/meta/subscribe-page` | |

### 6.11 Content Studio — `src/modules/content/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| POST | `/api/content/generate` | توليد بالـ AI (AI credits) |
| POST | `/api/content/compliance-check` | |
| POST | `/api/content/posts` | إنشاء |
| GET | `/api/content/posts` | قائمة |
| GET | `/api/studio/posts` | |
| GET | `/api/content/posts/{post_id}` | |
| POST | `/api/content/posts/{post_id}/publish-now` | |
| DELETE | `/api/content/posts/{post_id}` | |
| POST | `/api/content/scheduler/trigger` | admin (ADMIN_EXACT_PATHS) |

### 6.12 Automations — `src/modules/automations/routes.py`
| الطريقة | المسار |
|---|---|
| GET/POST | `/api/automations` |
| GET/PUT/DELETE | `/api/automations/{wf_id}` |
| POST | `/api/automations/{wf_id}/toggle` |
| POST | `/api/automations/{wf_id}/test` |

### 6.13 Knowledge Base — `src/modules/knowledge/routes.py`
| الطريقة | المسار | Notes |
|---|---|---|
| POST | `/api/knowledge/sync-meta` | جلب من Meta (social knowledge) |
| GET | `/api/knowledge/documents` | |
| GET/PUT/DELETE | `/api/knowledge/documents/{filename}` | |
| POST | `/api/knowledge/documents` | |
| POST | `/api/knowledge/upload` | ملف → chunks + embedding (RAG) |
| POST | `/api/knowledge/search` | بحث هجين tenant-scoped |

### 6.14 Analytics & Reports — `src/modules/analytics/routes.py`
| الطريقة | المسار |
|---|---|
| GET | `/api/analytics/summary` |
| GET | `/api/reports/page-performance` |
| GET | `/api/analytics/config` |
| GET | `/api/reports/activity-execution` |

### 6.15 Billing & Payments — `src/modules/billing/__init__.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/billing/quote?platforms=…&coupon=CODE` | السعر المركّب (multiplataform discount + coupon) |
| GET | `/api/billing/catalog-public` | |
| GET | `/api/billing/subscription` | |
| GET | `/api/billing/usage` | رصيد AI |
| GET | `/api/admin/billing/catalog` · PUT `/api/admin/billing/catalog/{platform}` | |
| GET/PUT | `/api/admin/billing/settings` | discounts/trial config |
| POST | `/api/payments/webhook/{provider}` | Svix signature verify (fail-closed) |
| POST | `/api/billing/checkout` | create checkout مع quote |
| GET | `/api/admin/billing/polar-diag` | |
| POST | `/api/billing/trial` | trial + card capture |
| GET/POST | `/api/admin/billing/coupons` | |
| DELETE | `/api/admin/billing/coupons/{coupon_id}` | |
| GET/PUT | `/api/admin/site-settings` | |

### 6.16 Notifications — `src/modules/notifications/__init__.py`
| الطريقة | المسار |
|---|---|
| GET | `/api/notifications` |
| GET | `/api/notifications/unread-count` |
| POST | `/api/notifications/{id}/read` |
| POST | `/api/notifications/read-all` |
| POST | `/api/admin/notifications/broadcast` |

### 6.17 Admin Console — `src/modules/admin_console/__init__.py`
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/admin/users` | list+filters |
| PATCH | `/api/admin/users/{id}` | enable/disable |
| POST | `/api/admin/users/{id}/credits` | تحميل رصيد |
| POST | `/api/admin/users/{id}/plan` | |
| GET | `/api/admin/overview` | KPIs + plan_distribution |
| GET | `/api/admin/traffic` | |
| GET | `/api/admin/system/health` | |
| POST | `/api/admin/cron/trigger/{job}` | |

### 6.18 Templates Manager — `src/modules/templates_manager/__init__.py`
| الطريقة | المسار |
|---|---|
| GET | `/api/admin/templates` |
| PUT | `/api/admin/templates/{key}` |
| POST | `/api/admin/templates/{key}/restore` |

### 6.19 Cron — `src/modules/cron_admin/routes.py` (كلها تحمل CRON_SECRET)
| الطريقة | المسار | Notes |
|---|---|---|
| GET | `/api/cron/scheduler-tick` | نفّذ scheduler + check credits |
| GET | `/api/cron/insights-sync` | |
| GET | `/api/cron/threads-token-refresh` | تحديث غير منتهٍ |
| GET | `/api/cron/instagram-token-refresh` | |
| GET | `/api/cron/billing-reconciliation` | |
| GET | `/api/admin/alerts` | collect_alerts |

### 6.20 Compliance & Legal — `src/meta_api/compliance_pages.py` + `src/modules/legal/__init__.py`
| الطريقة | المسار |
|---|---|
| GET | `/privacy`, `/data-deletion`, `/data_deletion` (public) |
| POST | `/api/data-deletion` (public, HMAC) |
| POST | `/api/threads/uninstall` (public, HMAC) |
| GET/POST | `/api/deauthorize` |
| GET | `/terms` |

---

## 7) طبقة الخدمات

| المجال | الملفات | الوظيفة بالتفصيل |
|---|---|---|
| **Orchestrator** | `src/agent/orchestrator.py` | انظر §2 — النواة: webhook→owner→token→AI→send→reply_error |
| **Conversation Engine** | `src/agent/conversation_engine.py` | §2.1 — Gemini+RAG + fallbacks; `used_ai` علامة العدّاد |
| **Knowledge Base** | `src/agent/knowledge_base.py` → `src/knowledge/db_knowledge_base.py`, `semantic_engine.py`, `document_processor.py`, `meta_crawler.py`, `utils.py` | RAG هجين (pgvector + tsvector + RRF)؛ وضع DB per-tenant، وضع file للاختبارات؛ `sanitize_safe_filename` |
| **Content Engine/Scheduler** | `src/agent/content_engine.py`, `src/agent/scheduler.py` | توليد المحتوى؛ حلقة نشر 30s (غير Vercel)؛ الجدولة عبر cron في Vercel |
| **Leads** | `src/leads/service.py`, `src/leads/models.py`, `src/leads/comment_bridge.py` | `PlatformSource` (facebook/instagram/threads/manual/other)؛ CRUD مع `user_id` scope؛ comment→lead |
| **Identity** | `src/identity/extractor.py`, `resolver.py`, `review_queue.py` | استخراج الملفات الشخصية؛ مطابقة معرّفات المنصات + cross-link score + عتبات الثقة؛ مراجعة بشرية |
| **Billing** | `src/modules/billing/services.py` (PricingService, EntitlementService), `usage.py` | quote مع discount جدول `billing_discounts`؛ entitlements fail-closed؛ عدّاد AI بالرصيد |
| **Payments** | `src/payments/base.py`, `registry.py`, `polar.py` | عقد `PaymentProvider` (create_checkout/verify_webhook/parse_event/start_trial)؛ Polar مع وضع sandbox/live؛ Svix |
| **Connections** | `src/modules/connections/service.py`, `models.py` | تخزين token مشفّر (Fernet بالـ SECRET_KEY)؛ `owner_for_account`/`get_active_token_for_account`/`get_send_token_for_instagram`؛ `assert_entitled` |
| **Meta API** | `src/meta_api/client.py` (GRAPH v26) · `token_manager.py` · `webhooks.py` · `threads_oauth.py` · `publishing.py` · `feed_sync.py` · `extended_api.py` (threads_publisher, marketing_leads_sync, meta_insights_sync) · `permissions.py` · `rate_limiter.py` · `compliance_pages.py` | Meta Graph API كل شيء؛ مصادقة طويلة الأمد؛ تحديث token (cron)؛ rate limits؛ بيانات الامتثال |
| **AI Providers** | `src/ai/provider_manager.py`, `src/ai/pause.py` | إدارة مزوّدي/نماذج؛ مفتاح pause (مستخدم/عالمي) |
| **Automations** | `src/automations/service.py`, `models.py` | workflows بصرية لكل مستخدم؛ `process_comment_event` |
| **Content Studio** | `src/content_studio/service.py`, `models.py`, `compliance_agent.py` | منشئ محتوى؛ امتثال تلقائي للسياسات (brand) |
| **Analytics/Reporting** | `src/analytics/statistics_engine.py`, `page_performance.py`, `src/reporting/report_generator.py`, `activity_reporter.py` | مقاييس؛ أداء الصفحة |
| **Notifications** | `src/modules/notifications/service.py`, `hooks.py` | إشعار الجرس + ربط الوظائف (trial, credits…) |
| **Admin Alerts** | `src/core/admin_alerts.py` | تجميع قبل /api/admin/alerts |

---

## 8) قاعدة البيانات والهجرات

**السلاسل**: `database/schema.sql` (مرجع كامل باليد) · `database/migrations/001…023` (**التطبيق الفعلي**).

| الملف | المحتوى |
|---|---|
| `001` | `users` (role/plan/credits/...)، `processed_events` (dedup)، `app_settings` |
| `002` | hardening أمني، pgvector extension، indexes content_posts/messages |
| `003/003b/003c` | `kb_documents` + `kb_chunks`، FTS `tsv`، embedding 3072، `match_kb_chunks()` |
| `004` | `ai_providers`, `ai_models` (enabled/available...) |
| `005` | terms acceptance (`users` flags) |
| `006` | `notifications` + function `create_notification` |
| `007` | `site_traffic` + users.ai_credits (Admin Console) |
| `008` | `message_templates` (lifecycle templates) |
| `009` | **Billing**: `platform_addons_catalog`, `user_subscriptions`, `user_entitlements`, `payment_events`, `usage_events`, `coupons`, `coupon_redemptions` |
| `010` | per-user isolation indexes: leads/messages/content_posts/page_performance_metrics (user_id) |
| `011` | `platform_connections` (access_token_encrypted) + trigger `touch_updated_at` |
| `012` | lead avatar |
| `013` | Threads leads index (threads_account_id) |
| `014` | `automations_workflows` (user_id) |
| `015` | lead_source_threads |
| `016` | platform_enum + threads |
| `017` | KB per-user (`user_id` on kb_documents) + `match_kb_chunks` scope |
| `018` | users.ai_paused (AI Pause) |
| `019` | automations_workflows.id → text |
| `020` | platform_enum + manual/other |
| `021` | kb tenant fail-closed guard |
| `022` | saas tenant hardening |
| `023` | guard null embedding in `match_kb_chunks` |
| (منقول تعليقات) | Alerts/hooks تفوق هذه الجداول أعلاه |

**تطبيق ترقية**: `python scripts/apply_migration.py database/migrations/NNN_x.sql <SUPABASE_ACCESS_TOKEN>`
(المفكك semicolon-aware يحترم `$$` blocks). الفحص: `scripts/audit_supabase.py`.

---

## 9) الإعدادات والبيئة

المصدر: `src/config.py` (pydantic-settings؛ يقرأ `.env`).

| المجموعة | المتغيرات |
|---|---|
| App | `APP_ENV`(default development) · `APP_DEBUG` · `TESTING` · `PORT` · `HOST` |
| Secret | **`SECRET_KEY`** — صُلب الأمان: HMAC sessions (`auth.py:151-156`) + Fernet tokens (`crypto.py:16-19`) + OAuth state signing. لا تشغّل بالقيمة الافتراضية في production. |
| Origin | `APP_BASE_URL` = `https://www.hudhd.com` (كل URL مطلق يُشتق) |
| Supabase | `SUPABASE_URL` · `SUPABASE_KEY` · `SUPABASE_SERVICE_ROLE_KEY` |
| Meta | `META_APP_ID` · `META_APP_SECRET` · `META_PAGE_ID` · `META_PAGE_ACCESS_TOKEN` · `META_INSTAGRAM_ACCOUNT_ID` · `META_WEBHOOK_VERIFY_TOKEN`/`WEBHOOK_VERIFY_TOKEN` (fail-closed) · `CRON_SECRET` |
| LLM | `LLM_PROVIDER`(gemini) · `GEMINI_API_KEY` · `LLM_MODEL`(gemini-flash-latest) · `OPENAI_API_KEY`(موقوف) |
| Google OAuth | `GOOGLE_CLIENT_ID` · `GOOGLE_CLIENT_SECRET` |
| Polar | `POLAR_ACCESS_TOKEN` · `POLAR_WEBHOOK_SECRET`(whsec_…) · `POLAR_ORGANIZATION_ID` |
| Threads | `THREADS_APP_ID` · `THREADS_APP_SECRET` · `THREADS_REDIRECT_URI` (يُلحق APP_BASE_URL) · `THREADS_ACCESS_TOKEN`/`THREADS_USER_ID` (fallback) · `THREADS_BASE_URL` |
| Instagram child app | `IG_APP_ID` · `IG_APP_SECRET` (مطلوب لـ IG Login؛ الـ META_APP_ID لا يصلح) |
| Governance | `MAX_MESSAGES_PER_MINUTE`(20) · `ENFORCE_24H_WINDOW`(true) · `REQUIRE_MANUAL_IDENTITY_CONFIRMATION`(true) · `CONFIDENCE_THRESHOLD_AUTO_LINK`(0.95) · `CONFIDENCE_THRESHOLD_QUEUE_REVIEW`(0.50) |

> **الأسرار في الغير**: Vercel env + `.env` المحلي (غير tracked). أدوات: `scripts/check_secrets_live.py`,
> `scripts/sync_vercel_env.py`, `scripts/audit_vercel_env.py`.

---

## 10) الأمان والتحقق من المسارات

**AuthMiddleware** (`src/main.py:189-212`) + **policy lists** (`src/core/auth.py`):

- `PUBLIC_EXACT_PATHS`/`PUBLIC_PATH_PREFIXES` (`auth.py:30,44`): landing، auth، webhooks، `/api/cron`، data-deletion، payments/webhook، threads/uninstall. + declarations من الموديولات.
- `ADMIN_EXACT_PATHS` (`auth.py:57`): `/api/content/scheduler/trigger`.
- `ADMIN_PAGE_PATHS` (`auth.py:62`): `/settings` (+ pages من module registry).
- `ADMIN_PATH_PREFIXES` (`auth.py:67`): `/api/ai/providers`، `/api/ai/models`، `/api/admin`، `/api/debug`.
- `ADMIN_MUTATION_PREFIXES` (`auth.py:78`): **فارغ** — لا توسّع بلا داعي (كل عملية حساسة في الـ handler).
- Middlewares: `uuid_segment_guard` (تصفية ids → 404) + `auth_middleware` + `_traffic_log_middleware`
  (تسجيل site_traffic لصفحات dashboard فقط).

**نموذج الجلسة**: HMAC-signed cookie `hudhud_session` (`auth.py:25,151`؛ `SESSION_TTL=7 أيام`)؛ كلمة المرور
PBKDF2-HMAC-SHA256 (390k تكرار، salt لكل مستخدم)؛ `auth_limiter` 429 لصفّ login/register.
**فقدان التوكن**: Fernet يستمد من SECRET_KEY — دوران SECRET_KEY يبطل التوكنات المخزنة (انظر SOP_03).

---

## 11) الاختبارات

- **التشغيل**: `python -m pytest tests` (من الجذر؛ بهذا الشكل فقط — فيت دائمًا لا تشغّل `pytest` العاري،
  فالتحصيل يأت من مجلد `tests/` المحدد). عبر CI في `.github/workflows/tests.yml`.
- **`tests/conftest.py`** (في الصورة الحرجة): يضبط `TESTING=true`؛ يعزل `user_store` إلى ذاكرة؛
  KB في وضع file بمجلد tmp (لا يلمس الجداول الحي)؛ يعطّل `GEMINI_API_KEY` (لا استدعاءات live)؛
  يعطّل dedup DB وevent_deduplicator؛ fixtures: `client` (admin) · `client_as_user` · `anon_client`
  · `admin_creds` (المالك seed).
- **تغطية**: auth/security، platform connections (IG state/refresh)، usage credits (honest reply_sent)،
  identity resolution، KB/RAG، billing/payments، automations، content، inbox onboarding، إشعارات،
  ثقافات Threads OAuth، legal، admin console، cron budget، tenant isolation (RAG/leads)،
  anti-fabrication sweeps.

---

## 12) سكربتات الجذر والسكربتات المعتمدة

- **جذر `src/` نظيف**: كل سكربتات الجلسات السابقة (audit/fix/scan/log/debug/check…)
  نُقلت إلى **`scripts/archive/`** وهي الآن تحت version control ومسجلة واحد بواحد في §16.
  **قاعدة**: لا تُنشئ سكربتات جذر جديدة أبدًا — `scripts/` للمعتمد، و`scripts/archive/` للاستهلاكي.
- **`scripts/` المعتمدة**: `apply_migration.py` · `apply_migration_00X.py` (لـ 001/002/005/009/010) ·
  `audit_supabase.py` · `audit_vercel_env.py` · `check_secrets_live.py` · `sync_vercel_env.py` ·
  `set_polar_products.py` · `seed_real_kb.py` · `fix_kb_documents_rls.py` · `final_verification.py` ·
  `final_acceptance_sweep.py` · `cleanup_dev_users.py` ·
  `record_*_cdp.py` (توليد تسجيلات Meta لأجل App Review) · `generate_brand_icons.py` ·
  `convert_webp_to_mp4.py` · `isolation_signature.py`/`isolate_signature.py` (تصحيح التواقيع) ·
  `reset_test_passwords.py` · `_fix_consent_test.py` · `_fix_meta_test.py` · `_update_review_guide.py`.

---

## 13) جدول Quick-start التحريري

| المهمة | افتح |
|---|---|
| صفحة جديدة بسيطة | `src/modules/pages/__init__.py` (أضف قالبًا في `src/templates/` + route + NavEntry) |
| صفحة جديدة لها منطق خاص | أنشئ موديولًا جديدًا (طابع §4.1) + `register_module` + سجّله في `main.py:228-269` |
| API جديد | route في `src/modules/<name>/routes.py` أو `__init__.py` |
| تعديل صلاحيات/امتيازات | `src/core/modules.py` (access per module/page) و/أو `src/core/auth.py` (lists) |
| تغيير نص الرد الآلي | `src/agent/conversation_engine.py` (fallbacks/المحفزات)، `orchestrator.py` (الدفق) |
| تغيير نموذج AI/مزوّد | `src/ai/provider_manager.py`، `src/config.py` (`LLM_*`)، admin UI `/api/ai/*` |
| Knowledge Base/RAG | `src/knowledge/*` + `src/agent/knowledge_base.py` + migrations `003*`/`017/021/023` |
| Webhooks/platform جديدة | `src/modules/webhooks/routes.py` + `src/meta_api/webhooks.py` + `src/platforms/registry.py` (يتبع قاعدة registry) |
| جدول جديد | `database/migrations/NNN_*.sql` + `apply_migration.py` |
| الأسعار/الخصومات | `src/modules/billing/services.py` (§PricingService/§_discount_percent) |
| بوابة دفع جديدة | `src/payments/<name>.py` (ترث `PaymentProvider`) + سجل في `src/payments/registry.py` |
| UI/تصميم | `src/templates/static/saas.css`، `saas.js` |
| ترجمات | `src/templates/static/i18n.js` |
| ربط منصة (OAuth) | `src/modules/connections/*`، `src/meta_api/threads_oauth.py`، `connections/routes.py` |
| إشعارات جديدة | `src/modules/notifications/service.py`، hooks في `notifications/hooks.py` |
| Cron جديد | `src/modules/cron_admin/routes.py` + `vercel.json` crons |
| توثيق قرار | `docs/PROJECT_MEMORY.md` (append-only) + `docs/PROJECT_REPORTS/SESSION_LOGS/` |
| Meta App Review | `docs/APP_REVIEW/` (plans + prompts + videos) |

---

## 14) قواعد العمل الصارمة

1. **API responses**: لا تسرّب void؛ أعد أخطاء عامة آمنة — `safe_error`/`_safe_error`
   (`src/core/http_utils.py:5`). `ValueError` يمرّ كـ message تحقق فقط.
2. **Default-deny**: كل POST/PUT/PATCH/DELETE يلزم session إلا بإعلان `public` صريح.
3. **Fail-closed gating**: entitlements/tenant/credits — الأخطاء = "لا وصول". لا نفوذ أبدًا.
4. **الـ webhooks تستهلك مرة واحدة**: dedup عبر `processed_events` — لا تسمح لرسالة مكررة أن تُعالج مرتين.
5. **Billing then send**: سعر/خصم يُحسب فقط في `src/modules/billing/services.py`؛ البوابة تُدفع.
   لا تحسب خصمًا داخل `polar.py` (إن أردت إصلاحه: حدّث `quote()` لتنتج `coupon_polar_id`).
6. **Migrations** تراكمية append-only: أضف `NNN_`, لا تعدّل `001–023`.
7. **الاختبار** لكل تغيير سلوك في `tests/`؛ شغّل `python -m pytest tests` قبل "تم".
8. **لا سكربتات جذر جديدة**؛ ضعها في `scripts/` والاختبارات في `tests/`.
9. **Secrets** لا تُطبع/تُسجَّل قط (فحص: `scripts/check_secrets_live.py`).

---

## 15) أوامر سريعة

```bash
python main.py                                    # تشغيل محلي (uvicorn reload, port 8000)
python -m uvicorn src.main:app --port 8000        # تشغيل محلي بديل (بدون reload)
python -m pytest tests                            # كل الاختبارات (الحاصل الوحيد لـ CI)
python -m pytest tests/test_platform_connections.py   # ملف محدد
python scripts/apply_migration.py database/migrations/NNN_x.sql <TOKEN>   # ترقية DB
python scripts/check_secrets_live.py              # فحص الأسرار في الحي
python scripts/audit_supabase.py                  # فحص الاتصال والجداول
```

> بيئة الحي: `https://www.hudhd.com` — `/health` يعرض Supabase و cron config و gates.

---

## 16) فهرس الأرشيف الكامل

كل ملف أرشيفي **مسجّل هنا بمساره ودوره** — إذا أردت التعديل أو الاستفادة من أي أداة قديمة، تجده من الجدولين. الأسماء تعكس الوظيفة؛ بعضها أدوات "استخدم مرة واحدة" وإصلاحات جلسات سابقة (لا تشغّلها على الوضع الحي دون فهم ماذا تفعل).

### 16.1 `scripts/archive/` (74 سكربت جلسات سابقة — tracked)

| السكربت | العامل على: | الدور (من رأس الملف) |
|---|---|---|
| `scripts/archive/add_mode_key.py` | dashboard | إضافة mode key لصفحة |
| `scripts/archive/add_reply_route.py` | routes | إضافة route رد |
| `scripts/archive/add_token_resolution.py` | connections | إضافة نواة توكن resolution |
| `scripts/archive/append_pause_routes.py` | ai | إلحاق مسارات AI Pause (AST patch) |
| `scripts/archive/apply_017.py` | Supabase | تطبيق migration 017 عبر SUPABASE_ACCESS_TOKEN |
| `scripts/archive/apply_019.py` | Supabase | تطبيق migration 019 |
| `scripts/archive/backfill_content_owner.py` | content_posts | backfill owner_id للبيانات القديمة |
| `scripts/archive/check_auth_keys.py` | auth | فحص مفاتيح auth |
| `scripts/archive/check_duplicates.py` | Supabase | فحص التكرارات في البيانات |
| `scripts/archive/check_kb_schema.py` | KB | فحص سكيما kb_documents/kb_chunks |
| `scripts/archive/check_store_sig.py` | user_store | فحص توقيع سلوك store |
| `scripts/archive/check_threads_conn.py` | Threads | فحص اتصال Threads الحي |
| `scripts/archive/check_users_cols.py` | users | فحص أعمدة جدول users |
| `scripts/archive/cutover_automations.py` | automations | التحويل لنسق workflows الجديد |
| `scripts/archive/debug_my_posts.py` | threads | تشخيص `/api/threads/my-posts` |
| `scripts/archive/debug_myposts.py` | threads | تشخيص my-posts (regex) |
| `scripts/archive/debug_select.py` | Supabase | تشخيص استعلامات SELECT |
| `scripts/archive/debug_select2.py` | Supabase | تشخيص ثانٍ للـ SELECT |
| `scripts/archive/debug_threads_reply.py` | threads | تشخيص POST رد Threads (خطأ + أشكال صحيحة) |
| `scripts/archive/debug_threads_ui.py` | Threads UI | تشخيص واجهة Threads |
| `scripts/archive/dedupe_lang_buttons.py` | templates | إزالة أزرار اللغة المكررة |
| `scripts/archive/find_threads_opt.py` | settings | البحث عن إعداد Threads في الكود |
| `scripts/archive/fix_ai_pill.py` | inbox | Class-D: حبة AI كانت ادعاءً كاذبًا → جعلها تعكس الواقع |
| `scripts/archive/fix_backslash.py` | strings | إصلاح backslash في سلاسل |
| `scripts/archive/fix_backslash2.py` | strings | إصلاح backslash (جولة ثانية) |
| `scripts/archive/fix_cascade_test.py` | tests | إصلاح اختبار cascade |
| `scripts/archive/fix_layer1.py` | backend | إصلاحات Layer-1 (ruff — backend فقط، بدون UI) |
| `scripts/archive/fix_myposts_route.py` | routes | إصلاح مسار my-posts |
| `scripts/archive/fix_nav_test.py` | tests | إصلاح اختبار الـ nav |
| `scripts/archive/fix_persist.py` | persistence | إصلاح مشكلة بقاء البيانات |
| `scripts/archive/fix_resolve_fallback.py` | identity | إصلاح fallback في identity resolution |
| `scripts/archive/fix_sanitizer.py` | KB | إصلاح sanitize_safe_filename |
| `scripts/archive/fix_test_hygiene.py` | tests | تنظيف التستات (AST) |
| `scripts/archive/fix_threads_i18n.py` | i18n | إصلاح ترجمة Threads |
| `scripts/archive/fix_threads_oauth_500.py` | oauth | إصلاح 500 في Threads OAuth |
| `scripts/archive/get_rpc.py` | Supabase | استدعاء RPC عبر Supabase API |
| `scripts/archive/inject_ai_pause_ui.py` | ai UI | حقن واجهة AI Pause (AST patch) |
| `scripts/archive/inject_threads_card.py` | dashboard | حقن بطاقة Threads |
| `scripts/archive/inject_threads_ui.py` | Threads UI | حقن واجهة Threads |
| `scripts/archive/log_button_audit.py` | UI | تسجيل فحص الأزرار |
| `scripts/archive/log_cron_fix.py` | cron | تسجيل إصلاح cron |
| `scripts/archive/log_final.py` | audit | سجل نهائي |
| `scripts/archive/log_final6.py` | audit | سجل نهائي (نسخة 6) |
| `scripts/archive/log_full_audit.py` | audit | سجل تدقيق شامل |
| `scripts/archive/log_gate_closed.py` | gates | سجل إغلاق gate |
| `scripts/archive/log_ig_diag.py` | Instagram | سجل تشخيص Instagram |
| `scripts/archive/log_settings_review.py` | settings | سجل مراجعة الإعدادات |
| `scripts/archive/log_submission.py` | App Review | سجل إرسال |
| `scripts/archive/log_truth_audit2.py` | audit | سجل تدقيق الصدق (نسخة 2) |
| `scripts/archive/move_threads_opt.py` | settings | نقل إعداد Threads في الصفحات |
| `scripts/archive/perform_api_tests.py` | threads | استدعاءات اختبار threads_manage_replies المطلوبة |
| `scripts/archive/refactor_db_helpers.py` | db | إعادة هيكلة مساعدات قاعدة البيانات |
| `scripts/archive/repro_send_500.py` | inbox | إعادة إنتاج 500 الإرسال اليدوي + قراءة الاستثناء الحقيقي |
| `scripts/archive/scan_automations.py` | automations | فحص workflows |
| `scripts/archive/scan_bits2.py` | audit | فحص مقاطع (نسخة 2) |
| `scripts/archive/scan_content.py` | content | فحص Content Studio |
| `scripts/archive/scan_content2.py` | content | فحص محتوى (نسخة 2) |
| `scripts/archive/scan_gaps.py` | landing | البحث عن فجوات فارغة render-blocking |
| `scripts/archive/scan_publisher.py` | publishing | فحص النشر |
| `scripts/archive/scan_review_bits.py` | App Review | فحص عناصر App Review |
| `scripts/archive/see_load.py` | pages | فحص الـ load |
| `scripts/archive/sweep_disease.py` | cross-site | مطاردة أنماط الأخطاء المشتركة عبر الموقع |
| `scripts/archive/sweep_js_fabrication.py` | JS | فحص بيانات مختلقة في الـ JS/inline-scripts |
| `scripts/archive/test_ai_pause_e2e.py` | ai | E2E: AI Master Pause (تشغيل + منع فعلي) |
| `scripts/archive/test_no_flash.py` | templates | إثبات خلو HTML الخام من الوميض (بدون JS) |
| `scripts/archive/test_pill_reflect.py` | inbox | E2E: انعكاس حالة الـ pause الحقيقية في الحبة |
| `scripts/archive/test_reply_prod.py` | threads | اختبار WRITE لـ threads_manage_replies على الحي (احذر) |
| `scripts/archive/test_store_live.py` | store | اختبار store على الحي |
| `scripts/archive/test_threads_ui.py` | Threads UI | اختبار واجهة Threads |
| `scripts/archive/update_gate_doc.py` | docs | تحديث وثيقة الـ gate |
| `scripts/archive/verify_nav_structure.py` | nav | تحقق الـ nav المُولّد (دليل خلو الوميض) |
| `scripts/archive/verify_review_gaps.py` | App Review | تحقق ads/campaigns/identity chip |
| `scripts/archive/wire_cutover.py` | automations | ربط التحوّل الجديد |
| `scripts/archive/wire_orchestrator_token.py` | orchestrator | ربط التوكن في orchestrator |

### 16.2 `scripts/` (4 ملفات مساعدة — tracked)

| السكربت | الدور |
|---|---|
| `scripts/_fix_consent_test.py` | تحديث اختبار consent: checkbox وحيد يتحكم بالمسارين |
| `scripts/_fix_meta_test.py` | إصلاح استدعاءات test_meta_api_calls.py لـ v26 endpoints الصحيحة |
| `scripts/_update_review_guide.py` | تحديث META_APP_REVIEW_GUIDE.md |
| `scripts/reset_test_passwords.py` | إعادة تعيين كلمة مرور admin.test والتحقق من الدخول |