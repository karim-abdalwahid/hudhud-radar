# 🔍 تقرير الفحص الشامل — منصة Hudhud (أمر الإصلاح)

> بتاريخ: الجمعة، 11 سبتمبر 2026 — النتائج تم **التحقق منها داخل الريبو** (file:line لكل تهمة)
> قبل حفظ هذا الملف. هذا الأمر هو خطة الإصلاح المعتمدة من المالك، ويُكتفى بالتعديلات
> الجراحية فقط دون كسر أي كود غير مرتبط.

## 🟥 1) إجبار SECRET_KEY في الإنتاج

**وصف الداء:** `SECRET_KEY` له قيمة افتراضية مكتوبة في الكود
(`dev-secret-key-change-in-production-32-chars-min` في `src/config.py:16`) — أي أن أي
دخلاء يقرؤون الريبو يعرفون سرّ التشفير (توقيع JWT + usertokens + تشفير + salt).

**الوضع الحالي:** `validate_security()` (`src/config.py:95-99`) يكتفي بـ `print` في وضع
الإنتاج — أي إقلاع صامت بسرّ افتراضي.

**الإصلاح المعتمد:**
- في `APP_ENV=production`، إذا كان `SECRET_KEY` هو الافتراضي (أو قصير/بدون سر) → **رفع
  RuntimeError يمنع الإقلاع** (نمط الرفع المستخدم في `supabase_client.py:99-101`).
- بيئات dev/test تبقى متسامحة (لا رفع) حتى لا تُكسر الاختبارات الـ397 المحلية.

**تحقّق:** مصدر أصلي — `src/config.py:16,95-105`.

---

## 🟠 2) خصم الكوبون يُعرض لكن لا يصل إلى Polar

**وصف الداء:** عند الدفع يعرض الاقتباس (`quote`) خصم الكوبون، لكن كود Polar يرسل
`discount_id = None` دائمًا — أي يدفع العميل السعر الكامل بينما يُعرض خصم.

**أسباب مُتحقَّق منها:**
- `src/payments/polar.py:92-93`:
  `if quote.get("coupon_discount_usd"): payload["discount_id"] = quote.get("coupon_polar_id")`
  — والمفتاح `coupon_polar_id` غير موجود أصلًا في مخرجات `quote()`.
- `src/modules/billing/services.py:401-432`: `quote()` يُخرج `total_usd` و
  `coupon_discount_usd` فقط، بلا `coupon_polar_id`.
- جدول `coupons` (ميجريشن 009) لا يحتوي عمود `polar_discount_id` إطلاقًا.

**الإصلاح المعتمد (إما/أو):**
- **أ)** ربط حقيقي: ميجريشن `024` يضيف `coupons.polar_discount_id`، و`quote()` يُخرج
  `coupon_polar_id` منه، وPolar يمرّره فقط عندما يكون حقيقيًّا، مع إرسال `total_usd` في
  metadata.
- **ب)** تعطيل صريح: لا يُظهر الخصم حتى يُربط الكوبون بمعرّف Polar حقيقي.

**الاختيار:** الأسلوب (أ) + fail-closed عند الدفع: إن استُخدم كوبون بخصم موثّق دون
`polar_discount_id` → الخطأ يُرفع بوضوح بدل الدفع الكامل صامتًا.

---

## 🟠 3) تجاوز العزل متعدد المستأجرين في سجل المراجعة

**وصف الداء:** في `src/identity/review_queue.py`:
- `approve_match` يتحقق من ملكية **الرئيسي فقط** (سطر 69-73)، ثم يكتب تحديثًا على
  **المرشح** (سطر 83-87) دون أي تحقق من ملكيته — أي أن مشرفًا يستطيع ربط lead من
  مستأجر آخر عبر طابور آيل.
- `reject_match` كذلك يتحقق من الرئيسي فقط.

**الإصلاح المعتمد:** قبل أي كتابة، التثبت من ملكية **كلا السجلين** (primary + candidate)
لنفس `user_id` حين يُمرَّر (مع رفض القيود بلا مالك يحمي من الربط العشوائي).

---

## 🟠 4) ادعاءات WhatsApp وهمية على الواجهة

**وصف الداء:** الواجهات تُعلن دعم WhatsApp بدون وجود تكامل حقيقي.

