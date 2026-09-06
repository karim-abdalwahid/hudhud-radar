"""
Comprehensive Automated Tests for Knowledge Base, Meta Scraping & RAG Management.
Tests Document Management, Multi-Format Ingestion (PDF, Text, Images), AI Synthesis, and Conversational Sales Closing.
"""
import pytest
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

import pypdf
from src.main import app
from src.agent.knowledge_base import KnowledgeBaseManager, knowledge_base
from src.knowledge.meta_crawler import MetaContentCrawler, BusinessKnowledgeSynthesizer
from src.knowledge.document_processor import DocumentProcessor
from src.agent.conversation_engine import ConversationEngine


@pytest.fixture
def temp_kb(tmp_path):
    """Provides an isolated temporary knowledge base manager."""
    kb = KnowledgeBaseManager(kb_dir=str(tmp_path))
    return kb


def test_knowledge_base_crud(temp_kb):
    """Tests create, read, update, list, and delete operations on knowledge documents."""
    # 1. Create document
    res = temp_kb.save_document("test_policy.md", "# Test Policy\nThis is our customer policy.")
    assert res["status"] == "success"
    assert res["words_count"] > 0

    # 2. Read document
    content = temp_kb.get_document("test_policy.md")
    assert content is not None
    assert "customer policy" in content

    # 3. List documents
    docs = temp_kb.list_documents()
    assert len(docs) == 1
    assert docs[0]["name"] == "test_policy"

    # 4. Search relevant chunks (RAG)
    relevant = temp_kb.search_relevant_chunks("policy customer")
    assert "customer policy" in relevant

    # 5. Delete document
    deleted = temp_kb.delete_document("test_policy.md")
    assert deleted is True
    assert temp_kb.get_document("test_policy.md") is None


def test_document_processor_text(tmp_path):
    """Tests processing plain text and markdown files."""
    processor = DocumentProcessor(kb_dir=str(tmp_path))
    res = processor.process_text_or_markdown("agency_terms.txt", "نحن نقدم خدمات التسويق الرقمي وإدارة الحملات.")
    assert res["status"] == "success"
    assert (tmp_path / "agency_terms.md").exists()
    content = (tmp_path / "agency_terms.md").read_text(encoding="utf-8")
    assert "التسويق الرقمي" in content


