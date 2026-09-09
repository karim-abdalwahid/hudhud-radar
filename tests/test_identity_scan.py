"""
S-Purge identity scanner test (R16): the platform code must NEVER reference
the owner's personal/business identity — the platform serves ALL users.
Backed by scripts/scan_identity.py.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_personal_identity_in_platform_code():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "scan_identity.py")],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, f"Identity leaked into platform code:\n{r.stdout}"


def test_legal_pages_use_platform_identity():
    legal = (ROOT / "src" / "modules" / "legal" / "__init__.py").read_text(encoding="utf-8")
    assert '"company_en": "Hudhud (hudhd.com)"' in legal
    assert "support@hudhd.com" in legal
    assert "ebdamarketing" not in legal


def test_conversation_prompts_are_account_scoped():
    conv = (ROOT / "src" / "agent" / "conversation_engine.py").read_text(encoding="utf-8")
    assert "لحساب التواصل الاجتماعي المتصل" in conv  # platform-neutral prompt
    assert "إبدأ ماركتينج" not in conv
    assert "كريم عبد الواحد" not in conv
