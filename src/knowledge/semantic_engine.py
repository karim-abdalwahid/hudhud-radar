"""
LEANN-Inspired Lightweight Semantic Hybrid Search Engine.
Provides on-demand vector embeddings, in-memory cosine similarity caching,
and Reciprocal Rank Fusion (RRF) combining keyword and semantic relevance
with zero external vector database overhead.
"""
from typing import List, Dict, Tuple, Optional, Any
import math
import re
import hashlib
from datetime import datetime, timezone
import httpx

from src.config import settings
from src.core.logger import logger


class LightweightSemanticEngine:
    """
    Ultra-low footprint semantic search engine inspired by LEANN.
    Uses on-demand vector computation and in-memory similarity caching.
    """

    # Semantic synonym clusters for Arabic marketing, sales, and agency services
    SYNONYM_CLUSTERS = [
        {"سعر", "اسعار", "بكام", "كام", "تكلفة", "اشتراك", "باقات", "مصاريف", "ميزانية", "فلوس", "price", "cost", "pricing"},
        {"حملات", "اعلانات", "ممولة", "ترويج", "سبونسر", "فيسبوك", "انستغرام", "ads", "sponsored", "campaigns"},
        {"ريلز", "فيديوهات", "ستوري", "تصوير", "مونتاج", "سيناريو", "reels", "video", "shorts"},
        {"خدمات", "شغل", "بتقدموا", "بتقدم ايه", "عرض", "تفاصيل", "استشارة", "services", "offers"},
        {"عملاء", "مبيعات", "ليدات", "شراء", "تعاقد", "اغلاق", "اتفاق", "sales", "leads", "closing"},
        {"تواصل", "واتساب", "تليفون", "موبايل", "رقم", "رسائل", "contact", "whatsapp", "phone"}
    ]

    def __init__(self):
        # In-memory vector cache: chunk_id -> (embedding_vector, content_hash)
        self._vector_cache: Dict[str, Tuple[List[float], str]] = {}

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two float vectors using pure math."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))

    def _generate_deterministic_embedding(self, text: str, dimensions: int = 64) -> List[float]:
        """
        Deterministic lightweight subword and synonym-aware vectorizer.
        Functions 100% offline with zero external dependencies.
        """
        tokens = re.findall(r'\w+', text.lower())
        if not tokens:
            return [0.0] * dimensions

        vec = [0.0] * dimensions
        
        # 1. Subword character n-gram hashing
        for token in tokens:
            # Token weight based on length
            token_weight = 1.0 + min(len(token), 10) * 0.1
            
            # Semantic synonym cluster projection
            for cluster_idx, cluster in enumerate(self.SYNONYM_CLUSTERS):
                if token in cluster or any(syn in token for syn in cluster):
                    target_dim = (cluster_idx * 7) % dimensions
                    vec[target_dim] += 2.5 * token_weight

            # 3-gram hashing for subword matching
            padded = f"_{token}_"
            for i in range(len(padded) - 2):
                ngram = padded[i:i+3]
                h = int(hashlib.md5(ngram.encode("utf-8")).hexdigest(), 16) % dimensions
                vec[h] += 1.0

        # Normalize vector to unit length
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    async def _fetch_gemini_embedding(self, text: str) -> Optional[List[float]]:
        """Optionally fetches text embedding from Gemini API when available."""
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your-"):
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {
                "parts": [{"text": text[:2000]}]
            }
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("embedding", {}).get("values")
        except Exception as e:
            logger.debug(f"Gemini embedding call failed: {e}. Falling back to deterministic vectorizer.")
        
        return None

    def get_or_create_chunk_embedding(self, chunk_id: str, text: str) -> List[float]:
        """
        Retrieves vector from in-memory cache or computes it on-demand.
        Zero disk storage and minimal RAM footprint.
        """
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        
        if chunk_id in self._vector_cache:
            vec, cached_hash = self._vector_cache[chunk_id]
            if cached_hash == content_hash:
                return vec

        # Compute on-demand vector
        vec = self._generate_deterministic_embedding(text)
        self._vector_cache[chunk_id] = (vec, content_hash)
        return vec

    def hybrid_search(
        self,
        query: str,
        documents: Dict[str, str],
        top_k: int = 3,
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5
    ) -> List[Tuple[float, str, str]]:
        """
        Executes hybrid semantic search across documents using LEANN principles:
        1. Tokenizes and breaks docs into structured sections.
        2. Computes keyword BM25/frequency overlap.
        3. Computes on-demand cosine semantic similarity.
        4. Fuses ranks using Reciprocal Rank Fusion (RRF).
        
        Returns list of (combined_score, filename, chunk_text).
        """
        query_tokens = set(re.findall(r'\w+', query.lower()))
        query_vec = self._generate_deterministic_embedding(query)
        
        all_chunks: List[Tuple[str, str, str]] = [] # (chunk_id, filename, text)
        
        for filename, content in documents.items():
            # Split by markdown headers
            sections = re.split(r'\n(?=#{1,3}\s)', content)
            for idx, sec in enumerate(sections):
                cleaned_sec = sec.strip()
                if not cleaned_sec:
                    continue
                chunk_id = f"{filename}#sec_{idx}"
                all_chunks.append((chunk_id, filename, cleaned_sec))

        if not all_chunks:
            return []

        # 1. Keyword scoring
        keyword_scores: Dict[str, float] = {}
        for chunk_id, fn, text in all_chunks:
            sec_lower = text.lower()
            score = 0.0
            for tok in query_tokens:
                if len(tok) > 1 and tok in sec_lower:
                    score += 2.0
            # Extra weight for exact phrases
            if query.lower() in sec_lower:
                score += 5.0
            keyword_scores[chunk_id] = score

        # 2. Semantic vector cosine similarity
        semantic_scores: Dict[str, float] = {}
        for chunk_id, fn, text in all_chunks:
            chunk_vec = self.get_or_create_chunk_embedding(chunk_id, text)
            sim = self._cosine_similarity(query_vec, chunk_vec)
            semantic_scores[chunk_id] = sim

        # 3. Rank calculation for Reciprocal Rank Fusion (RRF)
        sorted_by_keyword = sorted(all_chunks, key=lambda c: keyword_scores[c[0]], reverse=True)
        sorted_by_semantic = sorted(all_chunks, key=lambda c: semantic_scores[c[0]], reverse=True)

        keyword_ranks = {c[0]: rank + 1 for rank, c in enumerate(sorted_by_keyword)}
        semantic_ranks = {c[0]: rank + 1 for rank, c in enumerate(sorted_by_semantic)}

        # RRF formula: RRF_score = sum(1 / (k + rank))
        k = 60
        fused_results: List[Tuple[float, str, str]] = []
        for chunk_id, filename, text in all_chunks:
            kw_rank = keyword_ranks[chunk_id]
            sem_rank = semantic_ranks[chunk_id]
            
            # Combine RRF score with direct semantic similarity boost
            rrf_score = (keyword_weight * (1.0 / (k + kw_rank))) + (semantic_weight * (1.0 / (k + sem_rank)))
            # Add semantic cosine boost
            total_score = rrf_score + (semantic_scores[chunk_id] * 0.1)

            # Filter out chunks with 0 keyword match AND very low semantic similarity (< 0.15)
            if keyword_scores[chunk_id] > 0 or semantic_scores[chunk_id] >= 0.15:
                fused_results.append((total_score, filename, text))

        fused_results.sort(key=lambda x: x[0], reverse=True)
        return fused_results[:top_k]


semantic_engine = LightweightSemanticEngine()
