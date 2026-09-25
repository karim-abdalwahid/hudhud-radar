import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
addition = '''

## 2️⃣5️⃣ 🟢 بند الـ API Test Calls اقفل بالكامل (أمر المالك: مفيش تقديم غير لما كلهم يخضروا)
- **threads_manage_replies — PASSED ✅**: الجذر ما كانش advanced access — كان **endpoint غلط**: POST /{id}/replies مش مسار نشر صحيح (THApiException 100/33). المسار الرسمي للرد: container عبر /me/threads بـ reply_to_id ثم /me/threads_publish → **اتنفذ حيًا 200/200** (reply id 2750047694351 ظاهر على ثريد المالك؛ حذف الرد نفسه يتطلب موافقة — موثق).
- **instagram_business_manage_comments — PASSED ✅** (3 استدعاءات 200: POST comment/GET comments/POST reply-to-comment).
- **كود**: publish_thread بـ reply_to_id · /api/threads/{id}/reply استُبدل بالتدفق الرسمي · RECORDING_PROMPTS محدث.
- 278/278 · c67b2e4 منشور ومتحقق حيًا.'''
open("docs/PROJECT_REPORTS/SESSION_LOGS/2026-09-11_session.md", "a", encoding="utf-8").write(addition)
addition2 = '''

### 19. Post-Entry Addition — API test calls gate مكتمل
- threads_manage_replies PASSED: الرد عبر المسار الرسمي (container + reply_to_id) — 200/200 حيًا (كان endpoint خاطئ). IG comments PASSED (3×200). c67b2e4 لايف — المالك يقدر يقدم المراجعة.'''
open("PROJECT_MEMORY.md", "a", encoding="utf-8").write(addition2)
print("logged")
