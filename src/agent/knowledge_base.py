"""
Knowledge Base Ingestion, Management, and RAG Context Provider.
Loads brand tone, FAQs, business rules, sales scripts, and dynamically indexed documents.
Supports live hot-reload, file CRUD, and semantic retrieval for the AI Agent.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import re
from datetime import datetime, timezone
from src.core.logger import logger
from src.knowledge.utils import sanitize_safe_filename


class KnowledgeBaseManager:
    """Reads, manages, and structures markdown knowledge files for AI context & RAG."""

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
        self.reload()

    def reload(self):
        """Reloads all markdown files from the knowledge base directory into memory."""
        self.knowledge_cache.clear()
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
        """Returns metadata of all knowledge base files for UI explorer."""
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

    def get_document(self, filename: str) -> Optional[str]:
        """Returns raw content of a specific knowledge base document."""
        clean_name = sanitize_safe_filename(filename)
        target = (self.kb_dir / clean_name).resolve()
        # Ensure path does not escape knowledge base directory
        if not str(target).startswith(str(self.kb_dir.resolve())):
            logger.warning(f"Blocked path traversal attempt in get_document: {filename}")
            return None

        if target.exists() and target.is_file():
            return target.read_text(encoding="utf-8")
        return None

    def save_document(self, filename: str, content: str) -> Dict[str, Any]:
        """Saves or edits a document in the knowledge base and hot-reloads memory."""
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
        """Deletes a document from the knowledge base and reloads memory."""
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

    def get_combined_context(self) -> str:
        """Returns all knowledge base content formatted for LLM system prompting."""
        if not self.knowledge_cache:
            self.reload()

        parts = []
        for name, text in self.knowledge_cache.items():
            parts.append(f"--- KNOWLEDGE BASE SECTION: {name.upper()} ---\n{text}\n")
        return "\n".join(parts)

    def search_relevant_chunks(self, query: str, top_k: int = 3) -> str:
        """
        RAG Hybrid Semantic Retrieval (LEANN-Inspired):
        Finds the most relevant knowledge sections based on on-demand vector cosine similarity
        and keyword Reciprocal Rank Fusion (RRF).
        """
        if not self.knowledge_cache:
            self.reload()

        try:
            from src.knowledge.semantic_engine import semantic_engine
            results = semantic_engine.hybrid_search(
                query=query,
                documents=self.knowledge_cache,
                top_k=top_k
            )
            if results:
                chunks = [f"[من وثيقة: {fn}]\n{chunk}" for _, fn, chunk in results]
                return "\n\n---\n\n".join(chunks)
        except Exception as e:
            logger.warning(f"Hybrid semantic search encountered an issue: {e}")

        # Fallback to general combined context if no specific matches
        return self.get_combined_context()[:2500]

    def get_sales_closing_context(self) -> str:
        """Retrieves targeted context for lead conversion and sales closing."""
        closing_docs = ["sales_scripts_and_closing.md", "products_and_services.md", "business_profile.md"]
        parts = []
        for doc in closing_docs:
            content = self.get_document(doc)
            if content:
                parts.append(f"--- تكتيكات البيع والمعلومات المعتمدة ({doc}) ---\n{content}\n")
        return "\n".join(parts) if parts else self.get_combined_context()


knowledge_base = KnowledgeBaseManager()
