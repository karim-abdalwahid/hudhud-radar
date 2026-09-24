# دليل تنفيذ مواءمة SOPs وProject Brain مع SaaS tenant isolation

- **التاريخ:** 2026-09-16 23:44 +03:00
- **النوع:** Documentation Walkthrough
- **القرار:** المالك وافق على بدء تحديث الوثائق بعد تقرير الفروقات 026.
- **حدود التنفيذ:** توثيق فقط؛ لا تعديل لكود التطبيق، ولا migration، ولا تغيير
  بيانات Supabase أو token أو إعداد إنتاجي.

---

## ما تم تحديثه

### الإجراءات القياسية

- أُلحق `SOP-01` بدورة سجل جلسة حي وذاكرة/مرجع Codex append-only وحدود ملكية
  المستأجر في الميزات الجديدة.
- أُلحق `SOP-03` بمصدر الحقيقة (migrations)، pre/post-flight، قواعد ownership
  وFK cascade-safe، واستثناء السجلات append-only من فرض `updated_at` الأعمى.
- أُلحق `SOP-04` بعقد token المشفر لكل عميل، recipient ownership resolution،
  entitlement، وعدم وجود shared-token fallback.
- أُلحق `SOP-05` بحد منع identity search/merge بين العملاء.
- أُلحق `SOP-07` بالمسار الحالي وبقاعدة عدم حذف/استبدال Memory أو مرجع Codex.
- أُلحق `SOP-08` بملكية المحتوى والنشر/الجدولة باستخدام exact tenant connection.
- بقيت `SOP-09` الأصلية محفوظة كنموذج تاريخي، وأُنشئت `SOP-09 v2` كمرجع
  تشغيلي مستقل للـRAG المعزول.
- أُلحق `SOP-10` بأن snippets المستقبلية global non-secret فقط، مع admin actor
  صريح في audit.

### المعمارية والمخطط والخطة

- أضيف tenant ownership flow إلى System Architecture وData Flow وSecurity Model.
- أُنشئ `SaaS_Tenant_Data_Contract.md` لبيان مصدر الحقيقة، ownership، grants،
  RAG contract، وما هو مكتمل/غير مكتمل فعلاً.
- أُلحق `Supabase_Database_Schema.md` بحالة live migration؛ لا يُعاد تفسير
  `app_settings` كخزن credentials مشتركة.
- أُلحق `PHASE_9_PLAN.md` بمصفوفة حالة صادقة: 9.1–9.3/أغلب 9.8 مكتملة؛ 9.4
  و9.5 جزئية؛ Meta Advanced Access وEmbedded Signup أعمال خارجية معلقة.
- أُلحق Development Roadmap وMeta App Review Guide وAdmin Tools Plan بحالة
  التنفيذ الحالية، وأُضيفت روابط المرجعين الجديدين إلى `00_Index.md`.

## توضيح هام عن `database/schema.sql`

الملف يحتوي ترميزاً تاريخياً غير UTF-8 يمنع تحريره الآمن باستخدام أدوات patch
دون إعادة كتابة bytes قديمة. لذلك لم يُغيّر. هذا ليس تغييراً تشغيلياً مفقوداً:
المصدر التنفيذي للحالة الحية هو migrations، وتم الإعلان عن ذلك صراحة في
`SaaS_Tenant_Data_Contract.md` وملحق SOP-03. لا يُشغّل bootstrap وحده على cloud.

## ما لم يُزعم أنه مكتمل

- لا يوجد استخدام runtime موصول حتى الآن لـ`usage_events` أو خصم `ai_credits`.
- `conversation_engine` لم يُربط بعد بـ`provider_manager` لاختيار provider لكل
  tenant، ولم تحسم persona/settings الدائمة لكل عميل.
- Advanced Access وEmbedded Signup ينتظران Meta؛ refresh يحتاج smoke test بتوكن
  حقيقي؛ Wave 9.9 وPhase 10 لم يبدأا.

## التحقق

- تأكد وجود جميع الملفات والمراجع الجديدة.
- فحص `git diff --check` مر بلا أخطاء. تحذيرات CRLF في Windows فقط.
- لا توجد اختبارات تطبيق لازمة أو مشغلة لأن هذا block وثائقي بحت.

## الخطوة التالية

تدوير tokens التاريخية، التحقق من App Review، ثم smoke test حي لمستأجرين
مصرح بهما. بعد ذلك ينفذ Phase 9.4 بقرار منتج واضح حول provider وcredits/persona.
