"""
Structured Meta Posts Analyzer (Phase 5 completion — owner-approved prompt).

For each synced post (from meta_feed_sync) + its REAL comments from the Graph
API, sends ONE Gemini request per post using the approved structural prompt.
Gemini must return strict JSON with:
- published_summary, promises, cta_requested (extracted FROM the post text)
- comment_counts + per-comment classification (cta_response vs real_question vs
  complaint/spam/compliment/other) — every analytic line cites [منشور:{id}] or [تعليق:{id}]
- audience_real_questions, recurring_needs, gaps, content_lessons, confidence

Results are aggregated into REAL knowledge documents (source=meta_analysis):
audience_insights.md, cta_effectiveness.md, content_performance.md
Zero fabrication: posts/comments that fail analysis are skipped and logged.
"""
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db
from src.knowledge.db_knowledge_base import db_knowledge_base

GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

SYSTEM_PROMPT = """أنت محلل استراتيجي محتوى وتفاعل جمهور لحساب التواصل الاجتماعي المتصل داخل المنصة.
مهمتك تحليل منشور واحد حقيقي مع تعليقات جمهوره الحقيقية، وتقديم تحليل موضوعي صارم.

قواعد صارمة (مخالفتها تُلغي صلاحية التحليل):
1. اعتمد فقط على البيانات المعطاة أدناه (نص المنشور + التعليقات + التواريخ).
   ممنوع منعاً باتاً التخمين أو استخدام أي معرفة خارجية عن الحساب أو السوق.
2. كل جملة تحليلية يجب أن تُرفق بمرجع صريح: [منشور:{id}] أو [تعليق:{id}].
   أي جملة بلا مرجع = مخالفة.
3. التمييز الإلزامي بين نوعين يخلطهما التحليل السطحي:
   - CTA-response: تعليق يكرر كلمة/عبارة طلبها صاحب المنشور بنفسه في نصه
     (مثال: المنشور قال "اكتب ابدأ في الكومنتات" ← تعليق "ابدأ" = استجابة CTA،
     وهي إشارة تفاعل إيجابية لكنها ليست سؤالاً حقيقياً ولا نية شراء مثبتة).
   - Real-intent: تعليق بأسلوب المشترك الخاص يسأل سؤالاً حقيقياً أو يعرض حاجة
     (سعر، تفاصيل خدمة، موعد، شكوى، مقارنة...).
4. العدّ عدلاً: أعداد التعليقات كما هي، والنسب تُحسب فقط من الموجود. ممنوع التضخيم.
5. إن كان المنشور بلا وعد واضح أو بلا CTA صريح، قل ذلك بصراحة في النتائج.
6. ممنوع اقتراح "ماذا كان يجب أن يفعل العميل" — الوكيل يفهم الواقع فقط.
7. المحتوى والتحليل يعودان لصاحب الحساب المتصل — لا ترتبط المنصة نفسها بالبيزنس.

أعد JSON فقط (بلا أي نص خارج JSON ولا أسوار كود) بهذا الهيكل:
{
  "post_id": "...",
  "published_summary": "ماذا نشر صاحب الحساب بالضبط (سطران)",
  "promises": [{"claim": "...", "evidence": "[منشور:{id}]"}],
  "cta_requested": {"keyword_or_action": "...", "quote_from_post": "..."} أو null,
  "comment_counts": {"total": N, "cta_response": N, "real_question": N,
                     "complaint": N, "spam": N, "compliment": N, "other": N},
  "comment_classification": [
    {"comment_id": "...", "text": "...", "type": "cta_response|real_question|complaint|spam|compliment|other",
     "reason": "سبب التصنيف في سطر واحد"}
  ],
  "audience_real_questions": [{"topic": "...", "evidence": ["[تعليق:{id}]"]}],
  "recurring_needs": ["حاجات متكررة بمراجع"],
  "gaps": ["فجوة بين الوعد/الـ CTA وما استجاب له الجمهور فعلياً — بمراجع"],
  "content_lessons": ["دروس عملية مبنية على الأرقام والمراجع فقط"],
  "confidence": "high|medium|low"
}"""


