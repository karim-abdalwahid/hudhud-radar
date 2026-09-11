# 🎬 App Review Recording Prompts — AI Browser Agent (v1.0, 2026-09-11)
#recording #app-review #browser-agent

**ارسل هذا الملف كاملًا للـ agent. كل برومبت مستقل ودقيق — نفّذه حرفيًا بالترتيب.**

---

## 🧭 GLOBAL RULES (تطبق على كل فيديو — اقرأها قبل أي برومبت)

1. **الدخول**: افتح `https://www.hudhd.com/login` → `admin.test@hudhud.test` / `AdminTest#2026` → اضغط "Sign in to Dashboard".
2. **تسجيل الشاشة**: 1920×1080 كامل الشاشة — **شريط العنوان ظاهر دائمًا** — لقطة واحدة بدون قطع — 45–90 ثانية.
3. **التعليق الصوتي**: إنجليزي بطيء وواضح — النصوص جاهزة في كل برومبت (اقرأها كما هي).
4. **بعد كل خطوة**: تحقق من عنصر النجاح المذكور في "✅ SUCCESS" قبل ما تكمل — لو فشل، أعد الخطوة.
5. **ممنوع**: إظهار أي توكن/مفتاح على الشاشة · القطع والمونتاج · فتح صفحات غير المذكورة.
6. **قبل التسجيل**: شغّل Pre-flight (آخر قسم) وتأكد أن كل البنود ✅.

---

## 🧪 PRE-FLIGHT — Required API Test Calls (قبل تصوير #12 و #17)

Meta يشترط استدعاءات API ناجحة موثقة قبل مراجعة صلاحيتين. نفّذ الاتنين (من أي terminal على جهاز المالك، التوكن من `.env` → `META_PAGE_ACCESS_TOKEN`):

**أ. threads_manage_replies** (تم تنفيذها فعلًا 2026-09-11 بنجاح — أعد التأكيد):
```bash
curl -s "https://graph.facebook.com/v21.0/me/threads?fields=id,text,timestamp&limit=5&access_token=$TOKEN"
curl -s "https://graph.facebook.com/v21.0/{THREAD_ID}/replies?fields=id,text,timestamp,username&access_token=$TOKEN"
```
✅ النجاح: HTTP 200 + قائمة threads/replies.
   ⚠️ ملاحظة موثقة: POST الرد الآلي على الثريدز يرجع 400 (missing permissions) قبل الموافقة — هذا طبيعي (advanced access يُمنح بعد اعتماد المراجعة). استدعاءات GET replies الناجحة (منفذة 2026-09-11 ×3) هي التي يراها ميتا، والسكرينكاست يوضح القراءة والتخزين والإدارة في الـ CRM.

**ب. instagram_business_manage_comments**:
```bash
curl -s "https://graph.facebook.com/v21.0/{IG_ID}/media?fields=id,like_count,comments_count&limit=5&access_token=$TOKEN"
curl -s "https://graph.facebook.com/v21.0/{MEDIA_ID}/comments?fields=id,text&access_token=$TOKEN"
```
✅ النجاح: HTTP 200 + قائمة comments. سجّل وقت التنفيذ — ميتا تتحقق من النشاط تلقائيًا.
   ✅ منفذة فعلًا 2026-09-12: POST comment → id 18150530074556424 · GET comments → 200 · POST reply-to-comment → 200 (الثلاثة 200 حية).

---

## 📦 GROUP 1 — الإنبوكس (4 فيديوهات في جلسة واحدة)

### PROMPT 1 — pages_messaging
**اذهب**: `/inbox` → افتح محادثة "Kareem Abdelwahid".
**الخطوات**: (1) ورّي المحادثة والرسائل (2) أشر لرد الـ AI في الثريد (3) اكتب ردًا قصيرًا في صندوق الإدخال واضغط Send 🚀 (4) افتح تاب ثانٍ على Messenger وورّي الرسالة وصلت.
**التعليق**: "Customer messages arrive through Messenger webhooks; our AI replies within the 24-hour window, and a human can take over anytime — all through pages_messaging."
**✅ SUCCESS**: الرد ظاهر في الثريد + Messenger يعرضه.

### PROMPT 2 — Human Agent
**اذهب**: `/inbox` → نفس المحادثة.
**الخطوات**: (1) ورّي طابع زمني لرسالة قديمة (2) اضغط 🛑 Human Takeover → البنر الأصفر يظهر (3) اكتب ردًا بشريًا → Send (4) ورّي وصوله في Messenger (5) اشرح: "AI stays paused for this customer until I resume it."
**التعليق**: "Human Agent lets our client's human support team reply beyond the 24-hour window — bots never do this; only real human agents."
**✅ SUCCESS**: البنر "Human Takeover Active" ظاهر + الرسالة البشرية في Messenger.

