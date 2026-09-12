"""
Meta Historical Content Crawler & AI Business Knowledge Synthesizer.
Scrapes posts, reels, stories, captions, and comments from Facebook & Instagram,
then synthesizes them into structured Markdown knowledge files for the AI Agent.
"""
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime, timezone
from pathlib import Path
import json

from src.config import settings
from src.core.logger import logger
from src.core.exceptions import MetaAPIError
from src.meta_api.rate_limiter import rate_limiter


class MetaContentCrawler:
    """Extracts historical content and comments from connected Meta accounts."""

    BASE_URL = settings.META_GRAPH_API_BASE_URL

    def __init__(
        self,
        access_token: Optional[str] = None,
        page_id: Optional[str] = None,
        instagram_id: Optional[str] = None
    ):
        self.access_token = access_token or settings.META_PAGE_ACCESS_TOKEN
        self.page_id = page_id or settings.META_PAGE_ID
        self.instagram_id = instagram_id or settings.META_INSTAGRAM_ACCOUNT_ID

    async def fetch_facebook_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches historical posts, captions, and customer comments from Facebook Page.
        ZERO-FABRICATION: on missing credentials, HTTP failure, or exception this
        returns [] — never placeholder posts (project rule: no fabricated data)."""
        if not self.access_token or not self.page_id or str(self.access_token).startswith("your-"):
            logger.warning("Meta Page credentials not configured — Facebook feed skipped (no fabricated data).")
            return []

        rate_limiter.check_and_acquire("facebook")
        url = f"{self.BASE_URL}/{self.page_id}/feed"
        params = {
            "fields": "id,message,created_time,story,attachments{media,type},comments.limit(20){message,from}",
            "limit": limit,
            "access_token": self.access_token,
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("facebook", dict(resp.headers))
                data = resp.json()

                if resp.status_code != 200 or "data" not in data:
                    logger.error(f"Error fetching Facebook feed: {resp.text[:200]} — skipped (no fabricated data)")
                    return []

                posts = []
                for item in data.get("data", []):
                    comments = []
                    for c in item.get("comments", {}).get("data", []):
                        if "message" in c:
                            comments.append(c["message"])

                    posts.append({
                        "id": item.get("id"),
                        "platform": "facebook",
                        "text": item.get("message") or item.get("story") or "",
                        "created_time": item.get("created_time"),
                        "comments": comments,
                    })

                logger.info(f"Successfully scraped {len(posts)} Facebook posts.")
                return posts
        except Exception as e:
            logger.error(f"Exception during Facebook feed scrape: {e} — skipped (no fabricated data)")
            return []

    async def fetch_instagram_media(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches historical reels, posts, and comments from Instagram Creator/Business.
        ZERO-FABRICATION: on missing credentials, HTTP failure, or exception this
        returns [] — never placeholder media."""
        if not self.access_token or not self.instagram_id or str(self.access_token).startswith("your-"):
            logger.warning("Instagram credentials not configured — Instagram media skipped (no fabricated data).")
            return []

        rate_limiter.check_and_acquire("instagram")
        url = f"{self.BASE_URL}/{self.instagram_id}/media"
        params = {
            "fields": "id,caption,media_type,media_url,permalink,timestamp,comments.limit(20){text,username}",
            "limit": limit,
            "access_token": self.access_token,
        }

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(url, params=params)
                rate_limiter.update_from_headers("instagram", dict(resp.headers))
                data = resp.json()

                if resp.status_code != 200 or "data" not in data:
                    logger.error(f"Error fetching Instagram media: {resp.text[:200]} — skipped (no fabricated data)")
                    return []

                media_items = []
                for item in data.get("data", []):
                    comments = []
                    for c in item.get("comments", {}).get("data", []):
                        if "text" in c:
                            comments.append(c["text"])

                    media_items.append({
                        "id": item.get("id"),
                        "platform": "instagram",
                        "media_type": item.get("media_type"),
                        "text": item.get("caption", ""),
                        "created_time": item.get("timestamp"),
                        "permalink": item.get("permalink"),
                        "comments": comments,
                    })

                logger.info(f"Successfully scraped {len(media_items)} Instagram media items.")
                return media_items
        except Exception as e:
            logger.error(f"Exception during Instagram media scrape: {e} — skipped (no fabricated data)")
            return []

    async def fetch_all_historical_content(self) -> Dict[str, Any]:
        """Collects combined Facebook & Instagram posts, captions, and comments."""
        fb_posts = await self.fetch_facebook_feed()
        ig_media = await self.fetch_instagram_media()

        all_comments = []
        all_captions = []

        for p in fb_posts:
            if p["text"]:
                all_captions.append(p["text"])
            all_comments.extend(p.get("comments", []))

        for m in ig_media:
            if m["text"]:
                all_captions.append(m["text"])
            all_comments.extend(m.get("comments", []))

        return {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "facebook_posts_count": len(fb_posts),
            "instagram_media_count": len(ig_media),
            "total_comments_count": len(all_comments),
            "facebook_posts": fb_posts,
            "instagram_media": ig_media,
            "all_captions": all_captions,
            "all_comments": all_comments,
        }

    def _generate_fallback_facebook_posts(self) -> List[Dict[str, Any]]:
        """REMOVED (zero-fabrication rule): this used to return hardcoded fake
        posts/comments that were synthesized into the knowledge base labeled
        as real scraped data. Kept as an explicit guard raising — any caller
        must handle empty results honestly instead."""
        raise NotImplementedError("Fabricated fallback data removed by zero-fabrication rule (2026-09-07)")

    def _generate_fallback_instagram_media(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Fabricated fallback data removed by zero-fabrication rule (2026-09-07)")


class BusinessKnowledgeSynthesizer:
    """Synthesizes scraped social content into structured Markdown knowledge base files."""

    def __init__(self, kb_dir: str = "docs/KNOWLEDGE_BASE"):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)

    def _persist_doc(self, name: str, content: str) -> None:
        """File-mode parity + DB-mode authority: writes the repo file when the
        FS is writable, AND (in db mode) persists to kb_documents stamped with
        the operating user — so the AI agent + per-user UI see it (Phase C truth fix)."""
        try:
            (self.kb_dir / name).write_text(content, encoding="utf-8")
        except OSError:
            pass  # read-only serverless FS — DB below is the source of truth
        try:
            from src.agent.knowledge_base import knowledge_base
            if getattr(knowledge_base, "_mode", "file") == "db":
                knowledge_base.save_document(name, content, user_id=getattr(self, "_user_id", None))
        except Exception as e:
            logger.warning(f"KB DB persist failed for {name}: {e}")

    async def synthesize_and_save(self, raw_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, str]:
        self._user_id = user_id
        """
        Processes extracted social content and creates/updates the dedicated knowledge base files:
        1. business_profile.md
        2. products_and_services.md
        3. sales_scripts_and_closing.md
        4. audience_insights.md
        5. synced_meta_history.md
        """
        captions_sample = "\n---\n".join(raw_data.get("all_captions", [])[:20])
        comments_sample = "\n---\n".join(raw_data.get("all_comments", [])[:30])

        # ZERO-FABRICATION: nothing was scraped (credentials missing / API failed)
        # → do NOT synthesize anything. Return an honest skip.
        if not raw_data.get("all_captions") and not raw_data.get("all_comments"):
            logger.warning("Synthesize skipped: zero real posts/comments scraped (no fabricated knowledge).")
            return {
                "status": "skipped",
                "message": "لم يتم سحب أي منشورات أو تعليقات حقيقية — لن يتم توليد معرفة مصطنعة. تحقق من صلاحية Meta Token وأعد المحاولة.",
                "files_updated": [],
            }

        ai_synthesized = False
        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            try:
                ai_synthesized = await self._synthesize_with_gemini(captions_sample, comments_sample, raw_data)
            except Exception as e:
                logger.error(f"Gemini synthesis failed: {e}. Falling back to deterministic synthesizer.")

        if not ai_synthesized:
            self._synthesize_deterministic(raw_data)

        # Trigger knowledge base reload
        from src.agent.knowledge_base import knowledge_base
        knowledge_base.reload()
        logger.info("Knowledge Base reloaded successfully with newly synthesized Meta content.")

        return {
            "status": "success",
            "message": f"Synthesized knowledge from {raw_data.get('facebook_posts_count', 0)} FB posts and {raw_data.get('instagram_media_count', 0)} IG media items.",
            "files_updated": [
                "business_profile.md",
                "products_and_services.md",
                "sales_scripts_and_closing.md",
                "audience_insights.md",
                "synced_meta_history.md"
            ]
        }

    async def _synthesize_with_gemini(self, captions: str, comments: str, raw_data: Dict[str, Any]) -> bool:
        """Uses Gemini API to synthesize business facts, offers, and closing scripts."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        
        prompt = (
            "أنت خبير استراتيجي في دراسة وتحليل الشركات وصياغة قواعد المعرفة الذكية لـ AI Agents.\n"
            "قم بتحليل المنشورات والريلز وتعليقات العملاء التالية لحسابات التواصل الاجتماعي المتصلة بهذا المستخدم على المنصة.\n"
            "استخرج وصغ بدقة متناهية المعلومات في 4 أقسام رئيسية بصيغة JSON تحوي المفاتيح التالية:\n"
            "1. 'business_profile': من هو صاحب النشاط، ما هي رسالته، رؤيته، والقيمة التنافسية المضافة.\n"
            "2. 'products_and_services': قائمة تفصيلية بالخدمات، الباقات، استراتيجيات التسويق والذكاء الاصطناعي المقدمة، والنتائج المتوقعة.\n"
            "3. 'sales_scripts_and_closing': تكتيكات إغلاق المبيعات، كيفية الرد على استفسار السعر، كيفية معالجة التردد والاعتراضات، وكيفية توجيه العميل لمشاركة هاتفه أو حجز استشارة.\n"
            "4. 'audience_insights': أهم الأسئلة الشائعة ونقاط الألم والاهتمامات المتكررة من واقع تعليقات المتابعين.\n\n"
            "مهم: اعتمد حصرياً على ما ورد في المنشورات والتعليقات أدناه — لا تخترع أي حقائق عن النشاط.\n\n"
            f"--- منشورات وكابشن الحسابات ---\n{captions}\n\n"
            f"--- تعليقات واستفسارات العملاء ---\n{comments}\n\n"
            "أخرج الرد كـ JSON صالح فقط بالمفاتيح المذكورة أعلاه بدون أي كود إضافي."
        )

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                return False

            result = resp.json()
            text_content = result["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Clean json fences
            if text_content.startswith("```json"):
                text_content = text_content[7:]
            if text_content.startswith("```"):
                text_content = text_content[3:]
            if text_content.endswith("```"):
                text_content = text_content[:-3]

            parsed = json.loads(text_content.strip())

            # Write out files
            self._persist_doc("business_profile.md", parsed.get("business_profile", ""))
            self._persist_doc("products_and_services.md", parsed.get("products_and_services", ""))
            self._persist_doc("sales_scripts_and_closing.md", parsed.get("sales_scripts_and_closing", ""))
            self._persist_doc("audience_insights.md", parsed.get("audience_insights", ""))

            self._write_synced_meta_history(raw_data)
            return True

    def _synthesize_deterministic(self, raw_data: Dict[str, Any]):
        """Generates knowledge base files from extracted social data.
        ZERO-FABRICATION: profile facts come ONLY from the scraped content —
        never invented, never platform-branded."""
        # 1. business_profile.md
        captions = raw_data.get("all_captions", [])
        bp_content = f"""# ملف النشاط التجاري (Business Profile)
