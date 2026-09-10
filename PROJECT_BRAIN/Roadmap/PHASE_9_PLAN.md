# 🚀 Phase 9 — Multi-Tenant Accounts Platform (خطة تنفيذ كاملة)

> **الحالة**: خطة للمراجعة — لا كود قبل موافقة المالك
> **الهدف**: كل مستخدم يربط حساباته بضغطة زر (أيقونات فيس/انستا/ثريدز) — وبياناته معزولة تماماً
> **المتطلبات القانونية**: ✅ Tech Provider Verified (Entry 036) · Meta App Review submissions متبقية (Advanced Access)
> **الأساس الجاهز**: Platform Adapters + Module Registry + RLS جاهزة للتوسع + users.plan/ai_credits

---

## 🏛️ 1. المعمارية المستهدفة

```
قبل (legacy — أُزيل بالتطهير):  حسابات عامة واحدة في app_settings (توكن المالك)
بعد  (Phase 9):                 كل مستخدم → اتصالاته هو → بياناته هو
```

### الجداول الجديدة
| الجدول | الأعمدة الأساسية | الغرض |
|---|---|---|
| `platform_connections` | id, user_id, platform, account_name, account_id, access_token, token_expires_at, metadata, status, connected_at | توكنات كل مستخدم لكل منصة (مشفرة) |
| `usage_events` | id, user_id, kind (ai_reply/ai_generate/...), amount, created_at | عداد الاستهلاك للـ credits |

### تعديلات على الجداول الحالية
| الجدول | التعديل |
|---|---|
| `leads` / `messages` | + `user_id` (المالك) — العزل |
| `automations_workflows` (app_settings → جدول) | + user_id |
| `site_traffic` / `notifications` | موجودة بالفعل بـ user_id ✓ |

### RLS: كل جدول عمليات = `USING (auth.role() = 'service_role')` داخلياً + الفلترة بـ user_id في طبقة الخدمة (النمط الحالي للمنصة).

---

## 🔌 2. تدفق الربط (One-Click Connect)

```
لوحة المستخدم → أيقونات [📘 Facebook] [📸 Instagram] [🧵 Threads]
→ POST /api/connections/{platform}/authorize (يبني OAuth URL بحالة CSRF خاصة بالمستخدم)
→ موافقة المستخدم على حسابه هو في Meta/Threads
→ Callback → حفظ التوكن في platform_connections (للمستخدم هو)
→ Dashboard يعرض: "متصل باسم @username — تجديد/فصل"
```

- **Meta**: تدفق إذن Pages + Instagram (نفس تطبيق المنصة — Tech Provider verified يسمح لعملاء آخرين)
- **Threads**: موجود أصلاً (threads_oauth) — يُعمم لكل مستخدم
- **الفصل**: حذف التوكن + إلغاء الاشتراك في الويب هوك

---

## 🧠 3. الـ AI Agent لكل مستخدم

- **قاعدة المعرفة**: بالفعل `kb_documents` تدعم `user_id` — تتعمم: كل مستخدم له مستنداته
- **الـ Persona/الإعدادات**: `user_settings` (جدول جديد أو أعمدة) — الـ tone/role لكل مستخدم
- **الردود**: conversation_engine يقرأ معرفة المستخدم المتصل فقط

---

## 💰 4. الاشتراكات (v1 يدوية → v2 بوابة دفع)

- **v1**: المالك يعيّن الخطة يدوياً (موجود: /users → Plan) — `trial_ends_at` عند التسجيل (14 يوم — يحقق وعد الـ landing)
- **v1.5**: Paymob/Stripe Checkout صفحة دفع بسيطة → Webhook يؤكد تلقائياً
- **الاستهلاك**: أفعال AI فقط (اتفقنا) — `usage_events` يخصم من `ai_credits`

---

## 📅 5. مراحل التنفيذ (كل مرحلة commit + اختبارات)