### PROMPT 3 — Business Asset User Profile Access
**اذهب**: `/inbox` → افتح محادثة Kareem.
**الخطوات**: (1) ورّي بطاقة "CUSTOMER DOSSIER & DEAL" يسار الشاشة: الاسم + الصورة (2) مرّر على تفاصيل العميل (3) افتح `/leads` وورّي نفس العميل في الـ CRM.
**التعليق**: "When customers message our clients, Business Asset User Profile Access lets Hudhud show who they are — name and profile info — so replies are personal and leads are properly identified."
**✅ SUCCESS**: الاسم "Kareem Abdelwahid" + الصورة ظاهرين في الـ Dossier.

### PROMPT 4 — instagram_manage_messages
**اذهب**: `/inbox` → فلتر/اختر محادثة قناتها 📸 Instagram.
**الخطوات**: نفس PROMPT 1 (رد AI ظاهر + رد يدوي + إثبات في IG Direct).
**التعليق**: "Instagram DMs flow into the same unified inbox — the AI replies within the messaging window, humans can take over — via instagram_manage_messages."
**✅ SUCCESS**: محادثة IG ظاهرة بردها.

---

## 📦 GROUP 2 — الاستوديو (5 فيديوهات)

### PROMPT 5 — pages_manage_posts
**اذهب**: `/studio?view=publisher`.
**الخطوات**: (1) اكتب منشورًا قصيرًا (2) Platform = Facebook (3) اضغط 🚀 Publish Now (4) افتح الصفحة على فيسبوك في تاب ثانٍ وورّي المنشور حيًا.
**التعليق**: "pages_manage_posts lets Hudhud publish and manage posts on the client's Page on their behalf."
**✅ SUCCESS**: المنشور حي على الصفحة.

### PROMPT 6 — instagram_content_publish (+ instagram_business_content_publish)
**اذهب**: `/studio?view=publisher`.
**الخطوات**: (1) اكتب منشورًا + Media URL لصورة (2) Platform = Instagram (3) Publish Now (4) ورّيه حيًا على instagram.com.
**التعليق**: "Hudhud publishes posts and reels to the client's Instagram through instagram_content_publish."
**✅ SUCCESS**: المنشور حي على IG.

### PROMPT 7 — pages_read_user_content (+ instagram_manage_contents)
**اذهب**: `/studio?view=feed`.
**الخطوات**: (1) ورّي مكتبة المحتوى المتزامن: منشورات وريلز فيسبوك وإنستجرام بأرقامها (2) افتح الصفحة على فيسبوك/إنستجرام في تاب ثانٍ وورّي نفس المنشورات (3) اضغط 🔄 Sync وورّي التحديث.
**التعليق**: "Hudhud reads the client's existing posts and content to build the AI's knowledge base — via pages_read_user_content."
**✅ SUCCESS**: نفس المنشورات ظاهرة في المكتبة وعلى المنصة.

### PROMPT 8 — threads_content_publish
**اذهب**: `/studio?view=publisher` → قسم "🧵 Threads Publishing".
**الخطوات**: (1) اكتب نصًا في حقل Threads (2) اضغط 🚀 Publish to Threads (3) ظهر ✅ مع الـ ID (4) افتح threads.net في تاب ثانٍ وورّي المنشور حيًا.
**التعليق**: "threads_content_publish lets our AI publish content to the client's Threads account."
**✅ SUCCESS**: ✅ Published + المنشور حي على threads.net.

### PROMPT 9 — threads_delete (+ threads_read_replies)
**اذهب**: `/studio?view=publisher` → نفس القسم.
**الخطوات**: (1) اضغط 🔄 Refresh my posts (2) ورّي قائمة منشوراتك (3) اضغط 💬 Replies على منشور وورّي الردود (4) اضغط 🗑️ Delete على منشور تجريبي → أكد (5) ورّيه اختفى من threads.net.
**التعليق**: "Clients can view replies and remove published content directly from Hudhud — via threads_read_replies and threads_delete."
**✅ SUCCESS**: المنشور اختفى من القائمة ومن threads.net.

---

## 📦 GROUP 3 — Analytics (4 فيديوهات)

### PROMPT 10 — pages_read_engagement
**اذهب**: `/analytics`.
**الخطوات**: (1) ورّي الـ metrics strip بأرقام حقيقية (2) مرّر على رسوم الأداء (3) غيّر المدى الزمني إن وُجد وورّي تحديث الأرقام.
**التعليق**: "These engagement metrics are read live from the client's Page via the Graph API — pages_read_engagement."
**✅ SUCCESS**: أرقام غير صفرية ظاهرة.

