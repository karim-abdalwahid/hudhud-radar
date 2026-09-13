import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
c = open("src/content_studio/service.py", encoding="utf-8").read()
i = c.find('"platform":')
print("content_posts insert platform ctx:", c[max(0,i-90):i+140].replace("\n", " | ")[:220])
m = open("src/content_studio/models.py", encoding="utf-8").read()
j = m.find("class ContentPlatform")
print("ContentPlatform enum:", m[j:j+240].replace("\n", " "))
# messages.platform can be manual/other only if a lead source flows there; orchestrator builds events from webhook = facebook/instagram only.