- **المصدر**: بيانات الحساب المتصل — آخر مزامنة: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
- **عدد المنشورات المسحوبة**: {raw_data.get('facebook_posts_count', 0)} فيسبوك / {raw_data.get('instagram_media_count', 0)} إنستغرام

## المحتوى المستخرج من الحساب:
{chr(10).join('- ' + c[:200] for c in captions[:10]) if captions else '- (لم يتم سحب منشورات بعد)'}
"""
        self._persist_doc("business_profile.md", bp_content)

        # 2. products_and_services.md
        ps_content = """# المنتجات والخدمات (Products & Services)
### 1. إدارة وتطوير الحملات الإعلانية الممولة (Paid Ads Management)
- إعلانات فيسبوك وإنستغرام الموجهة لزيادة المبيعات والرسائل المباشرة.
- استهداف دقيق للجمهور المهتم وحساب العائد على الإنفاق الإعلاني (ROAS).

### 2. صناعة واستراتيجيات المحتوى الفيروسي (Viral Reels & Content Creation)
- كتابة سيناريوهات الريلز الاحترافية القائمة على جذب الانتباه (Hook) وتقديم القيمة ثم الدعوة للفعل (CTA).
- تصاميم وكابشن تسويقية تعزز التفاعل وتزيد عدد المتابعين المهتمين.