class MetaPostsAnalyzer:
    """Structural analysis of synced posts + real comments via Gemini."""

    def __init__(self):
        self._failures: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Fetch comments for a post (Graph API)
    # ------------------------------------------------------------------
    async def _fetch_comments(self, post_id: str, token: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    f"{settings.META_GRAPH_API_BASE_URL}/{post_id}/comments",
                    params={
                        "fields": "id,message,timestamp,username",
                        "limit": limit,
                        "access_token": token,
                    },
                )
            if r.status_code == 200:
                return r.json().get("data", []) or []
            logger.warning(f"Comments fetch failed for {post_id}: {r.status_code} {r.text[:150]}")
        except Exception as e:
            logger.warning(f"Comments fetch error for {post_id}: {e}")
        return []

    # ------------------------------------------------------------------
    # Gemini structural analysis (single post + its comments per call)
    # ------------------------------------------------------------------
    async def _analyze_one(self, post: Dict[str, Any], comments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not settings.GEMINI_API_KEY:
            return None
        post_id = post.get("id", "")
        user_block = {
            "post": {
                "id": post_id,
                "text": (post.get("content_text") or "")[:3000],
                "published_at": post.get("published_at"),
                "platform": post.get("platform"),
                "post_type": post.get("post_type"),
            },
            "comments": [
                {"id": c.get("id"), "text": (c.get("message") or c.get("text") or "")[:500],
                 "timestamp": c.get("timestamp")}
                for c in comments
            ],
        }
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [
                {"text": "حلل هذا المنشور وتعليقاته:\n" + json.dumps(user_block, ensure_ascii=False)}
            ]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4000,
                "responseMimeType": "application/json",
            },
        }
        url = GEMINI_URL_TMPL.format(model=settings.LLM_MODEL)
        headers = {"Content-Type": "application/json", "X-goog-api-key": settings.GEMINI_API_KEY}

        resp = None
        async with httpx.AsyncClient(timeout=90.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                except httpx.RequestError:
                    resp = None
                if resp is not None and resp.status_code == 200:
                    break
                if resp is None or resp.status_code not in (500, 502, 503, 504):
                    break
                await asyncio.sleep(2.0 * (attempt + 1))

        if resp is None or resp.status_code != 200:
            logger.warning(f"Analyzer {post_id}: Gemini failed ({resp.status_code if resp is not None else 'network'})")
            return None

        try:
            data = resp.json()
            candidates = data.get("candidates") or []
            parts = (candidates[0].get("content") or {}).get("parts") if candidates else None
            raw = "".join(p.get("text", "") for p in (parts or []) if isinstance(p, dict)).strip()
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or "post_id" not in parsed:
                logger.warning(f"Analyzer {post_id}: non-conforming JSON")
                return None
            return parsed
        except Exception as e:
            logger.warning(f"Analyzer {post_id}: parse failed — {e}")
            return None

    # ------------------------------------------------------------------
    # Aggregate results into knowledge documents
    # ------------------------------------------------------------------
    def _aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, str]:
        audience = ["# رؤى الجمهور الحقيقية (من تحليل المنشورات والتعليقات)", ""]
        cta = ["# فعالية كلمات الـ CTA (استجابة الـ CTA مقابل الاهتمام الحقيقي)", ""]
        perf = ["# أداء المحتوى — دروس مستخرجة من التحليل البنيوي", ""]

        for r in results:
            pid = r.get("post_id", "?")
            counts = r.get("comment_counts", {}) or {}
            total = counts.get("total", 0)
            cta_resp = counts.get("cta_response", 0)
            real_q = counts.get("real_question", 0)

            # CTA effectiveness
            cta_req = r.get("cta_requested")
            if cta_req and total:
                cta.append(f"## منشور [منشور:{pid}] — CTA مطلوب: «{cta_req.get('keyword_or_action')}»")
                cta.append(f"- إجمالي التعليقات: {total}")
                cta.append(f"- استجابة CTA: {cta_resp} ({round(cta_resp/total*100)}%)")
                cta.append(f"- اهتمام حقيقي (أسئلة): {real_q} ({round(real_q/total*100)}%)")
                cta.append(f"- الاقتباس من المنشور: «{cta_req.get('quote_from_post', '')}»")
                cta.append("")

            # Audience real questions
            for q in (r.get("audience_real_questions") or []):
                ev = ", ".join(q.get("evidence", []))
                audience.append(f"- {q.get('topic')} — {ev}")

            # Content lessons
            for lesson in (r.get("content_lessons") or []):
                perf.append(f"- [منشور:{pid}] {lesson}")

            # Gaps
            for gap in (r.get("gaps") or []):
                perf.append(f"- فجوة [منشور:{pid}]: {gap}")

        return {
            "audience_insights": "\n".join(audience).strip(),
            "cta_effectiveness": "\n".join(cta).strip(),
            "content_performance": "\n".join(perf).strip(),
        }

    # ------------------------------------------------------------------
    # Main entry: analyze recent posts
    # ------------------------------------------------------------------
    async def analyze_recent(self, limit: int = 10) -> Dict[str, Any]:
        from src.meta_api.extended_api import _resolve_credentials
        from src.meta_api.feed_sync import meta_feed_sync

        creds = _resolve_credentials()
        token = creds["token"]
        if not token or token.startswith("your-"):
            return {"status": "skipped", "reason": "Meta token غير متوفر"}
        if not settings.GEMINI_API_KEY:
            return {"status": "skipped", "reason": "GEMINI_API_KEY غير متوفر"}

        posts = meta_feed_sync.get_synced_posts(platform="all", limit=limit) or []
        if not posts:
            # try a live sync then re-read
            await meta_feed_sync.sync_all_live_content(limit_per_platform=25)
            posts = meta_feed_sync.get_synced_posts(platform="all", limit=limit) or []
        if not posts:
            return {"status": "skipped", "reason": "لا منشورات متزامنة"}

        results: List[Dict[str, Any]] = []
        self._failures = []
        for post in posts[:limit]:
            pid = post.get("id", "")
            comments = await self._fetch_comments(pid, token)
            if not comments:
                logger.info(f"Analyzer: post {pid} has no comments — skipping")
                continue
            analysis = await self._analyze_one(post, comments)
            if analysis:
                results.append(analysis)
            else:
                self._failures.append({"post_id": pid, "reason": "analysis failed — skipped (no fabrication)"})

        if not results:
            return {"status": "no_results", "posts_fetched": len(posts), "posts_analyzed": 0,
                    "failures": self._failures, "reason": "لم ينجح تحليل أي منشور (لا بيانات مصطنعة)"}

        aggregated = self._aggregate(results)
        saved = []
        for name, content in aggregated.items():
            if content:
                res = db_knowledge_base.save_document(
                    f"{name}.md", content, source="meta_analysis", is_core=(name == "audience_insights")
                )
                saved.append(res.get("filename"))

        return {
            "status": "success",
            "posts_fetched": len(posts),
            "posts_analyzed": len(results),
            "failures": self._failures,
            "documents_saved": saved,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


meta_posts_analyzer = MetaPostsAnalyzer()
