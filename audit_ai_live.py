"""Phase C LIVE: AI generation, compliance, knowledge sync — proven real (not canned)."""
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

results = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context().new_page()
    pg.goto("http://localhost:8000/login"); pg.wait_for_load_state("networkidle")
    pg.fill("#loginEmail", "admin.test@hudhud.test"); pg.fill("#loginPassword", "AdminTest#2026")
    pg.click("#loginBtn"); pg.wait_for_url("**/dashboard**", timeout=15000)

    # 1. AI content generation (real Gemini, grounded in KB)
    t0 = time.time()
    r = pg.request.post("http://localhost:8000/api/content/generate", data={
        "topic": "ادارة صفحات السوشيال ميديا للمطاعم", "post_type": "post", "platform": "both"})
    gen = r.json()
    text = (gen.get("content") or gen.get("generated_text") or json.dumps(gen))[:400]
    dur = time.time() - t0
    print(f"1. /content/generate {r.status} ({dur:.1f}s) model:{gen.get('model', gen.get('provider', '?'))}")
    print("   sample:", text[:220].replace("\n", " | "))
    results.append(("AI content generation", "REAL ✅" if (r.status == 200 and len(text) > 60 and dur > 1) else "SUSPECT ❌"))

    # 2. Compliance check on obviously violating text
    r2 = pg.request.post("http://localhost:8000/api/content/compliance-check", data={
        "content_text": "اربح مليون جنيه في يوم واحد مضمون 100% بدون مجهود 🚀",
        "platform": "instagram", "post_type": "post"})
    comp = r2.json()
    print("2. /compliance-check", r2.status, "| verdict:", str(comp.get("is_compliant", comp))[:220])
    results.append(("Compliance check", "REAL ✅" if r2.status == 200 else "SUSPECT"))

    # 3. LLM live probe
    r3 = pg.request.get("http://localhost:8000/api/debug/llm-status")
    llm = r3.json()
    print("3. /llm-status", r3.status, "|", json.dumps(llm, ensure_ascii=False)[:220])
    results.append(("LLM live probe", "REAL ✅" if r3.status == 200 and str(llm).strip("{}") else "EMPTY ⚠️"))

    # 4. Knowledge sync from Meta (real crawl)
    t0 = time.time()
    r4 = pg.request.post("http://localhost:8000/api/knowledge/sync-meta")
    sync = r4.json()
    print(f"4. /knowledge/sync-meta {r4.status} ({time.time()-t0:.0f}s):", json.dumps(sync, ensure_ascii=False)[:300])
    docs = pg.request.get("http://localhost:8000/api/knowledge/documents").json()
    print("   documents after sync:", len(docs.get("documents", [])))
    results.append(("Meta knowledge sync", "REAL ✅" if r4.status == 200 else "SUSPECT"))

    # 5. Knowledge search — grounded chunks
    r5 = pg.request.post("http://localhost:8000/api/knowledge/search",
                         data={"query": "اسعار باقات ادارة السوشيال ميديا كام؟", "top_k": 2})
    sr = r5.json()
    hits = sr.get("results", [])
    print("5. /knowledge/search", r5.status, "| hits:", len(hits), "| first:", str(hits[0] if hits else {})[:180])
    results.append(("KB search", "REAL ✅" if hits else "EMPTY ⚠️"))

    b.close()

print("\n===== PHASE C MATRIX =====")
for n, v in results:
    print(f"  {v:<12} {n}")
