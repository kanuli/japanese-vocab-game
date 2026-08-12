from pathlib import Path

js = Path('mocktest.js')
s = js.read_text(encoding='utf-8')

needle = 'function sample(a,n){return shuffle(a).slice(0,n)}\n'
helper = '''function sample(a,n){return shuffle(a).slice(0,n)}\nfunction unique(a){const seen=new Set;return a.filter(x=>{const k=(x&&typeof x==="object")?(x.id||JSON.stringify(x)):String(x);if(seen.has(k))return false;seen.add(k);return true})}\n'''

if 'function unique(a)' not in s:
    if needle not in s:
        raise SystemExit('sample helper insertion point not found')
    s = s.replace(needle, helper, 1)

if 'function unique(a)' not in s:
    raise SystemExit('unique helper was not added')
js.write_text(s, encoding='utf-8')

html = Path('mocktest.html')
h = html.read_text(encoding='utf-8')
import re
h, n = re.subn(r'<script src="\./mocktest\.js(?:\?v=[^"]*)?"></script>', '<script src="./mocktest.js?v=20260813-unique-fix"></script>', h, count=1)
if n != 1:
    raise SystemExit('mocktest.js script tag not found')
html.write_text(h, encoding='utf-8')

print('Added unique helper and cache-busted mocktest.js')
