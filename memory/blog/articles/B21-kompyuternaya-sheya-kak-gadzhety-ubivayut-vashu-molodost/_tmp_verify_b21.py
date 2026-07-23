# TEMP: recount B21 then delete
import json
import re
from pathlib import Path

p = Path(r"C:\Cursor\EXCALIBUR\memory\blog\articles\B21-kompyuternaya-sheya-kak-gadzhety-ubivayut-vashu-molodost")
html = (p / "article.grok-draft.html").read_text(encoding="utf-8")
text = re.sub(r"<[^>]+>", "", html)
n = len(text)
kw = "компьютерная шея упражнения"
print(n)
print(text.count(kw))
# find near matches
idx = 0
while True:
    i = text.find("компьютерная шея", idx)
    if i < 0:
        break
    print(repr(text[i:i+40]))
    idx = i + 1
meta_path = p / "article.grok-draft.meta.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
meta["char_count"] = n
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("meta_updated", n)
