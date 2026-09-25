import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "tests/test_nav_registry.py"
src = open(p, encoding="utf-8").read()
old = ('    assert nav.count("nav-section-title") == 3\n'
       '    assert nav.count(\'class="nav-item\') == 12  # /users + /templates admin console entries')
new = ('    # Wave 9.8: admin nav ships pre-separated - client titles (2) + a dev section\n'
       '    assert nav.count("nav-section-title") == 2\n'
       '    assert "client-nav-section" in nav and "dev-nav-section" in nav\n'
       '    assert "dev-badge" in nav\n'
       '    assert nav.count(\'class="nav-item\') == 12  # /users + /templates admin console entries')
assert old in src, "anchor not found"
src = src.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(src)
print("nav test updated to the new intended structure")
