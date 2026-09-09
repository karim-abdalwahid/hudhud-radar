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
