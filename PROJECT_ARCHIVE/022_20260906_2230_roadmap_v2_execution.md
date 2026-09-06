# [022] دليل إنجاز خارطة الطريق v2 — المراحل المنفذة (Roadmap v2 Execution Walkthrough)
- **التاريخ**: 2026-09-06 22:30 (UTC+3)
- **الوكيل المنفذ**: opencode (GLM)
- **الحالة**: 7 من 8 مراحل لايف — Google OAuth بانتظار OAuth Client من المالك

---

## 1. المرحلة 1 — صفحة الدخول SendRad ✓ لايف
- لوحة عرض متحركة: محاكاة شات كاملة (عميل يسأل عن السعر → هدهد يرد خلال 3.2 ثانية → موعد محجوز) + عدادات نابضة + خلفية orbs
- **اللوجو الموحد `hudhud.`**: على auth + الشريط الجانبي + الـ 9 صفحات (فحص آلي: صفر بقايا)
- اختيار دولة: 120+ دولة مع أعلام، بحث بالاسم (عربي/إنجليزي) أو بكود الهاتف، حفظ دولي كامل
- i18n حقيقي AR/EN (حتى سكريبت الأنيميشن يتبدل)

## 2. المرحلة 2 — تدقيق Supabase الحية ✓
**🔥 الثغرة الحرجة**: anon كان يملك DML كامل على كل جداول البزنس — أي شخص بالمفتاح العام يستطيع حذف كل شيء!
**الإصلاح (migration 002)**: REVOKE ALL FROM anon ×10 جداول + الـ schema — تحقق: صفر بقايا
**إضافات**: تفعيل pgvector + 3 فهارس أداء + ERD Mermaid في PROJECT_BRAIN/Schemas/LIVE_DATABASE_AUDIT.md

## 3. المرحلة 3 — اليوزرين + مصفوفة 49/49 ✓
| الحساب | كلمة المرور | الدور |
|---|---|---|
| admin.test@hudhud.test | AdminTest#2026 | admin |
| user.test@hudhud.test | UserTest#2026 | user |
| karim@ebdamarketing.com | (الأصلي) | admin المالك |

المصفوفة الحية: مجهول 9 ✓ + أدمن 28 ✓ + مستخدم 16 ✓ (بما فيها محاولات تجاوز) = **49/49**

## 4. توكن Meta — إحياء كامل ✓
- توكن جديد (30 صلاحية) → تبادل دائم (EXPIRES=0) → .env + Vercel + ويب هوك ✓
- إصلاحات Insights: أسماء v26 (page_views_total...) + IG fallback + upsert (on_conflict platform,metric_date)
- **نتيجة حية**: 7 أيام بيانات فيسبوك + 32 متابع إنستجرام — تقارير الأداء تتغذى الآن تلقائياً عبر cron اليومي

## 5. المرحلة 5 — RAG pgvector ✓ لايف (بدل LEANN المرفوض بعد دراسة كاملة)
- migrations 003/003b/003c: kb_documents + kb_chunks (vector(3072) + tsv) + RPC match_kb_chunks (RRF)
- **اكتشاف**: text-embedding-004 متقاعد → gemini-embedding-001 (3072 بعد)
- DBKnowledgeBase: chunking ذكي + embedding + بحث هجين + fallbacks
- KnowledgeBaseManager ثنائي الوضع: DB أساسي (يحل read-only نهائياً) / ملفات للاختبارات
- **حذف المعرفة الوهمية** من git والقرص + .gitignore
- بذر business_profile.md حقيقي بمتجهات — بحث هجين مختبر حياً ✓

## 6. المرحلة 7 — تنبيهات الأدمن ✓ لايف
`/api/admin/alerts` + بانل ملوّن في اللوحة: توكن Meta (يكشف إبطال تغيير كلمة المرور!)، Threads <14 يوم، Gemini 429، الويب هوك، السكيدولر، Supabase — **حية**: 5 ok + 1 info

## 7. المرحلة 8 — AI Providers أسلوب opencode ✓ لايف
- migration 004: ai_providers + ai_models + users.agent_brain
- سجل رسمي: Google AI / Anthropic / OpenAI / OpenRouter (لوجو SVG لكل واحد)
- **اكتشاف تلقائي**: Google مربوط بمفتاح المالك → **33 موديل اكتُشفت فوراً** (متاح فقط لصلاحياته)
- Custom OpenAI-compatible: Base URL + API key اختياري + +Add model + +Add header
- باب انفتاح الموديلات: enabled+available فقط يظهر للعميل في /api/ai/brains
- المفاتيح مقنّعة (sk-ab…7890) لا تُعاد أبداً
- **2 bugs حقيقية أصلحتها الاختبارات**: قيمة enabled الافتراضية + إتاحة الموديلات عند فشل الاكتشاف
- الاختبارات: 77/77 (7 جديدة للمزودين)

## 8. المتبقي
| البند | الحاجز |
|---|---|
| Phase 4 — Google OAuth | منك: OAuth Client (Google Cloud Console → Credentials → OAuth client ID → Web application → Redirect: `https://yncxwcvxssvnjffrvxib.supabase.co/auth/v1/callback`) → أرسل Client ID + Secret |
| Phase 6 — App Review | الدليل الجاهز: PROJECT_BRAIN/Roadmap/META_APP_REVIEW_GUIDE.md (نصوص تبرير جاهزة للصق + مواصفات فيديو + مسار Testers للبدء فوراً) |
| برومبت محلل البوستات (خارطة 021 §5) | سيُعرض عليك للمراجعة قبل التنفيذ |
