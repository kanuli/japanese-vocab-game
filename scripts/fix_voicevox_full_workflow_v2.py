#!/usr/bin/env python3
from pathlib import Path

p=Path('.github/workflows/generate-voicevox-full-coverage.yml')
s=p.read_text(encoding='utf-8')

old="""          python - <<'PY' >> \"$GITHUB_OUTPUT\"
          import json
"""
new="""          python - <<'PY'
          import json, os
"""
assert old in s
s=s.replace(old,new,1)

old="""          print('speakers='+json.dumps(rows,ensure_ascii=False,separators=(',',':')))
          print('speaker_count='+str(len(rows)))
          for r in rows:
              print(f\"{r['key']}: {r['name']} / {r['style']} / {r['style_id']}\")
"""
new="""          with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as out:
              out.write('speakers='+json.dumps(rows,ensure_ascii=False,separators=(',',':'))+'\\n')
              out.write('speaker_count='+str(len(rows))+'\\n')
          for r in rows:
              print(f\"{r['key']}: {r['name']} / {r['style']} / {r['style_id']}\")
"""
assert old in s
s=s.replace(old,new,1)

old="""          HF_TOKEN=\"$(hf auth --oidc-token)\"
          export HF_TOKEN
"""
assert s.count(old)==2, s.count(old)
s=s.replace(old,'')

p.write_text(s,encoding='utf-8')
Path('.voicevox-full-trigger').write_text(
    'trigger=2026-08-12T21:28:00+08:00\\n'
    'mode=43-speakers-x-3310-questions\\n'
    'recordings=142330\\n'
    'retry=preflight-v2-auto-oidc\\n',
    encoding='utf-8'
)
print('Fixed discovery outputs and current Hugging Face Trusted Publisher CLI flow')
