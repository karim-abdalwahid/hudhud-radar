"""
Unit & Integration Tests for LEANN-Inspired Semantic Hybrid Search Engine.
"""
import pytest
from src.knowledge.semantic_engine import LightweightSemanticEngine, semantic_engine
from src.agent.knowledge_base import knowledge_base


def test_cosine_similarity_calculation():
    engine = LightweightSemanticEngine()
    
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    vec_zero = [0.0, 0.0, 0.0]

    # Identical vectors
    assert pytest.approx(engine._cosine_similarity(vec_a, vec_b), 0.01) == 1.0
    # Orthogonal vectors
    assert pytest.approx(engine._cosine_similarity(vec_a, vec_c), 0.01) == 0.0
    # Zero vector
    assert engine._cosine_similarity(vec_a, vec_zero) == 0.0
    # Empty vectors
    assert engine._cosine_similarity([], []) == 0.0


def test_on_demand_vector_caching():
    engine = LightweightSemanticEngine()
    chunk_id = "test_doc.md#sec_1"
    text = "باقات إدارة الحملات الإعلانية الممولة على فيسبوك وإنستغرام"

    vec1 = engine.get_or_create_chunk_embedding(chunk_id, text)
    assert len(vec1) == 64
    assert chunk_id in engine._vector_cache

    # Retrieve again - must return cached vector
    vec2 = engine.get_or_create_chunk_embedding(chunk_id, text)
    assert vec1 == vec2


def test_semantic_synonym_retrieval():
    engine = LightweightSemanticEngine()
    
    mock_docs = {
        "pricing_packages.md": "# باقات الأسعار\nتكلفة الاشتراك الشهري في إدارة الحملات الإعلانية تبدأ من 5000 جنيه.",
        "brand_story.md": "# قصة البراند\nتأسست شركة إبدأ ماركتينج عام 2020 لمساعدة رواد الأعمال.",
        "technical_rules.md": "# القواعد الفنية\nيجب مراعاة نافذة الـ 24 ساعة لرسائل فيسبوك ماسنجر."
    }

    # Query uses conversational synonyms ("بكام", "مصاريف", "سبونسر")
    query = "بكام مصاريف إعلانات السبونسر؟"
    results = engine.hybrid_search(query, mock_docs, top_k=2)

    assert len(results) > 0
    top_score, top_file, top_text = results[0]
    assert top_file == "pricing_packages.md"
    assert "باقات الأسعار" in top_text


def test_knowledge_base_hybrid_search_integration():
    # Seed an isolated document (conftest forces KB into a tmp file-mode dir),
    # then verify the hybrid search produces relevant chunks.
    knowledge_base.save_document(
        "pricing_packages.md",
        "# باقات الأسعار\nتكلفة الاشتراك الشهري في إدارة الحملات الإعلانية تبدأ من 5000 جنيه مصري.\nباقة الاحترافية تشمل ريلز وإدارة إعلانات."
    )
    result = knowledge_base.search_relevant_chunks("عايز اعرف اسعار باقات الإعلانات", top_k=2)
    assert isinstance(result, str)
    assert len(result) > 20
    assert "باقات" in result or "إعلان" in result
