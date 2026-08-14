from pathlib import Path
import re

PAGES=["index.html","wordaudio.html","wordlist.html","grammar.html","listening.html","mocktest.html","translator.html"]
BASE='text-decoration:none;border:1px solid #dfe4ec;background:#fff;border-radius:999px;padding:8px 11px;font-weight:700;font-size:13px;color:#182033'
ACTIVE='text-decoration:none;border:1px solid #3568dd;background:#eef3ff;border-radius:999px;padding:8px 11px;font-weight:700;font-size:13px;color:#3568dd'
ITEMS=[
 ("index.html","📚 單字"),("wordaudio.html","🔊 單字聽力"),("wordlist.html","📋 單字清單"),
 ("grammar.html","📝 文法"),("listening.html","🎧 聽解"),("conversation.html","💬 場景會話"),
 ("mocktest.html","🧪 模擬試驗"),("translator.html","🌐 語音・翻譯")
]
def nav(active):
    return '<div class="site-nav" style="display:flex;gap:7px;flex-wrap:wrap;margin:0 0 14px">'+''.join(
        f'<a href="./{fn}" style="{ACTIVE if fn==active else BASE}">{label}</a>' for fn,label in ITEMS
    )+'</div>'
pat=re.compile(r'<div class="site-nav"[^>]*>.*?</div>',re.S)
for fn in PAGES:
    p=Path(fn)
    if not p.exists():
        continue
    s=p.read_text(encoding="utf-8")
    n=nav(fn)
    if pat.search(s):
        s=pat.sub(n,s,count=1)
    else:
        s=re.sub(r'(<body[^>]*>)',r'\1'+n,s,count=1,flags=re.S)
    p.write_text(s,encoding="utf-8")
    print("patched",fn)
