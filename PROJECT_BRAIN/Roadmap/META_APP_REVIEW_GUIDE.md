# 🚀 دليل Meta App Review — فتح الربط للعملاء الخارجيين
#meta #app-review #saas
*المرحلة 6 من خارطة الطريق v2 — السر وراء قدرة sendrad.com وأمثالها على الربط بضغطة زر*

---

## 1. الحقيقة الكاملة (بدون تجميل)

| السؤال | الجواب |
|---|---|
| هل يمكن لأي عميل ربط حسابه الآن؟ | **لا** — التطبيق في Development Mode: فقط من له دور (Admin/Developer/Tester، حتى ~100 شخص) |
| ما الذي يفتح الربط للعموم؟ | **Meta App Review** للموافقة على Advanced Access لكل صلاحية |
| هل التوثيق التجاري يحتاج أوراق؟ | غالباً **لا**: تأكيد هاتف العمل (كود SMS) + إيميل + التحقق من الدومين (سجل DNS). الأوراق القانونية استثناء |
| التكلفة؟ | **صفر** — كله مجاني |
| المدة؟ | مراجعة الصلاحيات عادة 1-7 أيام لكل دفعة |

## 2. ما أنجزناه بالفعل (متطلبات جاهزة)
✅ Privacy Policy حية: `https://hudhud-radar.vercel.app/privacy`
✅ Data Deletion: صفحة `https://hudhud-radar.vercel.app/data-deletion` + callback API
✅ استبيانات البيانات ستجيب عنها بنفس المعلومات أدناه

## 3. خطوات التوثيق التجاري (Business Verification) — 15 دقيقة
1. business.facebook.com → إعدادات الأعمال → **مركز أمان الأعمال**
2. ابدأ التحقق: أدخل بيانات النشاط (اسم "إبدأ ماركتينج" أو اسمك كصانع أعمال فردي)
3. **تأكيد الهاتف**: كود SMS/اتصال لرقم عملك
4. **تأكيد الإيميل**
5. **التحقق من الدومين**: أضف سجل TXT في إعدادات DNS دومينك (أو ملف HTML في الموقع) — إن لم يكن لديك دومين خاص، الشراء غير ضروري: يمكن التحقق عبر صفحة Facebook Page المرتبطة
6. انتهى — التحقق يكتمل عادة خلال ساعات

## 4. طلبات App Review — الصلاحيات والنصوص الجاهزة

قدّمها على 3 دفعات (الأولوية أولاً). لكل صلاحية: **سبب الاستخدام** (انسخه حرفياً) + **فيديو** (المواصفات في §5).

### الدفعة 1 — الأساس (رسائل + تفاعل)
| الصلاحية | نص التبرير الجاهز (انسخه في خانة Justification) |
|---|---|
| `pages_show_list` | "The user connects their Facebook Page to our AI assistant platform. We list their Pages so they can choose which page to connect during onboarding." |
| `pages_read_engagement` | "We read page engagement metrics (reach, followers) to show the business owner performance analytics in their dashboard." |
| `pages_read_user_content` | "We read comments on the business's own posts and reels to analyze customer questions and enable automated comment responses." |
| `pages_messaging` | "Our AI assistant automatically replies to customer messages received on the connected Page within Meta's 24-hour messaging window, to qualify leads and answer product questions when the business owner is unavailable." |
| `instagram_basic` | "We display the connected Instagram account's profile info and media to the business owner in their dashboard." |

### الدفعة 2 — الإدارة
| الصلاحية | نص التبرير |
|---|---|
| `instagram_manage_messages` | "The AI assistant answers Instagram DMs within the allowed window to capture leads and answer inquiries when the owner is offline." |
| `instagram_manage_comments` | "The platform auto-replies to comments on the business's own posts and can hide spam, per the owner's configured rules." |
| `pages_manage_metadata` | "We subscribe the Page to our webhooks to receive real-time message and comment events for automated replies." |
| `pages_manage_posts` | "The owner schedules and publishes posts/reels through our AI content studio; we publish on their behalf at the scheduled time." |
| `pages_manage_engagement` | "We like and reply to comments on the business's own posts per the owner's automation rules." |
| `instagram_content_publish` | "The owner schedules and publishes Instagram reels/posts through our AI content studio." |

### الدفعة 3 — اختيارية لاحقاً
`instagram_manage_insights` (تحليلات إنستجرام), `leads_retrieval` + `ads_management`/`ads_read` (سحب ليدات الإعلانات), `business_management` (إدارة متقدمة)

## 5. مواصفات فيديو العرض (مطلوب لكل صلاحية — فيديو واحد شامل يكفي)
1. **المدة**: 60-90 ثانية، شاشة كاملة، إنجليزي أو عربي مع تعليق واضح
2. **المشهد 1** (10ث): "أنا مالك النشاط، أسجل دخول لمنصة Hudhud" → شاشة تسجيل الدخول
3. **المشهد 2** (15ث): أضغط "Connect with Facebook" → أنتقل لشاشة فيسبوك وأوافق → أختار صفحتي
4. **المشهد 3** (20ث): عميل يعلق على ريلز بكلمة "سعر" → لوحة التحكم تظهر التعليق والرد الآلي يُرسل فوراً (اشرح بصوتك: "أنا مالك الصفحة، الشاشة تعرض أن وكيل الذكاء الاصطناعي رد على تعليق العميل")
5. **المشهد 4** (20ث): رسالة DM تصل → الرد الآلي في Inbox → Human Takeover → ترد يدوياً
6. **المشهد 5** (15ث): من Studio: تكتب موضوع → AI يولّد بوست → جدولة → يظهر Published في Queue

## 6. مسار العدالة المؤقت (قبل الموافقة) — ابدأ البيع فوراً
- أضف كل عميل جديد كـ **Tester** في التطبيق: developers.facebook.com → App Roles → Roles → Add People (بإيميلهم أو فيسبوك ID) → يقبل الدعوة من إعداداته → **يقدر يربط صفحته فوراً**
- الحد: ~100 دور لكل تطبيق — يكفي لمرحلة الإطلاق اليدوي

## 7. أين تقدم؟
developers.facebook.com → تطبيقك → **App Review → Permissions and Features** → لكل صلاحية: Request Advanced Access → أجب عن الأسئلة بالنصوص أعلاه + ارفع الفيديو + أضف صفحات الاختبار التجريبية

## 8. ملاحظات حرجة
- الـ Privacy Policy يجب أن تظهر **دون تسجيل دخول** — ✓ متوفر عندنا
- لا تستخدم كلمة "WhatsApp" في أي واجهة قبل الحصول على WhatsApp Business Platform (مؤجل)
- أي صلاحية تُرفض تعطيك سبباً محدداً — صحّح الفيديو حسب السبب وأعد التقديم (لا حد لعدد المحاولات)
