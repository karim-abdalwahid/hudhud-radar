"""
Conversational Engine for generating compliant, human-like AI responses.
Enforces brand voice, checks 24-hr window, applies sales closing tactics, and leverages RAG retrieval.
"""
import asyncio
import re
from typing import Dict, Any, Optional, Tuple
import httpx
from src.config import settings
from src.core.logger import logger
from src.agent.knowledge_base import knowledge_base

EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+', re.IGNORECASE)
PHONE_REGEX = re.compile(r'(\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9})')


class ConversationEngine:
    """Generates context-aware responses adhering to business rules and sales closing strategies."""

    def __init__(self, kb=knowledge_base):
        self.kb = kb

    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Detects if lead provided an email or phone number in their message."""
        email_match = EMAIL_REGEX.search(text)
        phone_match = PHONE_REGEX.search(text)

        found_phone = None
        if phone_match:
            candidate = phone_match.group(0).strip()
            digits = re.sub(r'\D', '', candidate)
            if len(digits) >= 8:
                found_phone = candidate

        return {
            "email": email_match.group(0) if email_match else None,
            "phone": found_phone
        }

    async def generate_response(
        self,
        lead_data: Dict[str, Any],
        incoming_message: str,
        conversation_history: list = None
    ) -> Tuple[str, bool]:
        """
        Generates a human-like reply based on the knowledge base and conversation context.
        Returns: (reply_text, is_converted_lead)
        """
        extracted = self.extract_contact_info(incoming_message)
        is_converted = bool(extracted["email"] or extracted["phone"])
        lead_name = lead_data.get("full_name") or lead_data.get("username") or "صديقنا"

        # Case 1: Lead shared their contact details (Conversion Completed!)
        if is_converted:
            reply = (
                f"أهلاً بك يا {lead_name}، شكراً جزيلاً لمشاركتك وسيلة التواصل! "
                f"قام فريقنا بتسجيل بياناتك بنجاح، وسيتواصل معك مستشارنا المختص في أقرب وقت لتزويدك بكافة التفاصيل والبدء معاً."
            )
            return reply, True

        # Case 2: Use Gemini LLM with dynamic RAG context
        if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            try:
                llm_reply = await self._call_gemini_api(lead_data, incoming_message, conversation_history)
                if llm_reply:
                    return llm_reply, False
            except Exception as e:
                logger.error(f"Error invoking Gemini API: {e}. Falling back to knowledge-base heuristic.")

        # Case 3: Knowledge Base / Context Heuristics & Closing Tactics (Offline mode)
        msg_lower = incoming_message.lower().strip()

        # Trigger 1: Lead replied with "ابدأ" or "start" (Reels CTA)
        if msg_lower in ["ابدأ", "ابدا", "start", "مهتم"]:
            return (
                f"أهلاً بك يا {lead_name}! شرفتنا بتفاعلك 🚀 "
                f"حابب نعرف أكتر عن اللي محتاجه ونرسل لك التفاصيل المناسبة. "
                f"ممكن تشاركنا رقم هاتفك أو بريدك الإلكتروني للمتابعة معك فوراً؟"
            ), False

        # Trigger 2: Pricing / Cost inquiry
        if any(w in msg_lower for w in ["سعر", "اسعار", "أسعار", "بكم", "بكام", "كام", "تكلفة", "اشتراك", "اشتراكات", "باقة", "باقات", "عروض", "cost", "price"]):
            return (
                f"أهلاً بك يا {lead_name}! شكراً لاهتمامك. "
                f"التفاصيل والأسعار بتختلف حسب احتياجك — عشان نرسل لك العرض الأنسب بالظبط، "
                f"ما هي وسيلة التواصل الأنسب لك (رقم هاتف أو واتساب)؟"
            ), False

        # Trigger 3: Services inquiry
        if any(w in msg_lower for w in ["خدمات", "ايش تقدمون", "ماذا تقدمون", "خدمتكم", "services", "بتعملوا ايه"]):
            return (
                f"أهلاً بك {lead_name}! يسعدنا توضيح خدماتنا — حسب قاعدة معرفتنا الحالية:\n"
                f"{self.kb.get_sales_closing_context()[:600] or 'أخبرنا باحتياجك بالتفصيل وسنرد عليك بكل التفاصيل.'}\n"
                f"ما هو الهدف الأهم لحسابك حالياً؟"
            ), False

        # Default friendly response adhering to brand tone & inviting consultation
        return (
            f"مرحباً بك {lead_name}! يسعدنا تواصلك معنا. "
            f"كيف يمكننا مساعدتك اليوم؟"
        ), False

    async def _call_gemini_api(self, lead_data: Dict[str, Any], message: str, history: list) -> Optional[str]:
        """Calls Google Gemini API with multi-turn conversation memory + RAG context."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": settings.GEMINI_API_KEY,
        }

        # Dynamic RAG context
        rag_context = self.kb.search_relevant_chunks(message, top_k=3)
        sales_tactics = self.kb.get_sales_closing_context()

        system_prompt = (
            "أنت المساعد الذكي الرسمي المسؤول عن إدارة محادثات العملاء لحساب التواصل الاجتماعي المتصل بهذه المنصة.\n"
            "مهمتك الرئيسية:\n"
            "1. التعامل مع العميل بأسلوب إنساني وودود وواثق واحترافي.\n"
            "2. الرد على استفساراته بالاعتماد فقط على معلومات النشاط التجاري المذكورة أدناه دون اختلاق أي معلومات غير موجودة.\n"
            "3. تطبيق تكتيكات إغلاق المبيعات (Sales Closing): إبراز القيمة، طمأنة العميل، وتوجيهه لمشاركة وسيلة تواصله (رقم هاتف أو بريد) لحجز استشارة أو تلقي العرض.\n"
            "4. إذا سأل العميل عن السعر، وضح وجود باقات مخصصة واطلب رقم التواصل لتحديد الأنسب له.\n"
            "5. المحتوى يعود لصاحب الحساب المتصل — لا ترتبط المنصة نفسها بالبيزنس ولا تذكر اسمها في الردود.\n\n"
            f"--- سياق قاعدة المعرفة المسترجع (RAG Context) ---\n{rag_context}\n\n"
            f"--- تكتيكات البيع المعتمدة ---\n{sales_tactics}"
        )

        # Multi-turn conversation memory: include real prior turns (most recent first, capped)
        contents = []
        prior_turns = [
            m for m in (history or [])[:-1]  # exclude the just-stored duplicate of the current message
            if (m.get("content") or "").strip()
        ]
        for turn in prior_turns[-8:]:
            role = "model" if turn.get("sender_type") == "agent" else "user"
            contents.append({"role": role, "parts": [{"text": turn["content"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
                # Thinking tokens consume the output budget on flash-latest models.
                "thinkingConfig": {"thinkingBudget": 0},
            }
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = None
            for attempt in range(3):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                except httpx.RequestError:
                    resp = None
                if resp is not None and resp.status_code == 200:
                    break
                if resp is None or resp.status_code not in (500, 502, 503, 504):
                    break
                await asyncio.sleep(1.0 * (attempt + 1))
            if resp is not None and resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates") or []
                parts = (candidates[0].get("content") or {}).get("parts") if candidates else None
                text = "".join(p.get("text", "") for p in (parts or []) if isinstance(p, dict)).strip()
                return text or None
            else:
                logger.warning(f"Gemini API returned code {resp.status_code if resp is not None else 'network'}: {resp.text[:200] if resp is not None else 'request error'}")
        return None


conversation_engine = ConversationEngine()
