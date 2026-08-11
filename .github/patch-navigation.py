from pathlib import Path
import re

BASE = 'text-decoration:none;border:1px solid #dfe4ec;background:#fff;border-radius:999px;padding:8px 11px;font-weight:700;font-size:13px;color:#182033'
ACTIVE = 'text-decoration:none;border:1px solid #3568dd;background:#eef3ff;border-radius:999px;padding:8px 11px;font-weight:700;font-size:13px;color:#3568dd'

def nav(active):
    styles = {k:(ACTIVE if k == active else BASE) for k in ('vocab','grammar','listening')}
    return ('<div class="site-nav" style="display:flex;gap:7px;flex-wrap:wrap;margin:0 0 14px">'
            f'<a href="./index.html" style="{styles["vocab"]}">📚 單字</a>'
            f'<a href="./grammar.html" style="{styles["grammar"]}">📝 文法</a>'
            f'<a href="./listening.html" style="{styles["listening"]}">🎧 聽解</a>'
            '</div>')

# Vocabulary: replace the first navigation row immediately after .wrap.
p = Path('index.html')
s = p.read_text(encoding='utf-8')
s, n = re.subn(r'(<body><div class="wrap">)<div style="display:flex;gap:7px;flex-wrap:wrap;margin:0 0 14px">.*?</div>\s*', r'\1' + nav('vocab') + '\n', s, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Could not patch index navigation')
p.write_text(s, encoding='utf-8')

# Grammar: same top position, but highlight Grammar.
p = Path('grammar.html')
s = p.read_text(encoding='utf-8')
s, n = re.subn(r'(<div class="wrap">)<div style="display:flex;gap:7px;flex-wrap:wrap;margin:0 0 14px">.*?</div>\s*', r'\1' + nav('grammar') + '\n', s, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Could not patch grammar navigation')
p.write_text(s, encoding='utf-8')

# Listening: remove its below-title nav, then insert the unified nav immediately after .wrap.
p = Path('listening.html')
s = p.read_text(encoding='utf-8')
s, n1 = re.subn(r'\n?<div class="nav"><a href="\./index\.html">📚 單字</a><a href="\./grammar\.html">📝 文法</a><a class="active" href="\./listening\.html">🎧 聽解</a></div>\s*', '\n', s, count=1)
if n1 != 1:
    raise SystemExit('Could not remove old listening navigation')
s, n2 = re.subn(r'(<div class="wrap">)\s*', r'\1\n' + nav('listening') + '\n', s, count=1)
if n2 != 1:
    raise SystemExit('Could not insert listening navigation')
p.write_text(s, encoding='utf-8')

print('Navigation synchronized across index.html, grammar.html, listening.html')
