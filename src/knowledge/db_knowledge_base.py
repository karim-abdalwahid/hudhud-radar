"""
Database-backed Knowledge Base with pgvector hybrid RAG (Phase 5, approved).

Replaces the markdown-file KB (which broke on Vercel's read-only FS) with:
- kb_documents / kb_chunks tables (migration 003/003b)
- Gemini text-embedding-004 embeddings (768 dims) at ingest time
- Hybrid search via Postgres RPC `match_kb_chunks` (cosine + tsvector + RRF)

The legacy in-memory semantic engine remains as a local-dev fallback when
Supabase is disconnected.
"""
import hashlib
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db

GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
)
EMBED_DIMS = 3072
CHUNK_MAX_CHARS = 900
CHUNK_OVERLAP_CHARS = 120


class DBKnowledgeBase:
    """CRUD + chunking + embedding + hybrid search over Supabase pgvector."""

    def __init__(self):
        self._embed_cache: Dict[str, List[float]] = {}

    # ------------------------------------------------------------------
    # Gemini embeddings
    # ------------------------------------------------------------------
    def _embed(self, text: str) -> Optional[List[float]]:
        """Returns a 768-dim embedding for text via Gemini, with a small cache."""
        key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if key in self._embed_cache:
            return self._embed_cache[key]
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY missing — cannot embed; chunk will be keyword-only")
            return None
        try:
            r = httpx.post(
                GEMINI_EMBED_URL,
                headers={"Content-Type": "application/json", "X-goog-api-key": settings.GEMINI_API_KEY},
                json={
                    "model": "models/gemini-embedding-001",
                    "content": {"parts": [{"text": text[:6000]}]},
                },
                timeout=20.0,
            )
            if r.status_code == 200:
                vec = r.json().get("embedding", {}).get("values")
                if vec and len(vec) == EMBED_DIMS:
                    self._embed_cache[key] = vec
                    return vec
            logger.warning(f"Gemini embedding failed: {r.status_code} {r.text[:150]}")
        except Exception as e:
            logger.warning(f"Gemini embedding error: {e}")
        return None

    # ------------------------------------------------------------------
    # Chunking (paragraph-aware, fixed-size with overlap)
    # ------------------------------------------------------------------
    def _chunk_text(self, text: str) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        # Prefer markdown/paragraph boundaries
        blocks = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        buf = ""
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if len(buf) + len(block) + 2 <= CHUNK_MAX_CHARS:
                buf = f"{buf}\n\n{block}" if buf else block
                continue
            if buf:
                chunks.append(buf)
            if len(block) <= CHUNK_MAX_CHARS:
                buf = block
            else:
                # hard-split very long block with overlap
                start = 0
                while start < len(block):
                    piece = block[start:start + CHUNK_MAX_CHARS]
                    chunks.append(piece)
                    if start + CHUNK_MAX_CHARS >= len(block):
                        break
                    start += CHUNK_MAX_CHARS - CHUNK_OVERLAP_CHARS
                buf = ""
        if buf:
            chunks.append(buf)
        return chunks or ([text] if text else [])

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------
    def save_document(self, filename: str, content: str, source: str = "upload",
                      user_id: Optional[str] = None, is_core: bool = False) -> Dict[str, Any]:
        filename = self._safe_filename(filename)
        content = (content or "").strip()
        if not filename or not content:
            raise ValueError("اسم الملف والمحتوى مطلوبان")

        # Upsert document (unique filename)
        try:
            doc = supabase_db.upsert("kb_documents", {
                "filename": filename,
                "content": content,
                "source": source,
                "word_count": len(content.split()),
                "is_core": is_core,
                **({"user_id": user_id} if user_id else {}),
            }, on_conflict="filename")
        except Exception as e:
            raise ValueError(f"تعذر حفظ المستند: {e}")

        doc_id = doc["id"]
        # Re-chunk + embed
        self._delete_chunks(doc_id)
        chunks = self._chunk_text(content)
        for idx, chunk in enumerate(chunks):
            vec = self._embed(chunk)
            payload: Dict[str, Any] = {
                "document_id": doc_id,
                "chunk_index": idx,
                "chunk_text": chunk,
            }
            if vec:
                payload["embedding"] = vec
            try:
                supabase_db.insert("kb_chunks", payload)
            except Exception as e:
                logger.warning(f"Chunk insert failed (doc={filename} idx={idx}): {e}")

        logger.info(f"KB document saved: {filename} ({len(chunks)} chunks, embedded={bool(chunks and vec)})")
        return {"status": "success", "filename": filename, "chunks": len(chunks),
                "embedded": all(self._embed(c) is not None for c in chunks[:1])}

    def get_document(self, filename: str) -> Optional[Dict[str, Any]]:
        try:
            rows = supabase_db.select("kb_documents", {"filename": self._safe_filename(filename)})
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"KB get_document failed: {e}")
            return None

    def get_document_content(self, filename: str) -> Optional[str]:
        doc = self.get_document(filename)
        return doc["content"] if doc else None

    def list_documents(self) -> List[Dict[str, Any]]:
        try:
            docs = supabase_db.select("kb_documents") or []
            docs.sort(key=lambda d: (not d.get("is_core", False), d.get("filename", "")))
            return [
                {
                    "filename": d["filename"],
                    "word_count": d.get("word_count", 0),
                    "source": d.get("source", "upload"),
                    "is_core": d.get("is_core", False),
                    "updated_at": d.get("updated_at"),
                }
                for d in docs
            ]
        except Exception as e:
            logger.error(f"KB list_documents failed: {e}")
            return []

    def delete_document(self, filename: str) -> bool:
        doc = self.get_document(filename)
        if not doc:
            return False
        self._delete_chunks(doc["id"])
        try:
            supabase_db.delete("kb_documents", doc["id"])
            return True
        except Exception as e:
            logger.error(f"KB delete failed: {e}")
            return False

    def _delete_chunks(self, doc_id: str):
        try:
            if supabase_db.is_connected and supabase_db.client:
                supabase_db.client.table("kb_chunks").delete().eq("document_id", doc_id).execute()
        except Exception as e:
            logger.warning(f"Chunk delete failed for doc {doc_id}: {e}")

    def _safe_filename(self, name: str) -> str:
        name = (name or "").strip()
        name = re.sub(r"[^\w\u0600-\u06FF.\- ]", "", name)
        name = name.replace(" ", "_")
        if not name.endswith(".md"):
            name += ".md"
        return name.lstrip("._")

    # ------------------------------------------------------------------
    # Hybrid search (Postgres RPC; keyword-only fallback)
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5) -> List[Tuple[float, str, str]]:
        """Returns [(score, filename, chunk_text), ...] via hybrid RRF search."""
        if not query.strip():
            return []
        try:
            if not (supabase_db.is_connected and supabase_db.client):
                return self._fallback_keyword_search(query, top_k)
            qvec = self._embed(query)
            params: Dict[str, Any] = {"query_text": query, "match_count": top_k}
            if qvec:
                params["query_embedding"] = qvec
            else:
                # keyword-only: pass null embedding
                params["query_embedding"] = None
            res = supabase_db.client.rpc("match_kb_chunks", params).execute()
            rows = res.data or []
            return [(r["score"], r["filename"], r["chunk_text"]) for r in rows]
        except Exception as e:
            logger.warning(f"Hybrid search failed, keyword fallback: {e}")
            return self._fallback_keyword_search(query, top_k)

    def _fallback_keyword_search(self, query: str, top_k: int) -> List[Tuple[float, str, str]]:
        """Simple ILIKE scoring over kb_documents.content (no RPC needed)."""
        results: List[Tuple[float, str, str]] = []
        try:
            docs = supabase_db.select("kb_documents") or []
            terms = [t for t in re.split(r"\s+", query.lower()) if len(t) > 1]
            for d in docs:
                content = d.get("content") or ""
                score = sum(content.lower().count(t) for t in terms)
                if score > 0:
                    start = max(0, content.lower().find(terms[0]) - 100) if terms else 0
                    results.append((float(score), d["filename"], content[start:start + 400]))
            results.sort(key=lambda x: x[0], reverse=True)
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
        return results[:top_k]

    # ------------------------------------------------------------------
    # Context builders (used by conversation engine — same interface as before)
    # ------------------------------------------------------------------
    def search_context(self, query: str, top_k: int = 3) -> str:
        results = self.search(query, top_k=top_k)
        if not results:
            return ""
        parts = []
        for score, filename, chunk in results:
            parts.append(f"[من وثيقة: {filename}]\n{chunk}")
        return "\n---\n".join(parts)

    def sales_context(self) -> str:
        """Concatenates conversion-critical docs (same trio as the file-based KB)."""
        out = []
        for name in ("sales_scripts_and_closing.md", "products_and_services.md", "business_profile.md"):
            doc = self.get_document_content(name)
            if doc:
                out.append(f"--- {name} ---\n{doc}")
        return "\n\n".join(out)


db_knowledge_base = DBKnowledgeBase()
