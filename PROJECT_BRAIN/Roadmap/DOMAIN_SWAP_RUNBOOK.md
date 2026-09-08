# Domain Swap Runbook — استبدال الدومين بدون أخطاء ولا أشياء مخفية

> **القاعدة الذهبية بعد الإصلاح (سبتمبر 2026):** الكود كله بيقرأ الدومين من `settings.APP_BASE_URL` — متغير واحد. ممنوع أي hardcode لدومين في الكود. أي موضع جديد يحتاج رابط مطلق → يشتق من `APP_BASE_URL` (باك) أو `window.HUDHUD_BASE_URL` (فرونت).

---

## 🟢 التنفيذ الحالي: hudhd.com (سبتمبر 2026)

| البند | القيمة |
|---|---|
| الدومين المدفوع (Hostinger) | `hudhd.com` |
| **الـ Canonical المعتمد** | `https://www.hudhd.com` (Vercel اختار www تلقائياً كأول دومين أضيف — apex بيعمل 308 redirect عليه تلقائياً) |
| DNS (Hostinger) | `A @ → 216.198.79.1` + `CNAME www → vercel-dns` ✅ منفذ |
| Vercel Domains (hudhud2) | `www.hudhd.com` + `hudhud-radar.vercel.app` ✅ شغالين SSL 200 |
| Local `.env` | `APP_BASE_URL=https://www.hudhd.com` ✅ محدّث |
| **قيد التنفيذ** | تحديث allowlists (جوجل/ثريدز/ميتا/سوبابيز/cron) + env flip في Vercel |

### قيم copy-paste لكل لوحة (www.hudhd.com)

**Google Cloud → OAuth Client → Authorized redirect URIs (أضف — سيب القديم):**
```
https://www.hudhd.com/auth/google/callback
```

**Threads app dashboard (استبدل الثلاثة):**
```
Redirect Callback URL:  https://www.hudhd.com/api/threads/oauth/callback
Uninstall Callback URL: https://www.hudhd.com/api/threads/uninstall
Delete Callback URL:    https://www.hudhd.com/api/data-deletion
```

**Meta app (تطبيق فيسبوك):**
```
Facebook Login → Valid OAuth Redirect URIs (أضف):
https://www.hudhd.com/settings

Webhooks → Callback URL (حدّث):
https://www.hudhd.com/api/webhook/meta

Data Deletion Callback (حدّث):
https://www.hudhd.com/api/data-deletion
```

**Supabase → Auth → URL Configuration:**
```
Site URL:      https://www.hudhd.com
Redirect URLs: https://www.hudhd.com/**  (سيب القديمة أيضاً)
```

**cron-job.org (الـ jobين):**
```
https://www.hudhd.com/api/cron/insights-sync?key=<نفس CRON_SECRET>
https://www.hudhd.com/api/cron/scheduler-tick?key=<نفس CRON_SECRET>
```

**Vercel env (hudhud2 — All Environments) ثم Redeploy:**
```
APP_BASE_URL=https://www.hudhd.com
```

### ترتيب التنفيذ الآمن (نافذة كسر صفرية تقريباً)
1. جوجل + FB Login redirect: **أضف الجديد مع الإبقاء على القديم** (آمنة في أي وقت)
2. Threads (3 حقول) + Vercel APP_BASE_URL + Redeploy: **نفس الجلسة ورا بعض** (ثواني)
3. Meta webhook + data-deletion + Supabase + cron
4. تحقق وكيل: /health على الدومينين + OAuth flows + فحص openapi

---

## 1️⃣ مصادر الحقيقة الوحيدة (بعد التوحيد)

| الموضع | المصدر |
|---|---|
| باكند — أي رابط مطلق | `settings.APP_BASE_URL` (env: `APP_BASE_URL`) |
| Threads redirect URI | مش بيحتاج env — مشتق: `EFFECTIVE_THREADS_REDIRECT_URI` = `{APP_BASE_URL}/api/threads/oauth/callback` |
| رابط data-deletion المُعاد لـ Meta | `compliance_pages.py` → من `APP_BASE_URL` |
| فرونت — أي رابط معروض | `window.HUDHUD_BASE_URL` (محقون في `<head>` من `render_page_template`) + عناصر `data-base-url="/path"` |
| سكربتات الـ ops | `os.environ.get("APP_BASE_URL", "https://hudhud-radar.vercel.app")` |