| # | المرحلة | المحتوى | الاختبارات |
|---|---|---|---|
| **9.1** | الأساس | migrations (platform_connections + usage_events + user_id columns) + ConnectionService + endpoints (authorize/callback/disconnect/status لكل منصة عبر Adapters) | ~15 |
| **9.2** | واجهة الربط | أيقونات السوشيال في الإعدادات/Onboarding + حالات متصل/غير متصل | ~8 |
| **9.3** | عزل البيانات | user_id على leads/messages/automations + فلترة كل الـ APIs + هجرة البيانات الحالية (فارغة بعد التطهير — سهلة) | ~10 |
| **9.4** | AI لكل مستخدم | conversation/content يقرأ معرفة + persona المستخدم + عدّاد credits + قوالب trial_ending/credits_low | ~10 |
| **9.5** | الاشتراكات v1 | trial_ends_at + تفعيل يدوي من /users + إشعارات التجربة | ~6 |
| **9.6** | ميتا App Review | بعد المالك يقدم: تفعيل Advanced Access للصلاحيات | owner |

---

## ⚠️ 6. قرارات مطلوبة من المالك (قبل 9.1)

1. **Meta App Review**: مقدم بالفعل أم لسه؟ (Advanced Access مطلوب لتشغيل عملاء آخرين — الدليل جاهز في `META_APP_REVIEW_GUIDE.md`)
2. **تجربة 14 يوم**: هل التسجيل الجديد يبدأ بـ trial تلقائياً (مفعّل كامل) أم plan=free محدود؟
3. **حدود الـ credits لكل خطة**: اقتراحي — free: 100/شهر، starter: 1,000، growth: 5,000، scale: 25,000 — موافق؟
4. **حساباتك الحالية**: تظل غير مربوطة لحد ما تعمل يوزر جديد وتربطها بنفسك (زي ما قلت) — تأكيد؟

---

# 🧩 Wave 9.7 — platform_connections (استكمال 9.1 المؤجلة)
> **أُضيفت**: 2026-09-10 · **الحالة**: ✅ **منفذة ومعتمدة من المالك** (2026-09-10) — migration 011 مطبقة حية، 244/244 اختبار
> **السياق**: موجة 9.1 الأصلية اتحولت لأساس الفوترة (migration 009) واتأجّل جزء الاتصالات — الاتصالات لسه Global قديم. التدقيق الحي 2026-09-10: **24 جدول حي، `platform_connections` غير موجود، `app_settings` نظيف تماماً (صفر توكنات) → القطع النظيف مجاني بلا هجرة بيانات**.

## 7.1 القاعدة التجارية الذهبية (Entitlement ≠ Capability)
- التوكن التقني قد يلمس منصات أكثر مما دفع العميل فيه (مثال: توكن صفحة فيسبوك يصل للـ IG المربوط بها).
- **الفحص server-side على كل عملية حساسة = `user_entitlements` فقط، fail-closed** (403) — لا علاقة لقدرة التوكن بالسماح.
- الاكتشاف المجاني (IG مربوط بصفحة عميل اشترى FB فقط) = metadata upsell مقفولة الواجهة + CTA ترقية بخصم المنصات المتعددة — **عامل بيع مش تسريب**.

## 7.2 أبواب الربط الثلاثة (حسب ما اشتراه العميل — الـ wizard يقرا entitlements)
| الباب | التدفق | يغطي |
|---|---|---|
| 📘 Facebook | Facebook Login (scopes: pages_show_list + messaging + pages_utility_messaging...) → توكن الصفحة | FB + الـ IG المربوط بالصفحة ( عبر FB-based IG APIs) |
| 📸 Instagram | Instagram Login (التطبيق الابن IG_APP_ID — scopes: instagram_business_*) → graph.instagram.com | IG-only بدون فيسبوك خالص |
| 🧵 Threads | threads.net OAuth (موجود — يُعمم لكل مستخدم) | Threads |

- الـ wizard يقترح باب فيسبوك أولاً لمن عنده صفحة (يجيب الاتنين بضغطة) ويسيب باب IG-only لمن لا يملك/يحب فيسبوك.
- كل باب يخزن اتصاله الخاص: platform = facebook / instagram / threads.

