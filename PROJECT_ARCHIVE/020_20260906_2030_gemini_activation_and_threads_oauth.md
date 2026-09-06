# [020] دليل إنجاز تفعيل Gemini وربط Threads (Gemini Activation & Threads OAuth Walkthrough)
- **التاريخ**: 2026-09-06 20:30 (UTC+3)
- **الوكيل المنفذ**: opencode (GLM)
- **الحالة**: مكتملة ✅ — 70/70 اختبار، Gemini حي على الإنتاج، Threads جاهز للتفويض

---

## 1. تفعيل Gemini (اكتمل بالكامل)
| البند | التفاصيل |
|---|---|
| المفتاح | صيغة جديدة `AQ.Ab8...` — هُجرت من URL `?key=` إلى **header** `X-goog-api-key` في 3 وحدات |
| الموديل | `gemini-flash-latest` (الاكتشاف: gemini-2.5-flash و2.0-flash متقاعدان للمستخدمين الجدد — 404) |
| 🔥 جذر المشكلة | متغير بيئة Windows قديم (User-scope) كان **يطغى على .env** (أولوية pydantic-settings) بمفتاح منهك حصته (429) — أُصلح بالكتابة فوقه |
| إصلاح إضافي | `thinkingBudget: 0` (موديلات flash-latest تاكل ميزانية الـ output في thinking) + maxOutputTokens 2500/800 + تجميع multi-part text |
| تشخيص دائم | `GET /api/debug/llm-status` (admin) — استدعاء حي مصغر يرجع النتيجة الدقيقة |
| **الإثبات الحي** | `POST /api/content/generate` → **`model_used: Gemini (gemini-flash-latest)`** + Hook عربي + 8 هاشتاجات |

## 2. ربط Threads بـ OAuth (جاهز — خطوة المالك متبقية)
- **App مستقل**: 2373862910115515 (Threads لا يعمل بتوكن الصفحة — يحتاج OAuth خاص)
- وحدة `src/meta_api/threads_oauth.py`: authorize URL + state CSRF أحادي الاستخدام (10 دقائق) → تبادل كود → توكن 60 يوم → تجديد تلقائي قابل للاستدعاء
- التخزين: Supabase `app_settings['threads_credentials']` مع تتبع انتهاء الصلاحية
- **ThreadsPublisher** أعيد توصيله: يرفض النشر بدون توكن مربوط (بدل توكن الصفحة الفاشل)
- Endpoints: status / authorize (admin) / callback / refresh (admin) / disconnect (admin)
- واجهة Settings: بانل Threads كامل (حالة + ربط + تجديد + فصل)

### خطوة المالك الوحيدة (دقيقة واحدة)
1. لوحة تطبيق Threads → Settings → **Add Redirect URI**:
   `https://hudhud-radar-steel.vercel.app/api/threads/oauth/callback`
2. افتح `/settings` → اضغط **🧵 ربط حساب Threads** → وافق → عُد تلقائياً
3. بعدها نشر الثريدز يعمل فوراً من `/api/threads/publish`

## 3. تنظيف إضافي
- حذف ~1000 صف اختبار تسرّبت سابقاً لجدول `processed_events` الحي + عزل class-level في conftest يمنع التكرار نهائياً

## 4. الجودة
- **8 اختبارات Threads جديدة** → المجموع **70/70 PASSED**
- Secrets (Gemini + Threads) في `.env` + Vercel فقط — لم تُرفع لـ git

## 5. قرارات مالك مسجلة
- META_APP_SECRET القديم يبقى مؤقتاً (الريبو خاص) — التدوير مؤجل
- جميع المفاتيح شاركت في الشات — يُنصح بإعادة توليدها بعد الجلسة (خطر منخفض)
