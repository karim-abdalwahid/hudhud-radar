import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = "src/templates/studio.html"
src = open(p, encoding="utf-8").read()

wrong = '''<option value="both" data-i18n="st.platform_both">Facebook & Instagram</option>
                                    <option value="threads" data-i18n="st.platform_threads">🧵 Threads</option>'''
right = '''<option value="both" data-i18n="st.platform_both">Facebook & Instagram</option>'''
assert wrong in src, "wrong-place pattern not found"
src = src.replace(wrong, right, 1)  # remove from the AI pane select

right_anchor = '''<select id="post-platform">
                                    <option value="facebook" data-i18n="st.platform_fb">Facebook</option>
                                    <option value="instagram" data-i18n="st.platform_ig">Instagram</option>
                                    <option value="both" data-i18n="st.platform_both">Facebook & Instagram</option>
                                </select>'''
right_new = '''<select id="post-platform">
                                    <option value="facebook" data-i18n="st.platform_fb">Facebook</option>
                                    <option value="instagram" data-i18n="st.platform_ig">Instagram</option>
                                    <option value="both" data-i18n="st.platform_both">Facebook & Instagram</option>
                                    <option value="threads" data-i18n="st.platform_threads">🧵 Threads</option>
                                </select>'''
assert right_anchor in src, "publisher select not found"
src = src.replace(right_anchor, right_new, 1)

open(p, "w", encoding="utf-8").write(src)
import re
occ = [m.start() for m in re.finditer(r'value="threads"', src)]
print("threads option occurrences now:", occ)