### PROMPT 11 — read_insights (+ instagram_manage_insights)
**اذهب**: `/analytics`.
**الخطوات**: (1) ورّي قسم Page insights: reach/impressions (2) ورّي قسم Instagram insights بأرقام المشاهدات الحقيقية.
**التعليق**: "read_insights powers every performance report in Hudhud — reach, engagement, trends."
**✅ SUCCESS**: أرقام حقيقية (مش أصفار) ظاهرة.

### PROMPT 12 — threads_manage_insights
**اذهب**: `/analytics` → كارت "🧵 Threads Insights".
**الخطوات**: (1) ورّي الثلاثة مؤشرات (Views/Likes/Replies) (2) اضغط 🔄 Refresh وورّي التحديث.
**التعليق**: "threads_manage_insights powers the Threads performance metrics in our analytics — read live from the Threads API."
**✅ SUCCESS**: الكارت يعرض أرقامًا (حتى لو 0 — حقيقية) بدون أخطاء.

### PROMPT 13 — instagram_business_manage_insights
**اذهب**: `/analytics` → قسم Instagram insights.
**الخطوات**: نفس PROMPT 11 مع النطق: "instagram_business_manage_insights reads reach, views and follower data from the client's connected Instagram business account."
**✅ SUCCESS**: أرقام IG ظاهرة.

---

## 📦 GROUP 4 — الإعدادات (5 فيديوهات)

### PROMPT 14 — pages_show_list
**اذهب**: `/settings` → تبويب Meta.
**الخطوات**: (1) ورّي كارت الصفحة المتصلة "إبدأ ماركتينج - Karim Abdalwahid" (2) اضغط "Connect with Facebook" (3) نافذة OAuth تسرد صفحات المستخدم (4) أغلق النافذة بدون إكمال وورّي الحالة المتصلة.
**التعليق**: "pages_show_list lets Hudhud list the Facebook Pages a client manages, so they pick which Page our AI agent operates."
**✅ SUCCESS**: نافذة فيسبوك تعرض قائمة الصفحات.

### PROMPT 15 — pages_manage_metadata
**اذهب**: `/settings` → قسم Webhooks.
**الخطوات**: (1) ورّي callback URL `https://www.hudhd.com/api/webhook/meta` (2) افتح تاب ثانٍ على داشبورد ميتا → Webhooks → ورّي نفس الـ URL والحقول المفعّلة (3) ارجع وورّي الحالة المتصلة.
**التعليق**: "pages_manage_metadata lets Hudhud subscribe the client's Page to our webhook — every customer message reaches our AI agent in real time."
**✅ SUCCESS**: نفس الـ URL في المكانين + الحقول مفعّلة.

### PROMPT 16 — threads_basic
**اذهب**: `/settings` → تبويب Threads.
**الخطوات**: (1) ورّي حالة الاتصال بالحساب @karim__abdalwahid (2) ورّي خيار Refresh للتوكن.
**التعليق**: "Through the official Threads OAuth, Hudhud reads the client's Threads profile identity via threads_basic."
**✅ SUCCESS**: الحساب ظاهر متصلًا.

### PROMPT 17 — instagram_business_basic (+ instagram_manage_messages)
**اذهب**: `/settings` → Meta → ورّي حساب IG المتصل @karim__abdalwahid.
**الخطوات**: (1) ورّي username ومعلومات الحساب (2) انتقل سريعًا للإنبوكس وورّي محادثة IG (يربط الصورتين).
**التعليق**: "instagram_business_basic reads the connected account's identity; instagram_business_manage_messages powers the unified inbox replies."
**✅ SUCCESS**: الحساب ظاهر + محادثة IG.

### PROMPT 18 — AI Master Switch (إضافي — يقوي الطلب)
**اذهب**: `/settings` → تبويب 🔐 الحساب والأمان → كارت "🤖 AI Master Switch".
**الخطوات**: (1) ورّي الحالة (✅ AI Active) (2) اضغط ⏸️ Pause → البادج يتحول ⏸️ AI Paused (3) افتح `/inbox` واشرح أن الـ AI ساكت في كل المحادثات (4) ارجع وأعد التشغيل.
**التعليق**: "The owner can pause the AI globally and manage pages personally — messages keep arriving for manual replies."
**✅ SUCCESS**: البادج يتبدل في الاتجاهين.

---

## 📦 GROUP 5 — الإدارة (3 فيديوهات)

### PROMPT 19 — business_management
**اذهب**: `/users` (أدمن) + تاب ثانٍ على business.facebook.com/settings.
**الخطوات**: (1) ورّي Business Settings في ميتا: الـ App والـ Assets (2) ارجع لتبويبنا وورّي لوحة الأدمن تشغل نفس الأصول.
**التعليق**: "business_management connects the client's business assets — Pages, Instagram accounts — to the Hudhud platform they subscribed to."
**✅ SUCCESS**: الصورتان تربطان الأصول بالمنصة.

