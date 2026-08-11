from pathlib import Path

p = Path('listening.html')
s = p.read_text(encoding='utf-8')
old = 'return"一般文法"]}'
new = 'return"一般文法"}'
if old not in s:
    raise SystemExit('target syntax error not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Fixed listening JavaScript syntax error')
