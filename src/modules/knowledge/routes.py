"""
Knowledge Base, Meta Scraping & RAG Management — migrated verbatim from main.py (WS0.3).

Owned by module 'knowledge'. Registered via src/modules/knowledge/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks, Response, UploadFile, File
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from src.modules.context import *  # noqa: F401,F403 — shared kernel (services, settings, caches)
from src.modules.context import (  # explicit for readability
    settings, logger, supabase_db, httpx, safe_error, _safe_error,
    content_studio_service, knowledge_base, webhook_handler,
    automations_service, agent_orchestrator, lead_service,
    identity_review_queue, statistics_engine, report_generator,
    meta_feed_sync, meta_token_manager, meta_insights_sync,
    threads_publisher, marketing_leads_sync, threads_oauth_manager,
    ai_provider_manager, content_scheduler, _verify_cron_secret,
    _meta_status_cache, META_STATUS_CACHE_TTL, _llm_status_probe,
    collect_alerts, TEMPLATES_DIR,
)

router = APIRouter()

# --------------------------------------------------------------------
# 6.5 Knowledge Base, Meta Scraping & RAG Management
# --------------------------------------------------------------------
class SaveDocumentRequest(BaseModel):
    content: str


class CreateDocumentRequest(BaseModel):
    filename: str
    content: str


@router.post("/api/knowledge/analyze-meta", tags=["Knowledge Base & RAG"])
async def analyze_meta_posts(request: Request, limit: int = Query(10, ge=1, le=40)):
    """
    Admin: runs the approved structural analyzer (Entry 021 Phase 5):
    fetches recent posts + their real comments, classifies every comment
    (CTA-response vs real-question vs complaint/spam), and saves REAL
    knowledge documents with mandatory citations. Zero guessing.
    """
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "") if request.cookies.get(SESSION_COOKIE_NAME) else None
    if not session or session.get("role") != "admin":
        raise HTTPException(status_code=403, detail="هذه العملية تتطلب صلاحيات المدير")
    from src.knowledge.meta_analyzer import meta_posts_analyzer
    result = await meta_posts_analyzer.analyze_recent(limit=limit)
    if result.get("status") == "skipped":
        raise HTTPException(status_code=400, detail=result.get("reason", "skipped"))
    return result


@router.post("/api/knowledge/sync-meta", tags=["Knowledge Base & RAG"])
async def sync_knowledge_from_meta():
    """Scrapes historical Facebook/Instagram posts, reels, and comments and synthesizes business knowledge."""
    raw_data = await meta_crawler.fetch_all_historical_content()
    res = await knowledge_synthesizer.synthesize_and_save(raw_data)
    return res


@router.get("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def list_knowledge_documents():
    """Lists all stored knowledge base documents with word count, size, and status."""
    return {"documents": knowledge_base.list_documents()}


@router.get("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def get_knowledge_document(filename: str):
    """Retrieves raw content of a specific knowledge base document."""
    content = knowledge_base.get_document(filename)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    return {"filename": filename, "content": content}


@router.put("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def update_knowledge_document(filename: str, payload: SaveDocumentRequest):
    """Updates a knowledge document and instantly reloads the AI agent's memory."""
    res = knowledge_base.save_document(filename, payload.content)
    return res


@router.post("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def create_knowledge_document(payload: CreateDocumentRequest):
    """Creates a new knowledge document and hot-reloads the agent's memory."""
    res = knowledge_base.save_document(payload.filename, payload.content)
    return res


@router.delete("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def delete_knowledge_document(filename: str):
    """Deletes a document from the knowledge base and reloads memory."""
    success = knowledge_base.delete_document(filename)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found or could not be deleted")
    return {"status": "success", "message": f"Document '{filename}' deleted successfully"}


@router.post("/api/knowledge/upload", tags=["Knowledge Base & RAG"])
async def upload_knowledge_file(request: Request, file: UploadFile = File(...)):
    """
    Multi-format file uploader:
    - .md / .txt: Parsed and stored into Knowledge Base.
    - .pdf: Extracted page-by-page and converted to structured Markdown.
    - .png / .jpg / .jpeg / .webp: Analyzed using Gemini Multimodal Vision to extract business facts.

    Audit fix (2026-09-11): the result is ALSO persisted to kb_documents with the
    uploader's user_id — previously uploads only wrote local files, so the
    database-backed knowledge base (the one the AI agent reads) never received them.
    """
    # Sanitize base filename to eliminate any directory traversal attempt
    safe_base = Path(file.filename or "upload").name
    ext = Path(safe_base).suffix.lower()

    # Resolve the uploading user (per-user knowledge ownership)
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    user_id = (session or {}).get("sub")

    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="الملف المرفوع فارغ.")

        if ext in [".md", ".txt"]:
            text_content = file_bytes.decode("utf-8", errors="replace")
            result = document_processor.process_text_or_markdown(safe_base, text_content)
        elif ext == ".pdf":
            result = document_processor.process_pdf(safe_base, file_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            mime = file.content_type or "image/jpeg"
            result = await document_processor.process_image_vision(safe_base, file_bytes, mime_type=mime)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"صيغة الملف غير مدعومة ({ext}). الصيغ المدعومة هي: .md, .txt, .pdf, .png, .jpg, .webp"
            )

        # Persist to the per-user database knowledge base (AI agent source of truth)
        try:
            from src.knowledge.db_knowledge_base import db_knowledge_base
            filename = result.get("filename") or safe_base
            content = knowledge_base.knowledge_cache.get(filename) or ""
            if not content and ext in [".md", ".txt"]:
                content = text_content
            if not content:
                doc = db_knowledge_base.get_document_content(filename)
                content = (doc or {}).get("content", "") if isinstance(doc, dict) else ""
            if content:
                db_result = db_knowledge_base.save_document(
                    filename, content, source="upload", user_id=user_id)
                result["db_saved"] = db_result.get("status") == "success"
                result["db_chunks"] = db_result.get("chunks")
        except Exception as db_err:
            logger.warning(f"KB DB persist failed for {safe_base}: {db_err}")
            result["db_saved"] = False

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing uploaded file {safe_base}: {e}")
        raise HTTPException(status_code=500, detail=f"حدث خطأ أثناء معالجة الملف: {str(e)}")


class SearchKnowledgeRequest(BaseModel):
    query: str
    top_k: int = 3


@router.post("/api/knowledge/search", tags=["Knowledge Base & RAG"])
async def search_knowledge(payload: SearchKnowledgeRequest):
    """
    Executes LEANN-inspired lightweight hybrid semantic search:
    Vector cosine similarity + keyword RRF fusion across knowledge base.
    """
    from src.knowledge.semantic_engine import semantic_engine
    if not knowledge_base.knowledge_cache:
        knowledge_base.reload()

    results = semantic_engine.hybrid_search(
        query=payload.query,
        documents=knowledge_base.knowledge_cache,
        top_k=payload.top_k
    )
    return {
        "query": payload.query,
        "results": [
            {
                "score": round(score, 4),
                "filename": filename,
                "chunk": chunk
            }
            for score, filename, chunk in results
        ]
    }
