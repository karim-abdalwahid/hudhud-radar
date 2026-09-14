import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 3️⃣6️⃣ 🎯اصطياد 500 الشامل — 10 أصناف حقيقية أُبيدت
**المصفوفة العدائية** (audit_500_hunter.py · 44 حالة): صفر →5xx. المكتشف والمصلح:
1-6. الويب هوكات (ميتا+ثريدز) كانت تنفجر 500 مع: جسم غير JSON مُوَقَّع بصحيح · payload=list · entry=nass · mentions value=null — الآن 400 صادق + parsers بحراسة isinstance كاملة (لم تعد أي حالة parsing قادرة على قتل المعالج).
7-14. أي UUID فاسد في المسار (15 نقطة: leads/posts/inbox/credits/plan/notifications/ai/queue/coupons) كان يضرب PostgREST وتطفو 500 — وسيط مركزي `uuid_segment_guard` يعيدها 404 صادق، **وبعد التصحيح مسجّل داخل طبقة التصديق** حتى لا يكسر 403-لغير-الأدمن (نفس الترتيب الذي كسر اختبار الأمان وأُعيد وأُخضر).
**إثباتات**: محلي 44/44 صفر 5xx · 317/317 · الإنتاج: garbage→400 · bad-uuid→401 auth-first. تقرير مفصل: docs/PROJECT_REPORTS/AUDIT_500_SWEEP_2026-09-15.md · commit 3d99b51 لايف.
**الباقي النظيف موثق**: 422 من الفريموورك لكل إدخال مهيكلي خاطئ، بارامترات فوضوية تتحمل، مدفوعات fail-closed.'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 32. Post-Entry Addition — 500-HUNTER (44-case hostile sweep)
- 10 real 5xx classes eliminated: webhook hostile payloads (garbage/None/non-list) now 400/ignored with full isinstance parsers; central uuid_segment_guard middleware (auth-ordered, 403 intact) converts every malformed UUID path to honest 404. 44/44 local, prod-verified 400/401. 317/317. commit 3d99b51. Report: AUDIT_500_SWEEP_2026-09-15.md'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
