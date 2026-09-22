"""
Knowledge Base, Meta Scraping & RAG Management — migrated verbatim from main.py (WS0.3).

Owned by module 'knowledge'. Registered via src/modules/knowledge/__init__.py.
Handlers are UNCHANGED — only @app.* became @router.* (same URLs).
"""
import asyncio

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

from src.knowledge.db_knowledge_base import db_knowledge_base  # per-user KB (Wave 9.8)

# --------------------------------------------------------------------
# 6.5 Knowledge Base, Meta Scraping & RAG Management
# --------------------------------------------------------------------
class SaveDocumentRequest(BaseModel):
    content: str


class CreateDocumentRequest(BaseModel):
    filename: str
    content: str


@router.post("/api/knowledge/sync-meta", tags=["Knowledge Base & RAG"])
async def sync_knowledge_from_meta(request: Request):
    """Fetches tenant posts from Facebook, Instagram, and Threads, extracting knowledge into kb_documents."""
    from datetime import datetime, timezone
    from src.modules.meta.tenant_feed_service import tenant_feed_service

    user_id = _require_session_user(request)
    posts = await tenant_feed_service.get_tenant_posts(user_id=user_id, platform="all", limit=50)

    if not posts:
        return {
            "status": "skipped",
            "message": "لم يتم العثور على منشورات في الحسابات المتصلة، أو لم يتم ربط أي حسابات بعد. اربط حساباتك أولاً ثم أعد المحاولة.",
            "synced_posts": 0,
            "filename": "social_posts_knowledge.md",
            "words_count": 0,
        }

    lines = [
        "# Social Media Knowledge Base (محتوى منشورات الحسابات المتصلة)",
        f"- **تاريخ المزامنة**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- **إجمالي المنشورات**: {len(posts)} منشور عبر منصات التواصل",
        "",
        "## محتوى المنشورات والخدمات والعروض المستخرجة:",
        "",
    ]

    total_words = 0
    for idx, p in enumerate(posts, 1):
        plat = (p.get("platform") or "social").upper()
        text = (p.get("content_text") or "").strip()
        pub_at = p.get("published_at") or ""
        permalink = p.get("permalink") or ""
        metrics = p.get("metrics") or {}
        likes = metrics.get("likes", 0)
        comments = metrics.get("comments", 0)

        if not text:
            continue

        words = len(text.split())
        total_words += words

        lines.append(f"### {idx}. منشور على [{plat}] ({pub_at[:10] if pub_at else 'مؤخراً'})")
        lines.append(f"> {text}")
        if likes or comments:
            lines.append(f"- التفاعل: {likes} إعجاب | {comments} تعليق")
        if permalink:
            lines.append(f"- الرابط: {permalink}")
        lines.append("")

    content_md = "\n".join(lines)
    filename = "social_posts_knowledge.md"

    await asyncio.to_thread(
        db_knowledge_base.save_document,
        filename,
        content_md,
        user_id,
    )

    try:
        from src.agent.knowledge_base import knowledge_base
        knowledge_base.reload()
    except Exception as e:
        logger.debug(f"Knowledge base reload notice: {e}")

    return {
        "status": "success",
        "message": f"تمت مزامنة {len(posts)} منشوراً واستخراج المعرفة منها وحفظها بنجاح!",
        "synced_posts": len(posts),
        "filename": filename,
        "words_count": total_words,
    }


def _session_user(request: Request) -> Optional[str]:
    """Returns the verified session owner id, when a session is present."""
    from src.core.auth import verify_session_token, SESSION_COOKIE_NAME
    session = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME) or "")
    return (session or {}).get("sub")


def _require_session_user(request: Request) -> str:
    """Requires the owner identity before touching tenant knowledge."""
    user_id = _session_user(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="غير مصرح")
    return str(user_id)


