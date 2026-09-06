# [017] تقرير التدقيق الشامل وخطة الإصلاح الرئيسية (Master Audit Report & Repair Plan)
- **التاريخ**: 2026-09-06 20:30 (UTC+3)
- **الوكيل المنفذ**: opencode (GLM)
- **الحالة**: معتمدة من المالك — تحت التنفيذ

---

## 1. نطاق التدقيق
تدقيق شامل كامل للمشروع بفحص مباشر للكود المصدري (ليس افتراضات): كل وحدات `src/` (13 حزمة)، الواجهات الـ 12، الإعدادات، قاعدة البيانات، النشر على Vercel، وحالة git.

## 2. نتائج التدقيق (مُتحقَّق منها بالكود)

### الأخطاء الأمنية
| ID | الخطورة | الوصف | الموقع |
|---|---|---|---|
| S1 | حرجة | GitHub PAT بالنص الكامل في git remote URL | `.git/config` |
| S2 | حرجة | META_APP_SECRET مكشوف في Entry 014 بالذاكرة (الريبو خاص — قرار المالك: إبقاء التاريخ مع تدوير السر) | PROJECT_MEMORY.md |
| S3 | حرجة | صفر Authentication — كل الصفحات والـ APIs مكشوفة | src/ كله |
| S4 | عالية | RLS على content_posts USING(true) | database/schema.sql:276 |

### الوظائف المعطلة
| ID | الوظيفة | المشكلة |
|---|---|---|
| B1 | أتمتة platform="both" | الكود يقارن بـ "omnichannel" غير الموجود → لا تُطلق أبداً |
| B2 | Human Takeover | واجهة فقط، لا backend، orchestrator لا يفحصه |
| B3 | Inbox conversations | يقرأ أعمدة غير موجودة في leads (بيانات مفبركة) |
| B4 | الجدولة على Vercel | scheduler معطل + صفر crons |
| B5 | n8n workflow | URL وهمي + trigger_type=webhook بلا مسار تنفيذ |
| B6 | روابط DM الافتراضية | hudhud.ai (دومين غير مملوك) |
| B7 | executions_count | أرقام وهمية hardcode (142/89/34) |
| B8 | تقارير الأداء | record_daily_metrics لا يستدعى أبداً |
| B9 | جدول campaigns | غير مستخدم |
| B10 | Gemini/OpenAI | مفتاح Gemini فارغ + لا يوجد كود OpenAI |
| B11 | Threads/Marketing API | معلنة بلا تنفيذ |
| B12 | WhatsApp tile | ديكور |
| B13 | Publish-now على Vercel | BackgroundTasks قد تُقطع بـ timeout |
| B14 | كتابة الملفات على Vercel | read-only FS — كل تعديلات المستخدم تضيع |

### أخطاء المنطق
1. history لا يُرسل لـ Gemini (بلا ذاكرة محادثة)
2. last_interaction_time=now() دائماً → فحص 24h شكلي
3. identity resolver يختار أول مرشح لا الأعلى ثقة
4. update_from_headers لا يفعل شيئاً فعلياً
5. صفر webhook dedup → ردود مكررة (خطر حظر)
6. الأتمتة تتجاوز rate limiter (أخطر مسار على الحساب)
7. لا retry/backoff على استدعاءات Meta
8. wait_for_container يرجع True عند timeout
9. BOTH: فشل IG لا يفشل العملية
10. app_settings ناقص من schema.sql
11. Python 3.12 (version file) مقابل 3.14 (venv محلي)
12. /api/meta/status يضرب Meta كل 15 ثانية من كل متصفح

### التكرار والقابل للحذف
dashboard.html (يتيم 1057 سطر) • main.py الجذر مقابل src/main.py • /api/studio/posts مكرر • 4 مسارات webhook • منطق اعتمادات Meta مكرر 3 مرات • automations HTTP calls يكرر meta_client • src/scraping/ غير مستخدم • egg-info • uploaded_test.md • ترقيم مكرر في PROJECT_MEMORY • وثيقتا تصميم • نظام CSS منفصل في dashboard.html و landing.html

## 3. قرارات المالك المعتمدة (2026-09-06)
1. تدوير الأسرار: **موافق** — والريبو خاص فتُبقى الذاكرة للسياق الكامل مع تدوير السر نفسه (يُلغي خطر التاريخ)
2. الإنتاج: **Vercel نهائياً** (ميزانية صفر)
3. Threads + Marketing API: **تنفيذ في هذه الدورة**
4. الهوية: **وكيل شخصي الآن** → SaaS عند النجاح
5. الأسعار: تُبقى كمحتوى تسويقي، الدفع الفعلي يؤجل لمرحلة SaaS؛ البيانات التشغيلية المفبركة (executions_count, inbox) **تُحذف**
6. WhatsApp: **حذف من Onboarding** (لا بيزنس موثق) — توثيق: ربط حسابات عملاء خارجيين يتطلب Meta App Review + Advanced Access؛ التوثيق التجاري على ميتا مجاني وغالباً هاتف/إيميل/دومين فقط — يُنفذ عند مرحلة SaaS
7. **المصادقة**: أولوية المالك — صفحات login/register بتصميم sendrad.com **مع إضافة رقم الموبايل** في التسجيل، مربوطة بقاعدة البيانات

## 4. خطة الإصلاح (8 مراحل) — الحالة
| المرحلة | المحتوى | الحالة |
|---|---|---|
| 0 | تدوير الأسرار + إزالة PAT من remote + تنظيف مخلفات الاختبار | 🔄 |
| 1 | Authentication كامل (users table + صفحات دخول + حماية مسارات + أدوار) | ⏳ |
| 2 | إصلاحات النواة (أتمتة، takeover، inbox حقيقي، ذاكرة Gemini، dedup، أعلى ثقة، RLS، app_settings) | ⏳ |
| 3 | Serverless (Supabase persistence، crons، timeout mitigation، Python 3.12) | ⏳ |
| 4 | Gemini 2.5-flash + تنظيف OpenAI/WhatsApp | ⏳ |
| 5 | Insights sync + Threads + Marketing API + Privacy/Data-Deletion | ⏳ |
| 6 | التنظيف الشامل وتوحيد الـ entrypoints والوثائق | ⏳ |
| 7 | CI (pytest + pip-audit) + اختبارات جديدة + SOP-02 Two-Pass + تقرير نهائي | ⏳ |

## 5. ملاحظة معمارية مهمة (SaaS المستقبلي)
طريقة عمل منصات مثل SendRad لربط حسابات العملاء: التطبيق يمر بـ **Meta App Review** للحصول على Advanced Access للصلاحيات. التوثيق التجاري (Business Verification) على ميتا **مجاني** ويتم عادة عبر: تأكيد رقم هاتف العمل + إيميل + التحقق من الدومين — وليس بالضرورة أوراق قانونية. الخطة: بناء المعمارية من الآن بحيث كل توكنات Meta تُخزن **لكل مستخدم** (user_id في app_settings) لجعل التحول لـ SaaS سلساً.