def test_document_processor_pdf(tmp_path):
    """Tests PDF parsing and extraction into structured Markdown."""
    # Generate a simple in-memory PDF using pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    
    pdf_buffer = io.BytesIO()
    writer.write(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    processor = DocumentProcessor(kb_dir=str(tmp_path))
    res = processor.process_pdf("company_catalog.pdf", pdf_bytes)
    assert res["status"] == "success"
    assert res["pages"] == 1
    assert (tmp_path / "company_catalog.md").exists()


@pytest.mark.asyncio
async def test_document_processor_image_vision(tmp_path):
    """Tests multimodal vision extraction from images."""
    processor = DocumentProcessor(kb_dir=str(tmp_path))
    fake_image_bytes = b"fake_png_binary_data"

    # Test fallback extraction when Gemini is in offline mode
    res = await processor.process_image_vision("promo_banner.png", fake_image_bytes, mime_type="image/png")
    assert res["status"] == "success"
    assert (tmp_path / "visual_promo_banner.md").exists()
    content = (tmp_path / "visual_promo_banner.md").read_text(encoding="utf-8")
    assert "promo_banner.png" in content


@pytest.mark.asyncio
async def test_meta_crawler_and_synthesizer(tmp_path):
    """Tests historical scraping aggregation and deterministic knowledge synthesis."""
    crawler = MetaContentCrawler(access_token=None, page_id=None, instagram_id=None)
    raw_data = await crawler.fetch_all_historical_content()

    assert raw_data["facebook_posts_count"] > 0
    assert raw_data["instagram_media_count"] > 0
    assert len(raw_data["all_comments"]) > 0

    synthesizer = BusinessKnowledgeSynthesizer(kb_dir=str(tmp_path))
    result = await synthesizer.synthesize_and_save(raw_data)

    assert result["status"] == "success"
    assert (tmp_path / "business_profile.md").exists()
    assert (tmp_path / "products_and_services.md").exists()
    assert (tmp_path / "sales_scripts_and_closing.md").exists()
    assert (tmp_path / "audience_insights.md").exists()
    assert (tmp_path / "synced_meta_history.md").exists()

    bp_text = (tmp_path / "business_profile.md").read_text(encoding="utf-8")
    assert "كريم عبد الواحد" in bp_text


@pytest.mark.asyncio
async def test_conversation_engine_sales_closing():
    """Tests that ConversationEngine utilizes sales closing scripts and handles pricing questions."""
    engine = ConversationEngine()
    lead_info = {"full_name": "أحمد محمود"}

    # 1. Test pricing question
    reply, converted = await engine.generate_response(lead_info, "بكام باقة التسويق وإدارة الحسابات؟")
    assert not converted
    assert "باقات" in reply or "سعر" in reply
    assert "رقم" in reply or "تواصل" in reply  # Encourages closing/sharing contact

    # 2. Test CTA keyword 'ابدأ'
    reply_cta, converted_cta = await engine.generate_response(lead_info, "ابدأ")
    assert not converted_cta
    assert "الخطة التسويقية" in reply_cta
    assert "رقم" in reply_cta

    # 3. Test conversion when customer provides phone
    reply_conv, is_conv = await engine.generate_response(lead_info, "تمام رقمي هو 01012345678")
    assert is_conv is True
    assert "شكراً جزيلاً لمشاركتك" in reply_conv


def test_fastapi_knowledge_endpoints(client):
    """Tests FastAPI REST endpoints for knowledge documents, meta sync, and upload (authed admin)."""
    # 1. List documents
    resp = client.get("/api/knowledge/documents")
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert isinstance(docs, list)

    # 2. Create document via API
    create_resp = client.post("/api/knowledge/documents", json={
        "filename": "api_test_doc.md",
        "content": "# API Test Document\nTesting knowledge REST API."
    })
    assert create_resp.status_code == 200

    # 3. Get document
    get_resp = client.get("/api/knowledge/documents/api_test_doc.md")
    assert get_resp.status_code == 200
    assert "API Test Document" in get_resp.json()["content"]

    # 4. Update document
    put_resp = client.put("/api/knowledge/documents/api_test_doc.md", json={
        "content": "# API Test Document Updated\nUpdated content."
    })
    assert put_resp.status_code == 200

    # 5. Sync from Meta
    sync_resp = client.post("/api/knowledge/sync-meta")
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "success"

    # 6. Upload file
    file_payload = {"file": ("uploaded_test.txt", b"Uploaded via REST multipart", "text/plain")}
    upload_resp = client.post("/api/knowledge/upload", files=file_payload)
    assert upload_resp.status_code == 200

    # 7. Delete test doc
    del_resp = client.delete("/api/knowledge/documents/api_test_doc.md")
    assert del_resp.status_code == 200


def test_security_path_traversal_and_sanitization(temp_kb):
    """Verifies that path traversal attacks (../, ..\\) are blocked and sanitized."""
    from src.knowledge.utils import sanitize_safe_filename

    # Test 1: sanitize_safe_filename removes path traversal characters
    malicious_inputs = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\calc.exe",
        "/absolute/path/doc.md",
        "nested/sub/dir/file.txt",
        "valid_doc",
        "special!@#$%^&*()name.md"
    ]
    for evil in malicious_inputs:
        safe_name = sanitize_safe_filename(evil, force_md=True)
        assert ".." not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert safe_name.endswith(".md")

    # Test 2: KB operations cannot escape KB root
    temp_kb.save_document("../../evil_escape.md", "# Evil Content")
    # File should be saved inside temp_kb.kb_dir, NOT in parent directories
    assert not (temp_kb.kb_dir.parent / "evil_escape.md").exists()
    assert (temp_kb.kb_dir / "evil_escape.md").exists()

    # Test 3: Get document cannot read arbitrary files outside kb_dir
    assert temp_kb.get_document("../../../requirements.txt") is None