**المواضع المُتحقَّق منها:**
- `src/templates/landing.html:7` (meta description)، `:676` (hero subtitle)، `:694`
  (أيقونة في صف التكاملات)، `:766` ("Instagram, Facebook Page, or WhatsApp")، `:797`
  ("Instagram, WhatsApp, and Messenger").
- `src/templates/static/i18n.js`: مفاتيح en `210/233/245/314-315`
  (`onboard.platform_wa_title/desc`) / `332` (`inbox.filter_wa`) / `396`
  (`leads.filter_whatsapp`) + المقابلة بـ ar `1238-1239/1256/1320`.
- `src/templates/onboarding.html:639-646`: بلاطة المنصة "WhatsApp Cloud (Upcoming)".

**الإصلاح المعتمد:** حذف هذه الادعاءات من الواجهات الثلاث (بأمر المالك: "احذف WhatsApp
لحد ما ييجي وقته بعدين"). تُترك العناصر الداخلية غير الواجهية (أيقونات/مفاتيح برمجية)
لعدم كونها ادعاءات.

---

## 🟡 5) غياب هيدرات الأمان في كل الاستجابة

**وصف الداء:** لا يوجد أي من هيدرات الأمان في `src` (بحث شامل بلا تطابق):
`X-Frame-Options`, `Content-Security-Policy`, `X-Content-Type-Options`,
`Referrer-Policy`. الكفيل الوحيد لـ Strict-Transport-Security هو طبقة Vercel فقط.

**الإصلاح المعتمد:** وسيط مركزي في `src/main.py` (بعد وسائط المصادقة/الحارس الترتيبيًا
ليكون الأبعد، فيحيط بكل الاستجابات بما فيها 401/403/404):
- `X-Frame-Options: DENY` + `X-Content-Type-Options: nosniff` +
  `Referrer-Policy: strict-origin-when-cross-origin`
- CSP عملي لا يكسر التطبيق (inline scripts مكثفة + Supabase/Meta/CDN): script-src 'self'
  'unsafe-inline' https://cdn.jsdelivr.net، style-src 'self' 'unsafe-inline'،
  img-src 'self' data: https:، connect-src 'self' + https://*.supabase.co +
  https://graph.facebook.com + https://*.fbcdn.net + https://graph.threads.net +
  https://*.threads.net + https://*.posthog.com + Polar domains، frame-ancestors 'none'.
- فحص Origin على الطلبات التحويلية (POST/PUT/PATCH/DELETE): حين تُرسل المتصفحات Origin
  يجب أن يطابق الـ Host (أو ضمن قائمة بيضاء) وإلا 403 — حماية CSRF فوق SameSite=Lax
  دون كسر OAuth/Webhooks (المسارات العامة مستثناة والطلبات بلا Origin تبقى مقبولة).
- HSTS في الإنتاج فقط.

---

## 🟡 6) kb_documents_loaded صفر دائمًا في الإنتاج

**وصف الداء:** `/health` يُخرج `kb_documents_loaded = len(knowledge_base.knowledge_cache)`
(`src/modules/health/routes.py:39`) — وفي وضع قاعدة البيانات الكاشف فارغ عن قصد، فيظهر
صفر حتّى مع وجود مستندات حقيقية (مضلّل للفحوص).

**الإصلاح المعتمد:** عند اتصال Supabase يُقرأ العدّ الفعلي من جدول `kb_documents`
(عبر طريقة `count()` جديدة على `supabase_db`)، ويبقى عدّ ملفات الكاش في وضع التطوير.

---

## 🟡 ملاحظة (خارج نطاق الإصلاح الستة)

- `APP_DEBUG: bool = True` افتراضيًا (`src/config.py:12`) — تحذير كتابي فقط عند
  `APP_ENV=production` (لا رفع حتى لا نوقف الإقلاع على متغير تشغيل غير حرج).

## ✅ سليم (لا حاجة لتغيير)

- بوابات AI كلها من خلف مشرف (مسارات `/api/admin/*`).
- SameSite=Lax على الكوكيز + فحص الـ Origin ملازم للمصادقة.
- مفتاح الختام: تطبيق TheFixes بالترتيب أعلاه ثم `python -m pytest tests`
  (المتوقع 397+ ناجحًا) — أي فشل خارج التوقّع = توقف للاستشارة لا تجاوز.