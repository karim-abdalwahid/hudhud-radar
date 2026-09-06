"""Seed real business knowledge into DB KB + verify hybrid search works."""
import sys
import time

sys.path.insert(0, ".")

from src.agent.knowledge_base import knowledge_base  # noqa: E402
from src.knowledge.db_knowledge_base import db_knowledge_base  # noqa: E402

BUSINESS_PROFILE = """# نبذة عن كريم عبد الواحد وإبدأ ماركتينج

كريم عبد الواحد صانع محتوى ومستشار تسويق رقمي متخصص في مساعدة أصحاب المشاريع الصغيرة والرواد على بناء حضور قوي على السوشيال ميديا.

## الخدمات المعتمدة
1. إدارة الحملات الإعلانية الممولة الموجهة للبيع المباشر على فيسبوك وإنستجرام.
2. صناعة سيناريوهات ومحتوى الريلز الفيروسي وتنمية الحسابات.
3. أنظمة الذكاء الاصطناعي للرد التلقائي وإغلاق الصفقات 24/7.

## التسعير
الباقات مرنة ومخصصة حسب الهدف — تبدأ الاشتراكات الشهرية من مستوى مبتدئ حتى مستوى الشركات. التفاصيل الدقيقة تقدم عبر مكالمة استشارية مجانية مدتها 15 دقيقة.

## أسلوب التواصل
مصري راقي وودود، يركز على النتائج الملموسة ويطلب من المتابعين كتابة كلمة ابدأ في التعليقات للتفاعل."""


def main():
    print("KB mode:", knowledge_base._mode)
    # Save via the DB layer directly (supports source/is_core)
    res = db_knowledge_base.save_document(
        "business_profile.md", BUSINESS_PROFILE, source="manual", is_core=True
    )
    print("Save:", res)
    time.sleep(1)

    # Verify listing
    docs = knowledge_base.list_documents()
    print(f"\nDocuments in DB ({len(docs)}):")
    for d in docs:
        print(f"  - {d['filename']} | words={d.get('word_count', d.get('words_count', '?'))} | source={d.get('source')}")

    # Hybrid search tests
    print("\n=== TEST 1: pricing query ===")
    r1 = knowledge_base.search_relevant_chunks("بكام اشتراك ادارة الصفحة؟ عايز اعرف الاسعار", top_k=2)
    print(r1[:350] or "(empty)")

    print("\n=== TEST 2: services query ===")
    r2 = knowledge_base.search_relevant_chunks("بتعملوا ايه بالظبط؟ ايه الخدمات", top_k=2)
    print(r2[:350] or "(empty)")


if __name__ == "__main__":
    main()
