"""
AI Content Studio Engine:
Generates viral, engaging Facebook & Instagram posts, Reel scripts, and Story sequences.
Adheres to Egyptian/Modern Arabic marketing voice, AIDA formula, and conversational CTAs.
"""
from typing import Dict, Any, Optional, List
import json
import httpx

from src.config import settings
from src.core.logger import logger
from src.content_studio.models import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    PostType,
    ContentPlatform,
)


class ContentEngine:
    """Specialized AI Content Engine for Social Media Marketing."""

    def __init__(self):
        pass

    async def generate_content(self, req: ContentGenerationRequest) -> ContentGenerationResponse:
        """
        Generates marketing copy, reel scripts, or story sequences based on the request.
        Uses Gemini LLM if key is present, with a rich Egyptian marketing copywriter fallback.
        """
        # Try Gemini LLM first if configured
        if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            try:
                llm_result = await self._generate_with_gemini(req)
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.error(f"Gemini content generation failed: {e}. Falling back to internal marketing engine.")

        # Fallback to internal high-conversion Arabic marketing templates
        return self._generate_fallback_content(req)

    async def _generate_with_gemini(self, req: ContentGenerationRequest) -> Optional[ContentGenerationResponse]:
        """Calls Google Gemini API to generate structured marketing copy."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

        prompt = self._build_gemini_prompt(req)
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1500,
            }
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                return self._parse_gemini_response(raw_text, req)
            else:
                logger.warning(f"Gemini API returned code {resp.status_code}: {resp.text}")
                return None

    def _build_gemini_prompt(self, req: ContentGenerationRequest) -> str:
        cta_word = req.cta_keyword or "ابدأ"
        audience = req.target_audience or "رواد أعمال، أصحاب مشاريع، صناع محتوى"
        
        system_instruction = (
            "أنت خبير محتوى تسويقي وCopywriter رقمي محترف متخصص في السوشيال ميديا المصرية والعربية.\n"
            "مهمتك هي كتابة محتوى يحقق أعلى نسبة تفاعل (Engagement) وتحويلات (Conversions) لصالح صفحة 'إبدأ ماركتينج - Karim Abdalwahid'.\n"
            "أسلوب الكتابة: مصري راقي، محفز، عملي، بدون حشو، مليء بالطاقة الإيجابية.\n"
            f"الجمهور المستهدف: {audience}.\n"
            f"كلمة الـ CTA المطلوبة للرد التلقائي: [{cta_word}].\n\n"
        )

        if req.post_type == PostType.REEL:
            system_instruction += (
                f"المطلوب: سيناريو ريلز (Reels Script) قصير وسريع (30-60 ثانية) عن موضوع: '{req.topic}'.\n"
                "يجب أن يتضمن:\n"
                "1. Hook بصري وكلامي صادم في أول 3 ثوانٍ.\n"
                "2. ثلاث نقاط سريعة وعملية جداً.\n"
                f"3. CTA قوي جداً في النهاية: اطلب من المشاهد كتابة كلمة '{cta_word}' في التعليقات لإرسال الدليل أو التفاصيل كاملة فوراً في الـ DM.\n"
                "4. كابشن مخصص للريلز مع هاشتاجات قوية ومناسبة.\n"
            )
        elif req.post_type == PostType.STORY:
            system_instruction += (
                f"المطلوب: سلسلة ستوري إنستغرام/فيسبوك (Story Sequence) مكونة من 4 فريمات مترابطة عن: '{req.topic}'.\n"
                "1. فريم 1: خطاف وسؤال تفاعلي (Interactive Poll / Question Sticker).\n"
                "2. فريم 2: المشكلة أو الخطأ الشائع الذي يقع فيه الأغلبية.\n"
                "3. فريم 3: الحل العملي والسر التسويقي.\n"
                f"4. فريم 4: دعوة للتفاعل (CTA) للرد على الستوري بكلمة '{cta_word}'.\n"
            )
        else:
            system_instruction += (
                f"المطلوب: منشور فيسبوك وإنستغرام متكامل واحترافي عن موضوع: '{req.topic}'.\n"
                "الهيكل المطلوب (AIDA Framework):\n"
                "- Hook قوي يجذب الانتباه من أول سطرين.\n"
                "- متن المنشور: قيمة تسويقية حقيقية، أرقام أو نصائح عملية سهلة التطبيق.\n"
                f"- Call To Action (CTA): ادعُ المتابعين لكتابة كلمة '{cta_word}' في التعليقات للحصول على التفاصيل التلقائية عبر الرسائل.\n"
                "- 5 إلى 8 هاشتاجات احترافية في النهاية.\n"
            )

        system_instruction += (
            "\nأخرج النتيجة بصيغة JSON حصراً بهذا الشكل:\n"
            "{\n"
            '  "generated_text": "النص الكامل الجاهز للنشر",\n'
            '  "suggested_hook": "الخطاف المقترح",\n'
            '  "suggested_hashtags": ["#هاشتاج1", "#هاشتاج2"],\n'
            '  "script_breakdown": {"part1": "...", "part2": "..."},\n'
            f'  "cta": "اكتب {cta_word} في الكومنتات"\n'
            "}"
        )
        return system_instruction

    def _parse_gemini_response(self, raw_text: str, req: ContentGenerationRequest) -> ContentGenerationResponse:
        """Extracts JSON structure from Gemini response with fallback formatting."""
        clean_json = raw_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(clean_json)
            return ContentGenerationResponse(
                topic=req.topic,
                post_type=req.post_type,
                platform=req.platform,
                generated_text=parsed.get("generated_text", raw_text),
                suggested_hook=parsed.get("suggested_hook"),
                suggested_hashtags=parsed.get("suggested_hashtags", []),
                script_breakdown=parsed.get("script_breakdown"),
                cta=parsed.get("cta", f"اكتب {req.cta_keyword or 'ابدأ'} في التعليقات"),
                model_used=f"Gemini ({settings.LLM_MODEL})",
            )
        except Exception:
            return ContentGenerationResponse(
                topic=req.topic,
                post_type=req.post_type,
                platform=req.platform,
                generated_text=raw_text,
                suggested_hook=raw_text.split("\n")[0] if raw_text else None,
                suggested_hashtags=["#إبدأ_ماركتينج", "#تسويق_رقمي", "#ريادة_أعمال"],
                cta=f"اكتب {req.cta_keyword or 'ابدأ'} في الكومنتات",
                model_used=f"Gemini ({settings.LLM_MODEL})",
            )

    def _generate_fallback_content(self, req: ContentGenerationRequest) -> ContentGenerationResponse:
        """High-converting internal Egyptian marketing copywriting generator."""
        topic = req.topic.strip()
        cta_word = req.cta_keyword or "ابدأ"

        if req.post_type == PostType.REEL:
            hook = f"ليه 90% من الناس بتفشل في {topic}؟ والـ 10% الباقيين بيعملوا إيه بالظبط؟ 🚀"
            script = {
                "00-03s (Hook)": f"وقف السكرول ثانية! لو إنت شغال على {topic}، الفيديو ده هيوفر عليك شهور من التوهان 🛑",
                "03-15s (Point 1)": f"أول خطأ: الاعتماد على الطرق التقليدية بدون استراتيجية واضحة تناسب جمهورك الحالي.",
                "15-30s (Point 2)": f"ثاني خطوة: استخدم أدوات الأتمتة والذكاء الاصطناعي عشان تضاعف إنتاجك وتتابع عملاءك 24/7.",
                "30-45s (Point 3)": f"ثالث سر: التركيز على القيمة الفعلية اللي العميل بيكسبها مش مجرد البيع المباشر.",
                "45-60s (CTA)": f"لو عايز خطتنا العملية لتطبيق ده خطوة بخطوة.. اكتب كلمة [{cta_word}] في الكومنتات وهبعتلك الدليل المجاني في الـ DM فوراً! 📩"
            }
            caption = (
                f"{hook}\n\n"
                f"في الفيديو ده لخصتلك أهم 3 أسرار للنجاح في {topic} بدون تعقيد.\n\n"
                f"💬 اكتب كلمة [{cta_word}] في التعليقات وهيصلك الدليل التطبيقي المجاني في رسائل الصفحة فوراً!\n\n"
                f"#ريلز #تسويق_إلكتروني #إبدأ_ماركتينج #{topic.replace(' ', '_')} #بيزنس #ذكاء_اصطناعي"
            )
            hashtags = ["#ريلز", "#تسويق_إلكتروني", "#إبدأ_ماركتينج", "#صناع_محتوى", "#أرباح"]
            return ContentGenerationResponse(
                topic=topic,
                post_type=PostType.REEL,
                platform=req.platform,
                generated_text=caption,
                suggested_hook=hook,
                suggested_hashtags=hashtags,
                script_breakdown=script,
                cta=f"اكتب [{cta_word}] في التعليقات ليصلك الدليل في الـ DM",
                model_used="HudhudRadar Reels Copywriter Pro",
            )

        elif req.post_type == PostType.STORY:
            breakdown = {
                "Frame 1 (Interactive)": f"سؤال سريع للناس الطموحة: هل بتواجه صعوبة في {topic} الفترة دي؟ (نعم جداً / محتاج خطة)",
                "Frame 2 (Pain Point)": f"الحقيقة إن معظم الناس بتضيع مجهود وميزانيات ضخمة بسبب تكرار نفس الأخطاء الشائعة في {topic}.",
                "Frame 3 (Solution)": f"السر مش في المجهود الزائد.. السر في بناء نظام ذكي بيشتغل لصالحك ويوفر وقتك بنسبة 80%!",
                "Frame 4 (Call To Action)": f"جاهز تبدأ صح؟ رد على الستوري دي بكلمة [{cta_word}] وهبعتلك أهم الأدوات اللي بنستخدمها في إبدأ ماركتينج 📩✨"
            }
            full_text = (
                "📱 تسلسل ستوري تفاعلي مقترح (4 فريمات):\n\n"
                f"1️⃣ فريم 1: {breakdown['Frame 1 (Interactive)']}\n\n"
                f"2️⃣ فريم 2: {breakdown['Frame 2 (Pain Point)']}\n\n"
                f"3️⃣ فريم 3: {breakdown['Frame 3 (Solution)']}\n\n"
                f"4️⃣ فريم 4: {breakdown['Frame 4 (Call To Action)']}"
            )
            return ContentGenerationResponse(
                topic=topic,
                post_type=PostType.STORY,
                platform=req.platform,
                generated_text=full_text,
                suggested_hook=breakdown["Frame 1 (Interactive)"],
                suggested_hashtags=["#ستوري", "#إبدأ_ماركتينج"],
                script_breakdown=breakdown,
                cta=f"رد على الستوري بكلمة [{cta_word}]",
                model_used="HudhudRadar Stories Copywriter Pro",
            )

        else:
            # Default Facebook & Instagram Feed Post
            hook = f"هل فكرت قبل كده ليه بعض الصفحات بتعمل نتائج خيالية في {topic} بينما الباقي بيعاني؟ 🤔👇"
            body = (
                f"{hook}\n\n"
                f"السر مش في الحظ، ولا في ميزانيات الإعلانات العملاقة.. السر في الـ System!\n\n"
                f"عشان تحقق أقصى استفادة من {topic}، لازم تركز على 3 حاجات أساسية:\n\n"
                f"1️⃣ فهم احتياج عميلك الحقيقي وتقديم حل مباشر لمشكلته بدون لف ودوران.\n"
                f"2️⃣ التواجد المستمر بمحتوى يقدم قيمة حقيقية تبني الثقة قبل البيع.\n"
                f"3️⃣ أتمتة الردود والمتابعة الذكية عشان متخسرش أي عميل مهتم بيبعتلك في أي وقت من اليوم.\n\n"
                f"💡 في 'إبدأ ماركتينج'، هدفنا نساعدك تحول المتابعين لعملاء فعليين بأقل مجهود وبأحدث تقنيات الـ AI.\n\n"
                f"👇 شاركنا في الكومنتات: اكتب كلمة [{cta_word}] وهيصلك دليل العملي المجاني مباشرة في رسائل الصفحة! 🚀\n\n"
                f"#إبدأ_ماركتينج #تسويق_رقمي #سوشيال_ميديا #ريادة_الأعمال #أتمتة_المبيعات #محتوى_هادف"
            )
            hashtags = ["#إبدأ_ماركتينج", "#تسويق_رقمي", "#سوشيال_ميديا", "#ريادة_الأعمال", "#أتمتة_المبيعات"]
            return ContentGenerationResponse(
                topic=topic,
                post_type=PostType.POST,
                platform=req.platform,
                generated_text=body,
                suggested_hook=hook,
                suggested_hashtags=hashtags,
                cta=f"اكتب [{cta_word}] في التعليقات للحصول على الدليل",
                model_used="HudhudRadar Post Copywriter Pro",
            )


content_engine = ContentEngine()
