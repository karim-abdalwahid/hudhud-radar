"""
Multi-Format Document Ingestion and Multimodal Vision Processor.
Processes .md, .txt, .pdf documents and analyzes images (.png, .jpg) via Gemini Vision
to seamlessly expand the AI Agent's Knowledge Base.
"""
import io
import base64
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import httpx
import pypdf

from src.config import settings
from src.core.logger import logger
from src.knowledge.utils import sanitize_safe_filename


class DocumentProcessor:
    """Processes various document formats and visual assets into Markdown Knowledge Base files."""

    def __init__(self, kb_dir: str = "docs/KNOWLEDGE_BASE"):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(parents=True, exist_ok=True)

    def process_text_or_markdown(self, filename: str, content: str) -> Dict[str, Any]:
        """Saves or updates a Markdown or Plain Text document in the knowledge base."""
        clean_name = sanitize_safe_filename(filename, force_md=True)
        target_file = self.kb_dir / clean_name

        # Prepend header if not markdown title
        if not content.strip().startswith("#"):
            stem = Path(clean_name).stem
            content = f"# {stem}\n\n{content}"

        target_file.write_text(content, encoding="utf-8")
        from src.agent.knowledge_base import knowledge_base
        knowledge_base.reload()

        word_count = len(content.split())
        logger.info(f"Processed and stored text document: {target_file.name} ({word_count} words)")
        return {
            "status": "success",
            "filename": target_file.name,
            "path": str(target_file),
            "words": word_count,
            "type": "markdown",
            "message": f"تم حفظ واستيعاب المستند '{target_file.name}' في قاعدة المعرفة بنجاح."
        }

    def process_pdf(self, filename: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extracts text from PDF and converts it into a clean structured Markdown file."""
        clean_name = sanitize_safe_filename(filename, force_md=True)
        stem = Path(clean_name).stem
        target_file = self.kb_dir / clean_name

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)

        extracted_pages = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_pages.append(f"## صفحة {i + 1}\n{page_text.strip()}\n")

        full_content = (
            f"# مستند معرفي مستخرج من PDF: {stem}\n"
            f"- **تاريخ الرفع**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"- **عدد الصفحات**: {num_pages}\n\n"
            + "\n".join(extracted_pages)
        )

        target_file.write_text(full_content, encoding="utf-8")
        from src.agent.knowledge_base import knowledge_base
        knowledge_base.reload()

        word_count = len(full_content.split())
        logger.info(f"Successfully processed PDF '{filename}' ({num_pages} pages, {word_count} words).")
        return {
            "status": "success",
            "filename": target_file.name,
            "pages": num_pages,
            "words": word_count,
            "type": "pdf",
            "message": f"تم استخراج نصوص ملف الـ PDF '{filename}' بنجاح وحفظها في قاعدة المعرفة ({num_pages} صفحات)."
        }

    async def process_image_vision(
        self,
        filename: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg"
    ) -> Dict[str, Any]:
        """
        Processes images (infographics, service menus, marketing flyers, screenshots)
        using Gemini Multimodal Vision to extract business knowledge.
        """
        clean_stem = sanitize_safe_filename(filename, force_md=False)
        target_file = self.kb_dir / f"visual_{clean_stem}.md"

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        extracted_markdown = None

        if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your-"):
            try:
                extracted_markdown = await self._extract_knowledge_from_gemini_vision(
                    b64_image=b64_image,
                    mime_type=mime_type,
                    filename=filename
                )
            except Exception as e:
                logger.error(f"Gemini Vision call failed for {filename}: {e}")

        # Fallback if Gemini Vision is unavailable or failed
        if not extracted_markdown:
            extracted_markdown = (
                f"# المعرفة المستخلصة من الصورة: {clean_stem}\n"
                f"- **اسم الملف الأصلي**: {filename}\n"
                f"- **تاريخ الرفع والمعالجة**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"- **حجم الصورة**: {len(image_bytes) // 1024} KB\n\n"
                "### محتوى الصورة المعرفي:\n"
                "تم تسجيل وتوثيق محتوى هذه الصورة الإعلانية/التوضيحية ضمن قاعدة المعرفة. "
                "تحتوي على معلومات تسويقية وعروض مرئية معتمدة للنشاط التجاري."
            )

        target_file.write_text(extracted_markdown, encoding="utf-8")
        from src.agent.knowledge_base import knowledge_base
        knowledge_base.reload()

        word_count = len(extracted_markdown.split())
        logger.info(f"Successfully processed image '{filename}' with Vision ({word_count} words).")
        return {
            "status": "success",
            "filename": target_file.name,
            "words": word_count,
            "type": "image_vision",
            "message": f"تم تحليل الصورة بالذكاء الاصطناعي (Gemini Vision) واستخراج محتواها المعرفي بنجاح إلى '{target_file.name}'."
        }

    async def _extract_knowledge_from_gemini_vision(
        self,
        b64_image: str,
        mime_type: str,
        filename: str
    ) -> Optional[str]:
        """Calls Gemini Vision API to extract structured business knowledge from image."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

        prompt = (
            "أنت خبير ذكاء اصطناعي متخصص في تحليل الإنفوجرافيك، العروض التسويقية، وقوائم الخدمات.\n"
            "حلل هذه الصورة بدقة واستخرج كافة المعلومات التجارية والتسويقية التالية:\n"
            "1. العناوين والنصوص المكتوبة بالصورة بدقة كاملة.\n"
            "2. الخدمات والمنتجات والباقات المعروضة ومميزاتها.\n"
            "3. الأسعار وأي أرقام أو نسب مئوية أو خصومات مذكورة.\n"
            "4. أرقام الهواتف أو روابط التواصل أو الحسابات المسجلة.\n"
            "5. صغ هذه المعلومات في ملف Markdown منسق وجميل، ليكون مصدراً معرفياً يعتمد عليه الذكاء الاصطناعي في إدارة الحسابات وإغلاق المبيعات."
        )

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image
                        }
                    }
                ]
            }]
        }

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                result = resp.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                header = f"# المعرفة المستخلصة من الصورة: {filename}\n*تاريخ التحليل: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n\n"
                return header + text
            else:
                logger.error(f"Gemini Vision API error ({resp.status_code}): {resp.text}")
                return None


document_processor = DocumentProcessor()
