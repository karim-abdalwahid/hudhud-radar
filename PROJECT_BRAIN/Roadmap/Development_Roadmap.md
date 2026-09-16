# 🗺️ Development Roadmap — HudhudRadar (v2)
> **هذه النسخة الرسمية الوحيدة** — استبدلت نسخة v1 (تالفة الترميز). التفاصيل التاريخية الكاملة في `PROJECT_MEMORY.md` (Entry 001 → 028) وأرشيف `PROJECT_ARCHIVE/`.
> آخر تحديث: 2026-09-07

---

## المرحلة 1: التأسيس والبنية التحتية ✅ 100%
- [x] Obsidian Project Brain + PROJECT_MEMORY (قواعد حوكمة append-only)
- [x] SOPs 01-06 | مخطط Supabase كامل (RLS + FK + JSONB provenance)
- [x] باكند FastAPI معياري: identity/leads/meta_api/agent/analytics/reporting
- [x] عميل Meta Graph مع Rate Limiting + HMAC webhook parsing
- [x] Two-Pass Audits (Pass 1 + Pass 2)

## المرحلة 2: المعرفة والهوية ✅ 100%
- [x] Zero-Assumption Identity Resolution + Human Review Queue
- [x] قاعدة معرفة RAG/pgvector (hybrid search: cosine + tsvector + RRF) — migration 003
- [x] المحلل البنيوي للمنشورات (Entry 021 Phase 5 — تصنيف CTA vs نية حقيقية، مرجعيات إلزامية)

## المرحلة 3: الواجهات والاستوديو ✅ 100%
- [x] Content Studio + Gemini content engine + Compliance checker
- [x] مجدول نشر (container flow) + publish-now
- [x] Live Inbox حقيقي (رسائل فعلية من قاعدة البيانات — صفر فبركة)
- [x] Automations visual builder (comment-to-DM workflows)

## المرحلة 4: Roadmap v2 (Entry 021) ✅ 8/8 مكتملة
- [x] **P1** Login/Auth UX (SendRad-style + i18n AR/EN)
- [x] **P2** Supabase audit + إصلاحات RLS الحرجة + indexes
- [x] **P3** Test users + مصفوفة صلاحيات (58/58 حي)
- [x] **P4** Google OAuth — **مباشر من الباكند** (شاشة الموافقة تعرض دوميننا) — Entry 028
- [x] **P5** RAG/pgvector migration + حذف المعرفة المفبركة + meta analyzer
- [x] **P6** حزمة App Review جاهزة (`META_APP_REVIEW_GUIDE.md`) — ⏳ التقديم على المالك
- [x] **P7** تنبيهات النظام للأدمن (6 فحوصات + كاش مشترك Supabase)
- [x] **P8** AI Providers (اكتشاف تلقائي، أدمغة لكل عميل، مفاتيح masked)

## المرحلة 5: التصلين والتوثيق ✅ 100% (سبتمبر 2026)
- [x] **Entry 026** — أمان: data-deletion موقّع إلزاماً، cron fail-closed، webhook HMAC صارم، admin gates شاملة
- [x] **Entry 026** — Zero-Fabrication: إلغاء المحاكاة والفبركة في كل المسارات، فشل صادق
- [x] **Entry 026** — توحيد الدومين: `APP_BASE_URL` مصدر وحيد + `DOMAIN_SWAP_RUNBOOK.md`
- [x] **Entry 027** — مسح واجهات شامل: صفر personae/KPIs وهمية + Guard tests دائمة
- [x] **Entry 028** — Google مباشر + إزالة secrets مسربة من 4 سكربتات
- [x] حوكمة دائمة: قواعد R1-R12 في PROJECT_MEMORY

## المرحلة 6: Phase 9 — الحسابات المتعددة (SaaS) ⏳ **التالية**
الموافقة مسجلة (Entry 026 §5). النطاق:
- [ ] ربط OAuth لكل عميل (Facebook/Instagram/Threads) بتوكنات معزولة لكل مستخدم
- [ ] جداول credentials لكل مستخدم + فصل leads/messages/automations بـ user_id + RLS
- [ ] تحويل endpoints للعمل على حساب المستخدم الحالي
- [ ] خطة إعادة استخدام + تسعير (خطة 14 يوم مجاناً موجودة بالفعل في landing)
- [ ] خطة تنفيذ تفصيلية تُراجع مع المالك قبل الكود

## ⚠️ قيد التشغيل من المالك (عمليات لوحة تحكم فقط)
| # | المهمة | المرجع |
|---|---|---|
| 1 | Gemini: تفعيل الفوترة أو الانتظار (الحد المجاني 20 طلب/دقيقة) | Entry 029 |
| 2 | Rotate: Google Client Secret + Supabase Management Token (كانوا في git) | Entry 028 |
| 3 | Google consent screen → In Production | Entry 028 |
| 4 | تقديم Meta App Review (P6) | `META_APP_REVIEW_GUIDE.md` |
| 5 | قرار تقاعد النطاق الاحتياطي (steel) | Entry 024 §4 |

## 🧹 ديون تقنية منخفضة (موثقة، غير حرجة)
- rate-limiting عام على كل APIs (حالياً auth فقط) | CSRF tokens (SameSite=Lax كافٍ حالياً)
- logout stateless (token ينتهي طبيعياً) | threads auto-refresh cron
- IG insights #10 scope (fallback فعال) | `semantic_engine` dead code (نموذج قديم)

## 🔒 قواعد ملزمة (الملخص — النص الكامل في PROJECT_MEMORY)
R1-R6 عمليات Vercel | R7-R8 نشر/env على النطاقين | R9 الدومين من APP_BASE_URL فقط | R10 Zero-Fabrication مطلق | R11 ممنوع وهمي في الواجهات (Guard tests) | R12 أي بلاغ = مسح كامل لنوعه

---

## تحديث حالة التنفيذ — 2026-09-16

المرحلة السادسة لم تعد "التالية" بكاملها. اكتملت قاعدة Phase 9 متعددة
المستأجرين: اتصالات مشفرة لكل عميل، entitlement gates، فصل بيانات CRM/RAG/
content/automations/analytics، وتحـصين Data API، مع migration حي واختبارات
`320 passed, 2 skipped`. التفاصيل والحالة الجزئية في [[PHASE_9_PLAN]].

- **مكتمل:** 9.1، 9.2، 9.3 والجزء البنيوي من Wave 9.8.
- **جزئي:** 9.4 (credit usage/provider integration/persona) و9.5 (أساس
  الاشتراكات موجود؛ الاستهلاك الآلي يحتاج إكمال).
- **خارجي:** Meta App Review قُدم في 2026-09-12؛ لا يدعي هذا المستند موافقة
  لم تثبت من لوحة Meta.
- **المسار التالي:** تدوير tokens القديمة → اختبار مستأجرين حي → إكمال 9.4.
  Wave 9.9 وPhase 10 يبقيان backlog لا تنفذ تلقائياً.
