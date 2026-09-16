"""
Knowledge Base Ingestion, Management, and RAG Context Provider.

Two modes:
- **DB mode (default)**: kb_documents + kb_chunks with pgvector hybrid RAG
  (Gemini embeddings + full-text + RRF) via `DBKnowledgeBase`. Survives
  Vercel's read-only filesystem — approved in Roadmap v2 Phase 5.
- **File mode**: legacy markdown directory storage, used when an explicit
  kb_dir is passed (tests) or when Supabase is disconnected (local dev).
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import re
from datetime import datetime, timezone
from src.core.logger import logger
from src.knowledge.utils import sanitize_safe_filename


class KnowledgeBaseManager:
    """Reads, manages, and structures knowledge documents for AI context & RAG."""

    def __init__(self, kb_dir: Optional[str] = None):
        if kb_dir:
            self.kb_dir = Path(kb_dir)
        else:
            self.kb_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "KNOWLEDGE_BASE"
        try:
            self.kb_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.knowledge_cache: Dict[str, str] = {}
        # Mode resolution: explicit dir = file mode; otherwise DB when connected
        self._mode = "file"
        if kb_dir is None:
            try:
                from src.core.supabase_client import supabase_db
                if supabase_db.is_connected:
                    self._mode = "db"
            except Exception:
                self._mode = "file"
        self.reload()

    # ------------------------------------------------------------------
    # Reload / listing
    # ------------------------------------------------------------------
    def reload(self):
        """Reloads legacy file-mode documents only.

        Production documents are tenant-owned.  Loading the entire
        ``kb_documents`` table into one process cache is both inefficient and
        unsafe: equal filenames collide and an outage could expose another
        tenant through a fallback.  DB-mode retrieval therefore always goes
        through :class:`DBKnowledgeBase` with an explicit owner id.
        """
        self.knowledge_cache.clear()

        if self._mode == "db":
            logger.info("Global KB cache disabled in DB mode; tenant retrieval is database-scoped.")
            return

        if not self.kb_dir.exists():
            logger.warning(f"Knowledge Base directory '{self.kb_dir}' not found.")
            return

        for md_file in sorted(self.kb_dir.glob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                self.knowledge_cache[md_file.name] = content
                logger.info(f"Loaded Knowledge Base document: {md_file.name}")
            except Exception as e:
                logger.error(f"Error loading {md_file}: {e}")

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns metadata of all knowledge base documents for UI explorer."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                docs = []
                for d in db_knowledge_base.list_documents():
                    content = d  # light rows only; fetch preview lazily below
                    docs.append({
                        "name": d["filename"].removesuffix(".md"),
                        "filename": d["filename"],
                        "size_bytes": len(self.knowledge_cache.get(d["filename"], "")),
                        "words_count": d.get("word_count", 0),
                        "updated_at": d.get("updated_at"),
                        "is_core": d.get("is_core", False),
                        "source": d.get("source", "upload"),
                        "preview": (self.knowledge_cache.get(d["filename"], "") or "")[:150] + "...",
                    })
                return docs
            except Exception as e:
                logger.warning(f"DB list_documents failed (no file fallback): {e}")
                return []

        self.reload()
        docs = []
        for md_file in sorted(self.kb_dir.glob("*.md")):
            try:
                stat = md_file.stat()
                content = self.knowledge_cache.get(md_file.name, "")
                words = len(content.split())
                is_core = md_file.name in [
                    "brand_tone.md",
                    "faqs.md",
                    "rules_and_guidelines.md",
                    "business_profile.md",
                    "products_and_services.md",
                    "sales_scripts_and_closing.md",
                ]
                docs.append({
                    "name": md_file.stem,
                    "filename": md_file.name,
                    "size_bytes": stat.st_size,
                    "words_count": words,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "is_core": is_core,
                    "preview": content[:150] + ("..." if len(content) > 150 else "")
                })
            except Exception as e:
                logger.error(f"Error stat-ing file {md_file}: {e}")
        return docs

    # ------------------------------------------------------------------
    # Document CRUD
    # ------------------------------------------------------------------
    def get_document(self, filename: str) -> Optional[str]:
        """Returns raw content of a specific knowledge base document."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                return db_knowledge_base.get_document_content(filename)
            except Exception as e:
                logger.warning(f"DB get_document failed (no file fallback): {e}")
                return None

        clean_name = sanitize_safe_filename(filename)
        target = (self.kb_dir / clean_name).resolve()
        # Ensure path does not escape knowledge base directory
        if not str(target).startswith(str(self.kb_dir.resolve())):
            logger.warning(f"Blocked path traversal attempt in get_document: {filename}")
            return None

        if target.exists() and target.is_file():
            return target.read_text(encoding="utf-8")
        return None

    def save_document(self, filename: str, content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Saves or edits a document (DB mode chunks+embeds with owner stamp; file mode writes)."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                res = db_knowledge_base.save_document(filename, content, user_id=user_id)
                res["message"] = f"تم حفظ المستند '{res['filename']}' وفهرسته للبحث الذكي بنجاح."
                return res
            except Exception as e:
                logger.warning(f"DB save failed (no file fallback): {e}")
                raise

        clean_name = sanitize_safe_filename(filename)
        target = (self.kb_dir / clean_name).resolve()
        if not str(target).startswith(str(self.kb_dir.resolve())):
            raise ValueError(f"Invalid filename or path traversal detected: {filename}")

        target.write_text(content, encoding="utf-8")
        self.reload()
        logger.info(f"Updated and reloaded Knowledge Base document: {clean_name}")
        return {
            "status": "success",
            "filename": clean_name,
            "words_count": len(content.split()),
            "message": f"تم حفظ المستند '{clean_name}' وتحديث معرفة الذكاء الاصطناعي بنجاح."
        }

    def delete_document(self, filename: str) -> bool:
        """Deletes a document and reloads memory."""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                ok = db_knowledge_base.delete_document(filename)
                return ok
            except Exception as e:
                logger.warning(f"DB delete failed (no file fallback): {e}")
                return False

        clean_name = sanitize_safe_filename(filename)
        target = (self.kb_dir / clean_name).resolve()
        if not str(target).startswith(str(self.kb_dir.resolve())):
            logger.warning(f"Blocked path traversal attempt in delete_document: {filename}")
            return False

        if target.exists() and target.is_file():
            target.unlink()
            self.reload()
            logger.info(f"Deleted Knowledge Base document: {clean_name}")
            return True
        return False

    # ------------------------------------------------------------------
    # Context + RAG
    # ------------------------------------------------------------------
    def get_combined_context(self) -> str:
        """Returns all knowledge base content formatted for LLM system prompting."""
        if self._mode == "db":
            # There is no safe global context in a multi-tenant database.
            return ""
        if not self.knowledge_cache:
            self.reload()

        parts = []
        for name, text in self.knowledge_cache.items():
            parts.append(f"--- KNOWLEDGE BASE SECTION: {name.upper()} ---\n{text}\n")
        return "\n".join(parts)

    def search_relevant_chunks(self, query: str, top_k: int = 3,
                               user_id: Optional[str] = None) -> str:
        """
        RAG Hybrid Retrieval:
        - DB mode: pgvector cosine + full-text tsvector + RRF (Postgres RPC).
        - File mode: in-memory deterministic hybrid (legacy LEANN-inspired).
        """
        if not user_id:
            logger.warning("RAG lookup skipped because tenant user_id is missing (fail-closed).")
            return ""

        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                context = db_knowledge_base.search_context(query, top_k=top_k, user_id=user_id)
                if context:
                    return context
                return ""
            except Exception as e:
                logger.warning(f"DB RAG search failed (no in-memory fallback): {e}")
        # The legacy file cache has no tenant boundary. It is never a safe
        # fallback for a SaaS reply, even when a user_id is present.
        return ""

    def get_sales_closing_context(self, user_id: Optional[str] = None) -> str:
        """Retrieves targeted context for lead conversion and sales closing."""
        if not user_id:
            return ""
        if self._mode == "db":
            try:
                from src.knowledge.db_knowledge_base import db_knowledge_base
                return db_knowledge_base.sales_context(user_id=user_id)
            except Exception as e:
                logger.warning(f"DB sales context failed: {e}")
                return ""
        # See search_relevant_chunks: file-mode documents are not tenant-scoped.
        return ""


knowledge_base = KnowledgeBaseManager()
