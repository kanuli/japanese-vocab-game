#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
changed=[]
def patch(path,anchor,addition):
 p=ROOT/path;s=p.read_text(encoding='utf-8')
 if addition not in s:
  if anchor not in s: raise SystemExit(f'{path}: anchor not found: {anchor}')
  s=s.replace(anchor,anchor+'\n'+addition,1);p.write_text(s,encoding='utf-8');changed.append(path)
patch('listening.html','<script src="./listening-gap-topup-batch2.js?v=20260827v2"></script>','<script src="./listening-quality-batch3.js?v=20260827v1"></script>')
patch('conversation.html','<script src="./conversation-function-topup.js?v=20260827v2"></script>','<script src="./conversation-quality-batch3.js?v=20260827v1"></script>')
p=ROOT/'data/reference_upgrade_manifest.json';d=json.loads(p.read_text(encoding='utf-8'))
d['version']='2026-08-27-quality-depth-batch3-v1'
for key,name in [('listening','listening-quality-batch3.js'),('conversation','conversation-quality-batch3.js')]:
 arr=d.setdefault('expansions',{}).setdefault(key,[])
 if name not in arr:arr.append(name)
d['qualityDepthBatch3']={'focus':['near-miss listening distractors','JLPT cognitive-load progression','conversation template diversity','duplicate-dialogue prevention'],'audit':'data/quality_depth_batch3_report.json','copyright':'All new wording is project-original; external sites remain reference-only.'}
text=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
if p.read_text(encoding='utf-8')!=text:p.write_text(text,encoding='utf-8');changed.append(str(p.relative_to(ROOT)))
print(json.dumps({'changed':changed,'count':len(changed)},ensure_ascii=False))