**ملاحظة:** لو `THREADS_REDIRECT_URI` موجود كـ env بيتعمد عليه بدل المشتق — سيبه فاضي إلا لو عايز override.

## 2️⃣ خطوات تبديل الدومين (لما تشتري دومين جديد)

### المرحلة 1 — Vercel (النطاقين حسب R8)
1. اشتري الدومين وأضفه في Vercel: `vercel.com` → scope **hudhud2** → project `hudhud-radar` → Settings → Domains → Add
2. حدّث env في **النطاقين** (hudhud2 + team):
   - `APP_BASE_URL=https://الدومين-الجديد`
   - شيل `THREADS_REDIRECT_URI` (أو حدّثه) من النطاقين
3. أعد النشر على النطاقين عشان الـ env الجديد ياخد مفعول

### المرحلة 2 — لوحات Meta/Threads/Google (Allowlists)
| اللوحة | الحقل | القيمة الجديدة |
|---|---|---|
| تطبيق فيسبوك | Facebook Login → Valid OAuth Redirect URIs | `https://الدومين-الجديد/settings` |
| تطبيق فيسبوك | Webhooks → Callback URL | `https://الدومين-الجديد/api/webhook/meta` |
| تطبيق فيسبوك | Data Deletion Callback | `https://الدومين-الجديد/api/data-deletion` |
| تطبيق Threads | Redirect Callback URL | `https://الدومين-الجديد/api/threads/oauth/callback` |
| تطبيق Threads | Uninstall Callback URL | `https://الدومين-الجديد/api/threads/uninstall` |
| تطبيق Threads | Delete Callback URL | `https://الدومين-الجديد/api/data-deletion` |
| Supabase Auth → URL Configuration | Site URL | `https://الدومين-الجديد` |
| Supabase Auth → Redirect URLs | أضف | `https://الدومين-الجديد/**` |
| Google Cloud OAuth Client | Authorized redirect URIs | `https://الدومين-الجديد/auth/google/callback` |

### المرحلة 3 — cron-job.org (خارج الريبو)
1. حدّث الـ job 8045365: URL → `https://الدومين-الجديد/api/cron/scheduler-tick?key=CRON_SECRET` (مع الحفاظ على نفس السر)

### المرحلة 4 — التحقق (لا تتجاهل)
```powershell
# 1. الصحة والدومين الجديد
curl https://الدومين-الجديد/health
# 2. لا يوجد أي إشارة للدومين القديم في الصفحات
(Invoke-WebRequest "https://الدومين-الجديد/settings").Content -match "hudhud-radar.vercel.app"  # MUST be False
# 3. الـ callback المُعاد لـ Meta جاي من APP_BASE_URL
# 4. جرب OAuth كامل (Google + Threads) من الدومين الجديد
```

### المرحلة 5 — تنظيف
- حدّث `APP_BASE_URL` في `.env` المحلي
- غيّر الدومين القديم: حافظ عليه redirect 301 للجديد لمدة شهر (SEO + روابط قديمة)

---

## 3️⃣ ماذا **لا** يحتاج تغيير (تلقائي)
- كل روابط الـ OAuth الجديدة (Google callback بيتبنى من الـ request نفسه)
- صفحة الإعدادات (تعروض الدومين من `HUDHUD_BASE_URL`)
- رابط data-deletion في رد Meta
- أي سكربت ops (بيقرأ `APP_BASE_URL` من الـ environment)

## 4️⃣ سجل التغييرات
| التاريخ | التغيير |
|---|---|
| 2026-09-07 | التوحيد الأول: APP_BASE_URL + إزالة كل hardcode (steel → canonical في .env) |