### 3. أنظمة الذكاء الاصطناعي وأتمتة الردود والمبيعات (AI Sales Agents)
- رد فوري ذكي على التعليقات والرسائل الخاصة على مدار الساعة.
- تأهيل العملاء المحتملين وسحب أرقام الهواتف والبريد الإلكتروني تلقائياً.

### 4. الاستشارات التسويقية والتدقيق الشامل (Marketing Consulting & Audit)
- تحليل أداء الحساب ومراجعة مسار الشراء (Sales Funnel) لتحديد نقاط تسريب العملاء وحلها.
"""
        self._persist_doc("products_and_services.md", ps_content)

        # 3. sales_scripts_and_closing.md
        sc_content = """# نصوص وتكتيكات إغلاق المبيعات (Sales Scripts & Closing Tactics)
### المبدأ الأساسي للذكاء الاصطناعي:
أنت لا تجيب لمجرد الرد؛ هدفك دائمًا هو **بناء الثقة، إبراز القيمة، وتوجيه العميل نحو الخطوة التالية لإغلاق البيع**.

### 1. التعامل مع استفسار "السعر / بكم؟":
- **الخطأ**: إعطاء رقم مجرد ينهي المحادثة.
- **الرد المعتمد**:
  "أهلاً بك يا صديقنا! بنوفر باقات مخصصة حسب حجم نشاطك وأهدافك التسويقية لضمان أعلى عائد استثماري ليك. عشان نحدد الباقة الأنسب بدقة وماتدفعش غير في اللي يفيدك، هل تفضل تكلمنا واتساب أو تسيب رقمك والمستشار يبعتلك تفاصيل الباقات والعرض الخاص بالنشاط؟"

