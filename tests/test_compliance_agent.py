"""
Unit & Integration Tests for Ruflo-Inspired Compliance Gatekeeper Agent & Swarm Safety.
"""
import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from src.main import app
from src.content_studio.compliance_agent import ComplianceGatekeeperAgent, compliance_gatekeeper
from src.agent.scheduler import ContentScheduler
from src.content_studio.service import ContentStudioService
from src.content_studio.models import ContentPostCreate, ContentPlatform, PostType, ContentStatus


def test_compliant_post_passes():
    agent = ComplianceGatekeeperAgent()
    good_text = (
        "عايز تضاعف مبيعات شركتك وتوصل لعملاء حقيقيين في مصر والخليج؟ 🚀\n"
        "في إبدأ ماركتينج بنقدملك خطة تسويقية متكاملة وإدارة احترافية للحملات الإعلانية.\n"
        "ابدأ الآن واطلب استشارتك التسويقية المجانية عبر رسائل الصفحة!"
    )

    verdict = agent.audit_content(
        content_text=good_text,
        platform="facebook",
        post_type="post"
    )

    assert verdict.is_compliant is True
    assert verdict.quality_score >= 80
    assert len(verdict.prohibited_terms) == 0
    assert any("CTA" in check for check in verdict.passed_checks)


def test_prohibited_terms_rejected():
    agent = ComplianceGatekeeperAgent()
    bad_text = "طريقة سرية لتحقيق ثراء سريع وتحقيق أرباح مضمونة بدون مجهود وبدون رأس مال تماما واكسب ملايين!"

    verdict = agent.audit_content(
        content_text=bad_text,
        platform="facebook",
        post_type="post"
    )

    assert verdict.is_compliant is False
    assert len(verdict.prohibited_terms) > 0
    assert verdict.quality_score < 60
    assert any("محظورة" in w for w in verdict.warnings)
    assert verdict.suggested_revision is not None


def test_instagram_without_media_flagged():
    agent = ComplianceGatekeeperAgent()
    text = "ابدأ معنا رحلتك في التسويق الإلكتروني اليوم وتواصل عبر الواتساب."

    verdict = agent.audit_content(
        content_text=text,
        platform="instagram",
        post_type="post",
        media_urls=[]
    )

    assert verdict.is_compliant is False
    assert any("إنستغرام يتطلب إرفاق صورة" in w for w in verdict.warnings)


@pytest.mark.asyncio
async def test_scheduler_blocks_non_compliant_post():
    service = ContentStudioService()
    scheduler = ContentScheduler(service=service)

    # Create a scheduled post that contains prohibited claims
    post = service.create_post(
        ContentPostCreate(
            platform=ContentPlatform.FACEBOOK,
            post_type=PostType.POST,
            content_text="اكسب فلوس مجانية وثراء سريع بدون مجهود اضغط هنا!",
            status=ContentStatus.SCHEDULED,
            scheduled_for=datetime.now(timezone.utc)
        ),
        user_id="tenant-compliance",
    )

    result = await scheduler.publish_single_post(post)

    assert result["status"] == "rejected_by_compliance"
    assert "verdict" in result
    assert result["verdict"]["is_compliant"] is False

    # Check that database record was marked as failed
    updated_post = service.get_post(post.id)
    assert updated_post.status == ContentStatus.FAILED
    assert "Ruflo Compliance Rejection" in (updated_post.error_message or "")


def test_api_compliance_check_endpoint(client):
    """Uses authenticated admin client from conftest (endpoint is admin-only)."""
    payload = {
        "content_text": "ابدأ الآن وطوّر حملاتك الإعلانية مع إبدأ ماركتينج. تواصل معنا للحصول على خطة مخصصة.",
        "platform": "facebook",
        "post_type": "post"
    }

    response = client.post("/api/content/compliance-check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_compliant" in data
    assert "quality_score" in data
    assert data["is_compliant"] is True
