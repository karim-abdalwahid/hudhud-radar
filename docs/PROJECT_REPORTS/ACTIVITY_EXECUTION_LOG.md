# 📊 سجل العمليات والأنشطة المنفذة (Activity & Execution Log)
#activity-log #operations #audit

توثيق دائم لجميع العمليات والأنشطة التي ينفذها نظام **HudhudRadar**.

---

| التوقيت (UTC) | نوع العملية (Action) | المنصة (Platform) | الهدف (Target) | الحالة (Status) | سبب الفشل / ملاحظات |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-09-03 19:25:00 | Project_Init | System | HudhudRadar | SUCCESS | تم إنشاء البنية التحتية، عقل المشروع، وسجل الذاكرة |

---

---

---

## 2026-09-10 — Wave 9.7: platform_connections (اتصالات لكل مستخدم بتوكنات مشفرة)
- Migration 011 طبقت حيًا: جدول platform_connections + تشفير Fernet + RLS بنمط المنصة.
- ConnectionService + بوابات entitlement (fail-closed 403) + مسارات /api/connections/* (أبواب FB/IG/Threads).
- خطوة 3 في الـ wizard: نوافذ OAuth بدل لصق التوكن + بطاقات upsell مقفولة (اكتشاف IG لاشتراك FB فقط).
- إجراءات Inbox/Threads محكومة لكل مستخدم؛ deauthorize/uninstall يلغي اتصالات المستخدم المعني.
- الاختبارات 244/244 (19 جديدة). الموجة 9.8 (إعادة توصيل الخدمات) مسجلة في PHASE_9_PLAN.md.

## 2026-09-10 (تكملة) — Phase 9.6: تحليلات المنتج (PostHog) toggle-gated — البنية التحتية
- GET /api/analytics/config: يرجع الإعداد فقط عند تفعيل المالك — معطل افتراضيًا (خصوصية أولًا).
- إعدادات الأدمن: analytics_config {enabled, posthog_key, posthog_host}.
- محمّل saas.js المشترك: posthog-js من CDN عند التفعيل، autocapture مغلق، أحداث صريحة فقط (hudhudTrack).
- onboarding.html: تتبع onboarding_completed عند إطلاق الوكيل.
- سياسة الخصوصية (عربي/إنجليزي): بند PostHog — استضافة أوروبية، تسجيل جلسات مجهول مع إخفاء الحقول، إلغاء اختياري.