### PROMPT 20 — email
**اذهب**: `/users`.
**الخطوات**: (1) ورّي جدول المستخدمين بالإيميلات (2) ورّي إشعار/إيميل خدمي إن وُجد.
**التعليق**: "email is used for account identity, receipts and product notifications — stored encrypted-at-rest, never sold."
**✅ SUCCESS**: الإيميلات ظاهرة في الجدول.

### PROMPT 21 — pages_utility_messaging
**اذهب**: `/inbox` → محادثة Kareem.
**الخطوات**: (1) اكتب رسالة خدمية: "Your report is ready — you can download it from your dashboard 📊" (2) Send (3) ورّي وصولها في Messenger.
**التعليق**: "For transactional, service-related updates we send utility messages through the same authorized channel — pages_utility_messaging."
**✅ SUCCESS**: الرسالة الخدمية وصلت Messenger.

---

## 📦 GROUP 6 — الأتمتة والمنشن (4 فيديوهات)

### PROMPT 22 — pages_manage_engagement
**اذهب**: `/automations` → ورّي workflow نشط (keywords → like/reply/DM) → ثم: علّق على منشور بالكلمة المفتاحية من حساب ثانٍ → ورّي الأتمتة تعمل (لايك + رد).
**التعليق**: "pages_manage_engagement lets our agents like and reply to comments on the client's Page per configured rules."
**✅ SUCCESS**: الأتمتة نفذت على التعليق.

### PROMPT 23 — instagram_manage_comments
**اذهب**: `/automations` → نفس السيناريو على تعليق Instagram (ريلز).
**التعليق**: "Comment inquiries on Reels are captured and answered — turning comments into sales conversations — instagram_manage_comments."
**✅ SUCCESS**: رد/لايك على تعليق IG.

### PROMPT 24 — instagram_manage_engagement
**اذهب**: نفس PROMPT 23 مع إبراز اللايك تحديدًا.
**التعليق**: "instagram_manage_engagement lets our agents protect the client's Instagram community — liking and replying per rules."
**✅ SUCCESS**: التفاعل ظاهر على المنشور.

### PROMPT 25 — threads_manage_mentions
**الخطوات**: (1) من حساب ثانٍ: اذكر/تاج صفحة إبدأ ماركتينج في منشن ثريدز (2) على hudhd.com: اضغط 🔄 Refresh my posts في الاستوديو أو اعرض الإنبوكس بعد المزامنة (3) ورّي المنشن ظهر كـ Lead/رسالة في النظام.
**التعليق**: "threads_manage_mentions lets Hudhud read mentions of the client's Threads account so they can see and respond in their inbox."
**✅ SUCCESS**: المنشن ظهر في النظام.

---

## 📦 GROUP 7 — الهوية والبنية (4 فيديوهات)

### PROMPT 26 — threads_read_replies
**اذهب**: `/studio?view=publisher` → Refresh my posts → 💬 Replies.
**التعليق**: "threads_read_replies reads replies to the client's Threads posts into their dashboard."
**✅ SUCCESS**: الردود ظاهرة تحت المنشور.

### PROMPT 27 — threads_manage_replies
**اذهب**: نفس الشاشة.
**الخطوات**: (1) ورّي الردود المقروءة والمخزنة في الـ CRM (2) اشرح أن الإدارة تشمل العرض والمتابعة من الإنبوكس.
**التعليق**: "threads_manage_replies lets Hudhud organize reply conversations on the client's behalf — replies are read, stored and managed in the unified inbox."
**✅ SUCCESS**: الردود ظاهرة في الواجهة (بدون ادعاء رد آلي).

### PROMPT 28 — instagram_business_manage_comments
**اذهب**: `/automations` → سيناريو تعليق IG (مثل PROMPT 23) مع إبراز استدعاءات الـ API الفعلية (Pre-flight ب).
**التعليق**: "instagram_business_manage_comments reads and replies to comments on the client's Instagram per their rules."
**✅ SUCCESS**: الرد ظاهر + اذكر أن استدعاءات الـ API موثقة.

### PROMPT 29 — business_asset_user_profile_access (نسخة إنستجرام)
**اذهب**: `/inbox` → محادثة IG → Dossier.
**التعليق**: "For Instagram conversations, the same Business Asset User Profile Access shows the customer's identity alongside their message."
**✅ SUCCESS**: بطاقة العميل ظاهرة على محادثة IG.

---

## 📋 ترتيب التصوير المقترح (جلسة واحدة)
1. Pre-flight API calls (قسم 🧪) 2. GROUP 1 (الإنبوكس) 3. GROUP 2 (الاستوديو) 4. GROUP 3 (Analytics) 5. GROUP 4 (الإعدادات) 6. GROUP 5-7 · **31 فيديو** (29 مطلوبة + 2 إضافيان يقويان الملف).
