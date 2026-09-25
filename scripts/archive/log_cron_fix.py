import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 3️⃣4️⃣ 🐛 إصلاح جذري: وظيفة cron-job.org كانت تُعطّل نفسها تلقائيًا
**السبب الحقيقي**: كرونجدول كان يستدعي scheduler-tick أثناء انتظار حاوية إنستجرام (15 محاولة × 3ث ≈ 45 ثانية) — Vercel يقتل الدالة عند ~10 ثوانٍ (حد Hobby) → فشل متكرر → cron-job.org **يوقف الوظائف المتكررة الفشل تلقائيًا** → المالك يعيد تفعيلها يدويًا كل مرة.
**الحل (آلة حالات قصيرة النفَس)**: كل tick الآن ≤ ثوانٍ: (1) استئناف الحاويات بانتظار حالة واحدة فقط لكل حاوية (2) شفاء ذاتي: أي 'publishing' عالق >15دقيقة يعود 'scheduled' (3) حد 2 منشور/نبذة — FB يُنشر فوريًا، IG يُنشئ حاوية ويعود فورًا. وكل نقاط cron الثلاث تعود **200 دائمًا** مع status صادق ('partial' عند خطأ داخلي) — لا فشل HTTP يعني لا تعطيل.
**إثبات**: محلي 4 ثوانٍ · مفتاح خاطئ 401 fail-closed · **PRODUCTION بعد النشر: 200 في 1.5 ثانية** · 4 اختبارات regressive (خط زمني queue→resume→published، إعادة إدراج عالق، سقف النبذة، 200 عند انهيار) — السويت 309/309.
**أمر مطلوب من المالك**: إعادة تفعيل الوظيفة في cron-job.org (ستبقى فعالة الآن)، **بالإضافة لتدوير CRON_SECRET** — المفتاح نُشر نصًا في الشات (Vercel Env → غيّره + حدّث رابط cron-job.org بنفسك؛ أدوات الوصول لدي لا تشمل تغيير متغيرات Vercel).'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 30. Post-Entry Addition — CRON AUTO-DISABLE ROOT-CAUSED & FIXED
- 45s container waits killed by Vercel 10s budget -> cron-job.org auto-disabled job. Short-budget state machine (queue/poll-once/requeue; cap 2/tick) + cron endpoints always-200. Prod tick 1.5s. +4 tests -> 309/309. commit 39a2764. ACTION owner: re-enable job + ROTATE exposed CRON_SECRET.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
