"""Fix dashboard header: Create Post -> studio publisher view + normalize topbar-actions."""
import glob
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STANDARD_ACTIONS_STYLE = ' style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;"'

# 1. overview.html: point Create Post at the publisher composer + fix actions style
p = "src/templates/overview.html"
src = open(p, encoding="utf-8").read()
before = src

src = src.replace(
    '<a href="/studio" class="btn-primary" data-i18n="topbar.new_post">+ Create Post</a>',
    '<a href="/studio?view=publisher" class="btn-primary" data-i18n="topbar.new_post">+ Create Post</a>', 1)

m = re.search(r'class="topbar-actions"([^>]*)>', src)
if m and "display:flex" not in m.group(1):
    src = src.replace('class="topbar-actions"' + m.group(1) + ">",
                      'class="topbar-actions"' + STANDARD_ACTIONS_STYLE + ">", 1)

open(p, "w", encoding="utf-8").write(src)
print(f"overview.html: create-post -> /studio?view=publisher | actions style normalized ({len(before)-len(src)} chars delta)")

# 2. normalize topbar-actions on every dashboard template missing the flex style
for f in sorted(glob.glob("src/templates/*.html")):
    t = open(f, encoding="utf-8", errors="replace").read()
    m = re.search(r'class="topbar-actions"([^>]*)>', t)
    if m and "display:flex" not in m.group(1):
        t = t.replace('class="topbar-actions"' + m.group(1) + ">",
                      'class="topbar-actions"' + STANDARD_ACTIONS_STYLE + ">", 1)
        open(f, "w", encoding="utf-8").write(t)
        print(f"normalized topbar-actions: {f}")

# 3. report the 'Studio →' card link context in overview (decide its target)
ov = open(p, encoding="utf-8").read()
i = ov.find("Studio →")
print("\n'Studio →' card context:")
print(ov[max(0, i - 420):i + 120])