## 7.3 Migration 011 — `platform_connections`
| العمود | النوع | الغرض |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK→users ON DELETE CASCADE | المالك |
| platform | TEXT (facebook/instagram/threads) | الباب |
| account_id / account_name | TEXT | معرف الحسل المتصل باسمه |
| access_token_encrypted | TEXT | **مشفر** (Fernet مشتق من SECRET_KEY — إضافة وحدة تشفير صغيرة لـ src/core) |
| token_expires_at | TIMESTAMPTZ NULL | للتوكنات المؤقتة |
| scopes | TEXT[] | الممنوحة فعلياً |
| metadata | JSONB | linked_ig_id / page_id / discovery (المرشح للـ upsell) |
| status | TEXT (active/revoked/expired) | |
| connected_at / created_at / updated_at | TIMESTAMPTZ | قاعدة SOP-03 + trigger updated_at |
- UNIQUE(user_id, platform, account_id) · فهرس user_id · RLS بنمط المنصة الموثق (منع anon، الفلترة بـ user_id في طبقة الخدمة) · REVOKE من anon.

## 7.4 ConnectionService (src/connections/)
- `store(user_id, platform, ...)` (تشفير شفاف) · `get_active_token(user_id, platform)` (فك شفاف) · `revoke(user_id, platform)` · `list(user_id)`.
- استبدال كامل لمسار app_settings القديم (meta_credentials/threads_credentials يُحذف كوده بعد القطع — لا fallback: السحابة نظيفة أصلاً).
- callbacks الموجودة (/api/meta/configure، threads callback) تُحوَّل تخزن للاتصال لكل مستخدم + deauthorize/uninstall callbacks تُلغي اتصال المستخدم.

## 7.5 الـ Feature Gate
- طبقة رقيقة فوق ConnectionService: `assert_entitled(user_id, platform)` — يقرا user_entitlements (موجودة من 009) وترفض fail-closed قبل أي Graph call.
- توكل على: publishing / inbox replies / insights / automations لكل منصة.

## 7.6 الاختبارات (~15)
نماذج Pydantic · تشفير/فك دوري · عزل user-to-user (403/empty) · gate: بدون entitlement → 403 · gate: مع entitlement → 200 (mock Graph) · callbacks تخزن/تلغي لكل مستخدم · wizard branches حسب entitlements.

## 7.7 تسلسل التنفيذ
1. migration 011 + تحديث database/schema.sql + [[Supabase_Database_Schema]] (SOP-03)
2. وحدة التشفير + ConnectionService + اختباراتها
3. تحويل الـ callbacks الثلاثة + deauthorize لكل مستخدم
4. Feature gate على الـ APIs الحساسة
5. Wizard: تفرع الأبواب + حالة الـ upsell المقفول
6. حذف مسار app_settings القديم + تحديث التوثيق (SOP-01 خطوة 6: Memory + Brain + Activity Log)

---

# ⏭️ Wave 9.8 — خدمات الوكيل لكل مستخدم (القطع النهائي) — مسجلة، غير منفذة
> **أُضيفت**: 2026-09-10 · **الحالة**: مخططة — بانتظار موافقة المالك

1. **إعادة توصيل الخدمات الخلفية** (agent orchestrator / webhook processing / meta_feed_sync / insights cron) لتقرا توكن المستخدم من `platform_connections` عبر ConnectionService بدل `settings.META_*` العام — رد الوكيل يعالج محادثات كل مستخدم متصل بتوكنه هو.
2. **مستقبل Threads Webhook حقيقي** (مؤجل من 2026-09-10 — الاشتراك متاح في لوحة ميتا ولم يُفعَّل عمدًا): endpoint يستقبل أحداث threads.net (الموضوع: `Moderate` — أحداث الردود) + تحقق توقيع بتوكن التطبيق المخصص → الوكيل يرد لحظيًا على ردود Threads بدل الـ polling. لا يُفعَّل من لوحة ميتا قبل وجود المستقبل (اشتراك ميت).
3. **إزالة مسار app_settings القديم كليًا**: meta_credentials/threads_credentials + get_active_threads_token shim (حاليًا shim جسر مؤقت موثق).
4. **لوحة الإعدادات**: بلوك الاتصالات في /settings (نفس عارض الـ wizard: الأبواب الثلاثة + upsell) — الـ wizard كامل في 9.7.
5. **تحديث تلقائي للتوكنات**: cron refresh لتوكنات instagram/threads (60 يوم) قبل انتهائها.
6. **Embedded Signup / Tech Provider flow**: تسليم OAuth عبر تطبيق المنصة لعملاء العملاء (لما يُفعَّل Advanced Access بعد App Review).
