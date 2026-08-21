from pathlib import Path
import runpy
import re

runpy.run_path('.github/scripts/fix_listening_mock_quality_v2.py', run_name='__main__')

# Root-fix one information-search template that could generate a duplicate
# distractor when t == 18. The QA gate already blocked it, but the generator
# itself should never create the bad candidate.
p=Path('mocktest.js')
s=p.read_text(encoding='utf-8')
old='w:["土曜日は18時まで利用できる。","毎週木曜日が休館日だ。","毎日8時から利用できる。"]'
new='w:[`土曜日は${t===18?16:18}時まで利用できる。`,"毎週木曜日が休館日だ。","毎日8時から利用できる。"]'
if old in s:
    s=s.replace(old,new,1)
elif 't===18?16:18' not in s:
    raise SystemExit('mock information-search duplicate root fix marker missing')
p.write_text(s,encoding='utf-8')

# Force browsers/GitHub Pages to fetch the repaired mocktest.js instead of a
# previously cached pre-QA build.
p=Path('mocktest.html')
h=p.read_text(encoding='utf-8')
h2=re.sub(r'mocktest\.js\?v=[^"\s<]+','mocktest.js?v=20260822-quality3',h,count=1)
if h2==h and 'mocktest.js?v=20260822-quality3' not in h:
    raise SystemExit('mocktest.js cache-bust marker not found')
p.write_text(h2,encoding='utf-8')

print('quality v3 finalization complete')
