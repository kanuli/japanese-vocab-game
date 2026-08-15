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
INLINE_LINK = f'<a href="./pronunciation.html" style="{BASE_STYLE}">🎙️ 發音</a>'
CLASS_LINK = '<a class="navlink" href="./pronunciation.html">🎙️ 發音</a>\n'

for name in PAGES:
    p = Path(name)
    if not p.exists():
        print(f'skip missing: {name}')
        continue
    s = p.read_text(encoding='utf-8')
    if 'href="./pronunciation.html"' in s or "href='./pronunciation.html'" in s:
        print(f'already present: {name}')
        continue

    # Most pages use inline-styled links.
    pos = s.find('<a href="./mocktest.html"')
    if pos >= 0:
        s = s[:pos] + INLINE_LINK + s[pos:]
        p.write_text(s, encoding='utf-8')
        print(f'updated inline nav: {name}')
        continue

    # Conversation uses class="navlink" before href.
    marker = '<a class="navlink" href="./mocktest.html">'
    pos = s.find(marker)
    if pos >= 0:
        s = s[:pos] + CLASS_LINK + s[pos:]
        p.write_text(s, encoding='utf-8')
        print(f'updated class nav: {name}')
        continue

    # Final generic fallback: insert before whichever anchor contains mocktest href.
    href_pos = s.find('href="./mocktest.html"')
    if href_pos >= 0:
        start = s.rfind('<a', 0, href_pos)
        if start >= 0:
            link = CLASS_LINK if 'class="navlink"' in s[start:href_pos] else INLINE_LINK
            s = s[:start] + link + s[start:]
            p.write_text(s, encoding='utf-8')
            print(f'updated generic nav: {name}')
            continue

    print(f'no nav insertion point: {name}')