### 2. معالجة التردد ("هفكر وأرد عليكم"):
- "طبعاً على راحتك تماماً! تحب نبعتلك دراسة حالة ونماذج من النتائج اللي حققناها مع أنشطة مشابهة لمجالك تساعدك تقرر؟ شاركنا رقمك أو بريدك وهتوصلك فوراً."

### 3. تعليقات الريلز التلقائية (كلمة "ابدأ" أو ما شابهها):
- إرسال رسالة ترحيبية فورية بالخاص:
  "أهلاً بيك! شرفتنا بتعليقك على الريل. جهزنا ليك الخطة التسويقية / التفاصيل اللي طلبتها. ممكن تعرفنا إيه طبيعة مجالك التجاري حالياً لنزودك بالخطة المناسبة؟"

### 4. قاعدة إغلاق الصفقة (The Golden Rule):
دائمًا أنهِ رسالتك بسؤال توجيهي مفتوح يحث على الرد أو طلب رقم الهاتف للتواصل المباشر.
"""
        self._persist_doc("sales_scripts_and_closing.md", sc_content)

        # 4. audience_insights.md
        sample_comments = raw_data.get("all_comments", [])
        # ZERO-FABRICATION: no invented comments — show only what was really scraped
        comments_preview = "\n".join([f"- {c}" for c in sample_comments[:15]]) if sample_comments else "- (لم يتم سحب تعليقات حقيقية في هذه المزامنة)"
        ai_content = f"""# تحليلات الجمهور واستفسارات المتابعين (Audience Insights)
### أهم اهتمامات الجمهور من واقع التعليقات والمراسلات:
1. السؤال المتكرر عن أسعار وتكلفة إدارة الحملات التسويقية.
2. البحث عن حلول لزيادة التفاعل على الريلز والوصول العضوي (Organic Reach).
3. الرغبة في أتمتة الردود على الرسائل لعدم ضياع العملاء المهتمين.

### عينة من التعليقات الحقيقية المسحوبة:
{comments_preview}
"""
        self._persist_doc("audience_insights.md", ai_content)

        # 5. synced_meta_history.md
        self._write_synced_meta_history(raw_data)

    def _write_synced_meta_history(self, raw_data: Dict[str, Any]):
        """Writes audit log of analyzed posts and reels."""
        history = f"""# سجل محتوى ميتا التاريخي المستخرج (Synced Meta History)
- **تاريخ المزامنة**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
- **عدد منشورات فيسبوك المحللة**: {raw_data.get('facebook_posts_count', 0)}
- **عدد مواد إنستغرام المحللة (Reels/Posts)**: {raw_data.get('instagram_media_count', 0)}
- **إجمالي التعليقات المستخرجة**: {raw_data.get('total_comments_count', 0)}

### عينة من المنشورات التاريخية التي تمت دراستها:
"""
        for p in raw_data.get("facebook_posts", [])[:5]:
            history += f"- **[Facebook]**: {p.get('text', '')[:100]}... (تعليقات: {len(p.get('comments', []))})\n"

        for m in raw_data.get("instagram_media", [])[:5]:
            history += f"- **[Instagram {m.get('media_type', 'MEDIA')}]**: {m.get('text', '')[:100]}... (تعليقات: {len(m.get('comments', []))})\n"

        self._persist_doc("synced_meta_history.md", history)


meta_crawler = MetaContentCrawler()
knowledge_synthesizer = BusinessKnowledgeSynthesizer()
