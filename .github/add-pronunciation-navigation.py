from pathlib import Path

PAGES = [
    'index.html',
    'wordaudio.html',
    'wordlist.html',
    'grammar.html',
    'listening.html',
    'conversation.html',
    'mocktest.html',
    'translator.html',
]

BASE_STYLE = 'text-decoration:none;border:1px solid #dfe4ec;background:#fff;border-radius:999px;padding:8px 11px;font-weight:700;font-size:13px;color:#182033'
LINK = f'<a href="./pronunciation.html" style="{BASE_STYLE}">🎙️ 發音</a>'

for name in PAGES:
    p = Path(name)
    if not p.exists():
        print(f'skip missing: {name}')
        continue
    s = p.read_text(encoding='utf-8')
    if 'href="./pronunciation.html"' in s or "href='./pronunciation.html'" in s:
        print(f'already present: {name}')
        continue

    anchors = [
        '<a href="./mocktest.html"',
        "<a href='./mocktest.html'",
        '<a href="./translator.html"',
        "<a href='./translator.html'",
    ]
    pos = -1
    for marker in anchors:
        pos = s.find(marker)
        if pos >= 0:
            break

    if pos < 0:
        print(f'no nav insertion point: {name}')
        continue

    s = s[:pos] + LINK + s[pos:]
    p.write_text(s, encoding='utf-8')
    print(f'updated: {name}')