@router.get("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def list_knowledge_documents(request: Request):
    """Lists the session user's knowledge base documents (per-user scoping)."""
    user_id = _require_session_user(request)
    documents = await asyncio.to_thread(db_knowledge_base.list_documents, user_id)
    return {"documents": documents}


@router.get("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def get_knowledge_document(filename: str, request: Request):
    """Retrieves raw content of one of the session user's knowledge documents."""
    user_id = _require_session_user(request)
    content = await asyncio.to_thread(
        db_knowledge_base.get_document_content, filename, user_id
    )
    if content is None:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    return {"filename": filename, "content": content}


@router.put("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def update_knowledge_document(filename: str, payload: SaveDocumentRequest, request: Request):
    """Updates a document in the caller's database-backed knowledge base."""
    user_id = _require_session_user(request)
    try:
        res = await asyncio.to_thread(
            db_knowledge_base.save_document, filename, payload.content, user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res


@router.post("/api/knowledge/documents", tags=["Knowledge Base & RAG"])
async def create_knowledge_document(payload: CreateDocumentRequest, request: Request):
    """Creates a new knowledge document owned by the session user."""
    user_id = _require_session_user(request)
    try:
        res = await asyncio.to_thread(
            db_knowledge_base.save_document, payload.filename, payload.content, user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res


@router.delete("/api/knowledge/documents/{filename}", tags=["Knowledge Base & RAG"])
async def delete_knowledge_document(filename: str, request: Request):
    """Deletes one of the session user's knowledge documents."""
    user_id = _require_session_user(request)
    success = await asyncio.to_thread(db_knowledge_base.delete_document, filename, user_id)
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

    # Resolve the uploading user before reading or processing a tenant file.
    user_id = _require_session_user(request)

    try:
        file_bytes = await file.read()
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="الملف المرفوع فارغ.")

        if ext in [".md", ".txt"]:
            text_content = file_bytes.decode("utf-8", errors="replace")
            result = await asyncio.to_thread(
                document_processor.process_text_or_markdown, safe_base, text_content
            )
        elif ext == ".pdf":
            result = await asyncio.to_thread(document_processor.process_pdf, safe_base, file_bytes)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            mime = file.content_type or "image/jpeg"
            result = await document_processor.process_image_vision(safe_base, file_bytes, mime_type=mime)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"صيغة الملف غير مدعومة ({ext}). الصيغ المدعومة هي: .md, .txt, .pdf, .png, .jpg, .webp"
            )

        # Persist to the per-user database knowledge base.  Local files are
        # development-only copies; a DB failure must never be reported as a
        # successful production upload.
        try:
            filename = result.get("filename") or safe_base
            content = result.get("content") or ""
            if not content and ext in [".md", ".txt"]:
                content = text_content
            if not content:
                raise ValueError("لم يتم استخراج محتوى قابل للحفظ من الملف")
            db_result = await asyncio.to_thread(
                db_knowledge_base.save_document,
                filename,
                content,
                source="upload",
                user_id=user_id,
            )
            if db_result.get("status") != "success":
                raise ValueError("قاعدة المعرفة لم تؤكد حفظ المستند")
            result["db_saved"] = True
            result["db_chunks"] = db_result.get("chunks")
        except Exception as db_err:
            logger.error(f"KB DB persist failed for {safe_base}: {db_err}")
            raise HTTPException(
                status_code=503,
                detail="تعذر حفظ الملف في قاعدة المعرفة. لم يتم اعتباره مرفوعًا بنجاح؛ أعد المحاولة.",
            )

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
async def search_knowledge(payload: SearchKnowledgeRequest, request: Request):
    """
    Hybrid semantic search (vector + keyword RRF) scoped to the session user.
    The legacy in-memory cache is deliberately never used as a fallback because
    it has no tenant boundary.
    """
    user_id = _require_session_user(request)
    if not supabase_db.is_connected:
        raise HTTPException(
            status_code=503,
            detail="البحث في قاعدة المعرفة غير متاح مؤقتًا. لم نستخدم أي بيانات مخزنة مشتركة.",
        )

    try:
        chunks = await asyncio.to_thread(
            db_knowledge_base.search, payload.query, payload.top_k, user_id
        )
    except Exception as exc:
        logger.error(f"Tenant KB search failed for user {user_id}: {exc}")
        raise HTTPException(status_code=503, detail="تعذر البحث في قاعدة المعرفة مؤقتًا.")

    return {"status": "success", "query": payload.query, "results": [
        {"filename": fn, "score": round(score, 4), "chunk": text, "text": text}
        for score, fn, text in chunks
    ]}
