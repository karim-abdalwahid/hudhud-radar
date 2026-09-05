# 📋 SOP-06: استكشاف واكتساب المهارات الذكية (Skill Discovery & Integration)
#sop #skills #ai-ecosystem #skills-cli #workflow

يحدد هذا الإجراء القياسي كيفية البحث عن المهارات المتقدمة (Agent Skills)، وتقييم جودتها وموثوقيتها، وتثبيتها لتعزيز قدرات الوكيل الذكي عند الحاجة.

---

## 🎯 المبدأ التوجيهي
**"إذا كان بإمكانك إنجاز العمل مباشرة وبأعلى جودة، فافعل ذلك مباشرة؛ وإذا كانت هناك مهارة متخصصة ضرورية ستمنحك قوة إضافية وخبرة عميقة في مجال محدد، فاستقطبها ولا تفوتها."**

---

## 🌐 المصادر المعتمدة للمهارات الذكية
1. **[Skills.sh Leaderboard](https://www.skills.sh/)** — مستودع المهارات المفتوح الأكثر انتشاراً.
2. **[GitHub AI Skills Topics](https://github.com/topics/ai-skills)** — المهارات المفتوحة المصدر على جيت هب.
3. **[AI Hero Skills](https://www.aihero.dev/skills)** — مكتبة أدوات وأدلة الذكاء الاصطناعي.
4. **[Find AI Skills](https://findaiskills.com/skills)** & **[Agentic Skills](https://agenticskills.io/skills/find-skills)** — محركات بحث وفهرسة المهارات.
5. **[Google AI Skills](https://ai.google/learn-ai-skills/)** & **[Microsoft AI Hub](https://learn.microsoft.com/en-us/ai/)** — معايير وأطر عمل الشركات الرائدة.

---

## 🛠️ أدوات وأوامر البحث والتثبيت (`npx skills`)

### 1. البحث التفاعلي والكلمات المفتاحية
```bash
npx skills find <query>
# أمثلة:
npx skills find "social media"
npx skills find "meta graph api"
npx skills find "react performance"
```

### 2. التثبيت المباشر
تتعرف أداة `npx skills` تلقائياً على بيئة **Antigravity** وتقوم بنسخ المهارة مباشرة إلى مجلد `.agents/skills/<skill-name>`:
```bash
npx skills add <package> --skill <skill-name> -y
# مثال:
npx skills add vercel-labs/skills --skill find-skills -y
```

### 3. التثبيت اليدوي عبر رابط `SKILL.md`
يمكن تنزيل ملف `SKILL.md` مباشرة ووضعه داخل:
- نطاق المشروع: `.agents/skills/<skill-name>/SKILL.md`
- النطاق العام للنظام: `C:\Users\Dell\.gemini\config\skills\<skill-name>\SKILL.md`

---

## ⚖️ معايير فحص جودة وأمان المهارة قبل الاعتماد
1. **عدد مرات التثبيت (Install Count)**: تفضيل المهارات التي تتجاوز 1,000 عملية تثبيت (1K+). الحذر من المهارات التي تقل عن 100 تثبيت.
2. **سمعة المطور / المستودع**: الاعتماد على الحسابات الموثقة والرسمية (مثل `vercel-labs`, `anthropics`, `langchain-ai`, `microsoft`).
3. **التقييم الأمني (Security Risk Assessment)**: التأكد من سلامة الكود وخلوه من استدعاءات مريبة (Zero alerts on Socket/Snyk).

---

## 🔄 التحديث والتوثيق
عند إضافة مهارة جديدة:
1. توثيق المهارة ومبرر استخدامها في سجل الذاكرة `PROJECT_MEMORY.md`.
2. تحديث فهرس عقل المشروع `PROJECT_BRAIN/00_Index.md`.
