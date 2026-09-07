# [023] سجل حادثة التلوث العابر للمشاريع والاستعادة الكاملة (Cross-Project Incident & Restoration)
- **التاريخ**: 2026-09-07 15:00 (UTC+3)
- **الوكيل**: opencode (GLM)
- **الحالة**: استُعيد كل شيء ✓ — قواعد دائمة مفعلة

---

## 1. ما حدث بصراحة
أثناء التحقيق في لغز دومين `hudhud-radar.vercel.app`، ربط الوكيل الـ CLI مؤقتاً بالمشروع القديم `hudhud` لفحص aliases الخاصة به، ثم نُفذ `vercel --prod` والرابط ما زال على القديم → **كود المشروع الحالي نُشر على المشروع القديم** وسطفت عنه اثنين من aliases الإنتاج الأصلية.

## 2. الأثر
| المشروع | الأثر |
|---|---|
| القديم (hudhud) | نشر إنتاج واحد دخيل + amber alias سقط 404 فترة + alias مسروق — **لا لمسات env ولا كود/ريبو** |
| الحالي (hudhud-radar) | steel alias أزيل ثم عاد تلقائياً بإعادة النشر — مزامنة الـ env كانت نظيفة 23/23 |

## 3. الاستعادة (متحقق منها حياً)
1. `hudhud-amber.vercel.app` → أُعيد توجيهه للنشر الأصلي `bqh9p37as` (54 يوم) ✓
2. `hudhud-karim-abdalwahids-projects.vercel.app` → أُعيد لـ `bqh9p37as` ✓
3. النشر الدخيل `hudhud-4hnti1orw` → **حُذف نهائياً** (404) ✓
4. التحقق الحي: amber يخدم التطبيق القديم ("هدهد · نشر إنستغرام" مع /login الخاص به) — مطابق لما قبل الحادثة ✓
5. الحالي سليم: steel يخدم آخر إصدار (marker v2-threads-setup، threads/cron ✓، 33 brains)

## 4. السبب الجذري
رابط الـ CLI (vercel/project.json) خاص بالمجلد وتم تبديله مؤقتاً أثناء الفحص، ثم أمر نشر لاحق استخدمه.

## 5. قواعد أمان دائمة (ملزمة لكل الوكلاء القادمين)
- **R1**: ممنوع `vercel link --project <آخر>` أو تبديل المشاريع مهما كان السبب — إن لزم فحص مشروع آخر: اطلب من المالك خطوات للوحة ونفّذها هو بنفسه
- **R2**: قبل كل `vercel --prod` تحقق: `vercel project ls` يطابق hudhud-radar → hudhud-radar-steel + `vercel whoami` = karimabdalwahid1w-7747، وإلا توقف
- **R3**: ممنوع alias rm/set وenv rm/add وdeployments remove وdomains إلا بموافقة صريحة من المالك على العملية نفسها في نفس المحادثة
- **R4**: المشروع القديم `hudhud` (hudhud-amber.vercel.app) **محظور تماماً** — تابع لحساب/سياق منفصل بحسب المالك
- **R5**: المشروع الوحيد لهذا الكودبيس: hudhud-radar (prj_yxGld…، فريق karim-abdalwahids-projects، الدومين الهدف: hudhud-radar.vercel.app — محتجز حالياً بنطاق المالك الشخصي وهو يعالجه من اللوحة)
- **R6**: مجلد العمل حصرياً C:\Users\Dell\Desktop\OpenCodeProjects\hudhud-radar — أي مشروع آخر على الجهاز للتعلم فقط، ممنوع تعديله

## 6. المتبقي على المالك (لوحة Vercel — دقيقتان)
دومين `hudhud-radar.vercel.app` محتجز بمشروع مكرر قديم في النطاق الشخصي (يخدم نسخة قديمة بلا متغيرات بيئة):
1. vercel.com → بدّل الـ scope من أعلى اليسار إلى الحساب الشخصي
2. مشروع hudhud-radar القديم → Settings → Delete (أو Domains → Remove)
3. ارجع لفريق Karim Abdalwahid's projects → مشروع hudhud-radar → Settings → Domains → Add → `hudhud-radar.vercel.app`
4. بعدها الدومين يخدم آخر نشر تلقائياً
