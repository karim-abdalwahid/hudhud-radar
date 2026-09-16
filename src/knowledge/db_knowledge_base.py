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
GEMINI_BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents"
)
EMBED_DIMS = 3072
EMBED_BATCH_SIZE = 32
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
        """Returns a 3072-dim embedding for text via Gemini, with a small cache."""
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

    def _embed_many(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Embeds uncached chunks in bounded Gemini batch requests.

        Gemini's ``batchEmbedContents`` returns vectors in the same order as
        submitted requests.  Using it reduces a large PDF upload from one HTTP
        request per chunk to one request per bounded batch; callers run this
        synchronous adapter in a worker thread, never in the ASGI event loop.
        """
        vectors: List[Optional[List[float]]] = [None] * len(texts)
        if not texts:
            return vectors

        missing: List[Tuple[int, str, str]] = []
        for index, text in enumerate(texts):
            key = hashlib.md5(text.encode("utf-8")).hexdigest()
            cached = self._embed_cache.get(key)
            if cached:
                vectors[index] = cached
            else:
                missing.append((index, text, key))

        if not missing or not settings.GEMINI_API_KEY:
            return vectors

        for offset in range(0, len(missing), EMBED_BATCH_SIZE):
            batch = missing[offset:offset + EMBED_BATCH_SIZE]
            try:
                response = httpx.post(
                    GEMINI_BATCH_EMBED_URL,
                    headers={"Content-Type": "application/json", "X-goog-api-key": settings.GEMINI_API_KEY},
                    json={
                        "requests": [
                            {
                                "model": "models/gemini-embedding-001",
                                "content": {"parts": [{"text": text[:6000]}]},
                            }
                            for _, text, _ in batch
                        ]
                    },
                    timeout=30.0,
                )
                returned = response.json().get("embeddings", []) if response.status_code == 200 else []
                if len(returned) != len(batch):
                    raise ValueError(
                        f"Gemini returned {len(returned)} embeddings for a batch of {len(batch)}"
                    )
                for (index, _text, key), embedding in zip(batch, returned):
                    vector = embedding.get("values") if isinstance(embedding, dict) else None
                    if vector and len(vector) == EMBED_DIMS:
                        vectors[index] = vector
                        self._embed_cache[key] = vector
                    else:
                        logger.warning("Gemini batch embedding returned an invalid vector dimension")
            except Exception as exc:
                logger.warning("Gemini batch embedding failed; retrying this batch per chunk: %s", exc)
                # Retain availability if batch support is unavailable for a
                # configured project/model.  This runs in the worker thread.
                for index, text, _key in batch:
                    vectors[index] = self._embed(text)

        return vectors

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
    # Document CRUD (tenant-owned; no legacy global documents in production)
    # ------------------------------------------------------------------
    def save_document(self, filename: str, content: str, source: str = "upload",
                      user_id: Optional[str] = None, is_core: bool = False) -> Dict[str, Any]:
        filename = self._safe_filename(filename)
        content = (content or "").strip()
        if not filename or not content:
            raise ValueError("اسم الملف والمحتوى مطلوبان")
        if not user_id:
            raise ValueError("مالك قاعدة المعرفة مطلوب")

        # Per-user upsert: filename uniqueness is scoped to (user_id, filename)
        # since migration 017 — so we select-then-insert/update manually.
        try:
            if supabase_db.is_connected and supabase_db.client:
                q = supabase_db.client.table("kb_documents").select("id").eq(
                    "filename", filename)
                q = q.eq("user_id", user_id)
                existing = q.execute().data or []
            else:
                existing = [r for r in supabase_db.memory_db.tables.get("kb_documents", [])
                            if r.get("filename") == filename
                            and r.get("user_id") == user_id
                            and "id" in r]
                existing = existing[:1]
        except Exception as e:
            raise ValueError(f"تعذر التحقق من المستند: {e}")

        payload = {
            "filename": filename,
            "content": content,
            "source": source,
            "word_count": len(content.split()),
            "is_core": is_core,
            "user_id": user_id,
        }
        try:
            if existing:
                doc = supabase_db.update("kb_documents", existing[0]["id"], payload)
            else:
                doc = supabase_db.insert("kb_documents", payload)
        except Exception as e:
            raise ValueError(f"تعذر حفظ المستند: {e}")

        doc_id = doc["id"]
        # Re-chunk + embed
        self._delete_chunks(doc_id)
        chunks = self._chunk_text(content)
        embedded_count = 0
        vectors = self._embed_many(chunks)
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
            payload: Dict[str, Any] = {
                "document_id": doc_id,
                "chunk_index": idx,
                "chunk_text": chunk,
            }
            if vec:
                payload["embedding"] = vec
                embedded_count += 1
            try:
                supabase_db.insert("kb_chunks", payload)
            except Exception as e:
                logger.warning(f"Chunk insert failed (doc={filename} idx={idx}): {e}")

        # HONEST embedded flag: true only when EVERY chunk has a real vector
        fully_embedded = bool(chunks) and embedded_count == len(chunks)
        if chunks and not fully_embedded:
            logger.warning(f"KB document {filename}: partial embedding ({embedded_count}/{len(chunks)} chunks) — hybrid search will degrade to keyword for missing vectors")
        logger.info(f"KB document saved: {filename} ({len(chunks)} chunks, embedded={embedded_count}/{len(chunks)}, user={user_id or 'legacy'})")
        return {"status": "success", "filename": filename, "chunks": len(chunks),
                "embedded": fully_embedded, "embedded_chunks": embedded_count}

    def get_document(self, filename: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        try:
            if supabase_db.is_connected and supabase_db.client:
                q = supabase_db.client.table("kb_documents").select("*").eq(
                    "filename", self._safe_filename(filename))
                q = q.eq("user_id", user_id)
                rows = q.execute().data or []
                return rows[0] if rows else None
            rows = [r for r in supabase_db.memory_db.tables.get("kb_documents", [])
                    if r.get("filename") == self._safe_filename(filename)
                    and r.get("user_id") == user_id]
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"KB get_document failed: {e}")
            return None

    def get_document_content(self, filename: str, user_id: Optional[str] = None) -> Optional[str]:
        doc = self.get_document(filename, user_id=user_id)
        return doc["content"] if doc else None

    def list_documents(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not user_id:
            return []
        try:
            if supabase_db.is_connected and supabase_db.client:
                q = supabase_db.client.table("kb_documents").select(
                    "filename,word_count,source,is_core,updated_at")
                q = q.eq("user_id", user_id)
                docs = q.execute().data or []
            else:
                docs = [r for r in supabase_db.memory_db.tables.get("kb_documents", [])
                        if r.get("user_id") == user_id]
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

    def delete_document(self, filename: str, user_id: Optional[str] = None) -> bool:
        doc = self.get_document(filename, user_id=user_id)
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
    def search(self, query: str, top_k: int = 5,
               user_id: Optional[str] = None) -> List[Tuple[float, str, str]]:
        """Returns [(score, filename, chunk_text), ...] via hybrid RRF search.
        user_id scopes results to that user's documents (Wave 9.8)."""
        if not query.strip():
            return []
        if not user_id:
            logger.warning("KB search skipped because tenant user_id is missing (fail-closed).")
            return []
        try:
            if not (supabase_db.is_connected and supabase_db.client):
                return self._fallback_keyword_search(query, top_k, user_id=user_id)
            qvec = self._embed(query)
            if not qvec:
                # ``embedding <=> NULL`` cannot produce a meaningful semantic
                # ranking.  Do an explicitly scoped keyword-only search rather
                # than letting the RPC assign arbitrary semantic row numbers.
                logger.info("Query embedding unavailable; using tenant-scoped keyword search only.")
                return self._fallback_keyword_search(query, top_k, user_id=user_id)
            params: Dict[str, Any] = {"query_text": query, "match_count": top_k}
            params["query_embedding"] = qvec
            params["p_user_id"] = user_id
            res = supabase_db.client.rpc("match_kb_chunks", params).execute()
            rows = res.data or []
            return [(r["score"], r["filename"], r["chunk_text"]) for r in rows]
        except Exception as e:
            logger.warning(f"Hybrid search failed, keyword fallback: {e}")
            return self._fallback_keyword_search(query, top_k, user_id=user_id)

    def _fallback_keyword_search(self, query: str, top_k: int,
                                 user_id: Optional[str] = None) -> List[Tuple[float, str, str]]:
        """Simple ILIKE scoring over kb_documents.content (no RPC needed)."""
        results: List[Tuple[float, str, str]] = []
        try:
            if supabase_db.is_connected and supabase_db.client:
                q = supabase_db.client.table("kb_documents").select("filename,content")
                q = q.eq("user_id", user_id)
                docs = q.execute().data or []
            else:
                docs = [r for r in supabase_db.memory_db.tables.get("kb_documents", [])
                        if r.get("user_id") == user_id]
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
    def search_context(self, query: str, top_k: int = 3,
                       user_id: Optional[str] = None) -> str:
        results = self.search(query, top_k=top_k, user_id=user_id)
        if not results:
            return ""
        parts = []
        for score, filename, chunk in results:
            parts.append(f"[من وثيقة: {filename}]\n{chunk}")
        return "\n---\n".join(parts)

    def sales_context(self, user_id: Optional[str] = None) -> str:
        """Concatenates conversion-critical docs (same trio as the file-based KB)."""
        out = []
        for name in ("sales_scripts_and_closing.md", "products_and_services.md", "business_profile.md"):
            doc = self.get_document_content(name, user_id=user_id)
            if doc:
                out.append(f"--- {name} ---\n{doc}")
        return "\n\n".join(out)


db_knowledge_base = DBKnowledgeBase()
