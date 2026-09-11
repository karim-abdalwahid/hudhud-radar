import re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
keys = ['cc_search_ph','sc.headline','sc.sub','sc.demo.customer','sc.demo.live','sc.demo.stat1','sc.demo.stat2','sc.demo.stat3','sc.demo.via','onboard.no_sub_title','onboard.no_sub_desc','onboard.brain_admin_note','set.threads_connect','set.security_title','set.security_desc','consent_prefix','consent_and','consent_terms','consent_privacy','consent_required','nav.dev_console','password_hint','phone_hint','onboard.role_opt_other','onboard.role_custom_ph','onboard.skip_all','onboard.start_trial','onboard.subscribe','onboard.skip','back_home','home','confirm','inbox.dossier_contact']
for f in Path("src/templates").rglob("*.html"):
    t = f.read_text(encoding="utf-8", errors="replace")
    for k in keys:
        for m in re.finditer('data-i18n="' + k + '"[^>]*>([^<]{0,70})', t):
            print(f"{f.name:<18} {k:<28} default={m.group(1).strip()!r}")
