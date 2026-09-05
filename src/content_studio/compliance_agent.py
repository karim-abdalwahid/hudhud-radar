"""
Ruflo-Inspired Multi-Agent Swarm: Compliance & Quality Gatekeeper Agent.
Audits draft content against Meta advertising/community policies, brand persona guidelines,
and technical platform requirements before scheduled or direct publication.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import re

from src.core.logger import logger


class ComplianceVerdict(BaseModel):
    """Typed Contract for Compliance Gatekeeper Agent output."""
    is_compliant: bool = Field(description="True if content is safe and approved for publishing")
    quality_score: int = Field(ge=0, le=100, description="Quality score from 0 to 100")
    passed_checks: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    prohibited_terms: List[str] = Field(default_factory=list)
    suggested_revision: Optional[str] = None
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ComplianceGatekeeperAgent:
    """
    Ruflo Swarm Quality Gatekeeper:
    Verifies that all outgoing posts, reels, and stories adhere to brand standards
    and platform safety rules before publication.
    """

    # Prohibited spam, deceptive, or policy-violating marketing terms
    PROHIBITED_TERMS = [
        "ارباح مضمونه", "أرباح مضمونة", "ثراء سريع", "مليونير بدون مجهود",
        "فلوس مجانا", "فلوس مجانية", "بدون رأس مال تماما واكسب ملايين",
        "مسابقة وهمية", "اكسب ايفون مجانا", "اضغط شير واكسب فورا"
    ]

    # Required or recommended high-converting CTA tokens
    RECOMMENDED_CTAS = ["ابدأ", "ابدا", "تواصل", "رسالة", "واتساب", "رقمك", "تفاصيل", "استشارة"]

    def __init__(self):
        pass

    def audit_content(
        self,
        content_text: str,
        platform: str,
        post_type: str,
        media_urls: Optional[List[str]] = None
    ) -> ComplianceVerdict:
        """
        Executes multi-step compliance evaluation on draft content.
        Returns a strongly typed ComplianceVerdict.
        """
        media_urls = media_urls or []
        warnings = []
        passed_checks = []
        prohibited_found = []
        score = 100

        clean_text = content_text.strip() if content_text else ""

        # 1. Content Length Check
        if not clean_text:
            warnings.append("نص المنشور فارغ تماماً!")
            score -= 50
        elif len(clean_text) < 15:
            warnings.append("نص المنشور قصير جداً وقد لا يحقق تفاعلاً كافياً.")
            score -= 15
        else:
            passed_checks.append("طول النص مناسب ومتوافق مع النشر.")

        if len(clean_text) > 2200 and platform.lower() in ["instagram", "both"]:
            warnings.append("النص يتجاوز الحد الأقصى لكابشن إنستغرام (2200 حرف).")
            score -= 25

        # 2. Meta Policy & Prohibited Terms Check
        text_lower = clean_text.lower()
        for term in self.PROHIBITED_TERMS:
            if term in text_lower:
                prohibited_found.append(term)
                warnings.append(f"تم اكتشاف عبارة محظورة إعلانياً أو مضللة: '{term}'")
                score -= 30

        if not prohibited_found:
            passed_checks.append("خلو المحتوى من أي عبارات مضللة أو محظورة في سياسات ميتا.")

        # 3. Instagram Media Requirement
        has_media_error = False
        if platform.lower() in ["instagram", "both"]:
            if not media_urls or len(media_urls) == 0 or not media_urls[0].strip():
                warnings.append("إنستغرام يتطلب إرفاق صورة أو فيديو صالح للنشر.")
                score -= 45
                has_media_error = True
            else:
                passed_checks.append("توفر رابط وسائط صالح لمنصة إنستغرام.")

        # 4. Call to Action (CTA) Verification
        has_cta = any(cta in text_lower for cta in self.RECOMMENDED_CTAS)
        if has_cta:
            passed_checks.append("يحتوي على دعوة واضحة لاتخاذ إجراء (CTA).")
        else:
            warnings.append("يُفضل إضافة كلمة حث على الشراء مثل 'ابدأ' أو 'تواصل معنا' لزيادة التحويلات.")
            score -= 10

        # Determine Final Compliance
        score = max(0, min(100, score))
        # Content fails if prohibited terms are present, score < 60, or missing required media
        is_compliant = (len(prohibited_found) == 0) and (score >= 60) and not has_media_error

        suggested_revision = None
        if not is_compliant and prohibited_found:
            suggested_revision = clean_text
            for term in prohibited_found:
                suggested_revision = re.sub(re.escape(term), "نتائج تسويقية مدروسة", suggested_revision)

        logger.info(
            f"Compliance audit completed for {platform}/{post_type}: "
            f"score={score}, compliant={is_compliant}, warnings={len(warnings)}"
        )

        return ComplianceVerdict(
            is_compliant=is_compliant,
            quality_score=score,
            passed_checks=passed_checks,
            warnings=warnings,
            prohibited_terms=prohibited_found,
            suggested_revision=suggested_revision
        )


compliance_gatekeeper = ComplianceGatekeeperAgent()
