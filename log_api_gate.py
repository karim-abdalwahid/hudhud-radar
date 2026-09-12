import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 2️⃣4️⃣ API test calls gate (threads_manage_replies + instagram_business_manage_comments)
- **instagram_business_manage_comments: مكتمل 100%** — ثلاثة استدعاءات 200 حية (POST comment id=18150530074556424 · GET comments · POST reply-to-comment).
- **threads_manage_replies**: GET /me/threads + GET /{id}/replies كلها 200 (×3 اليوم) — **لكن POST الرد يرجع 400 missing permissions** حتى بتوكينك الحقيقي — لأن advanced access بيتمنح **بعد** اعتماد المراجعة (دجاجة/بيضة موثقة من ميتا). السكرينكاست يوضح القراءة/التخزين/الإدارة في الـ CRM.
- **بنية جديدة**: POST /api/threads/{id}/reply (admin-only) — مسار الرد الجاهز يتفعل تلقائيًا بعد الموافقة + أُضيف للـ pre-flight توثيق كامل.
- الأخطاء اللي في الشات (The request is invalid) = أوامر inline فاشلة في PowerShell — القاعدة الدائمة SOP-11 في الـ Brain (كله ملفات سكربتات الآن).'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 18. Post-Entry Addition — API test calls gate
- IG comments: مكتمل (3 استدعاءات 200 حية). Threads replies: GETs ناجحة، POST الرد 400 قبل الموافقة (advanced access لاحق — سلوك ميتا). Route الرد جاهز يتفعل تلقائيًا. SOP-11 قاعدة دائمة ضد أوامر inline.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
