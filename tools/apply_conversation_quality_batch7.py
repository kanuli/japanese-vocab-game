#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'conversation.html';s=p.read_text(encoding='utf-8')
tag='<script src="./conversation-quality-batch7.js?v=20260827v1"></script>'
anchor='<script src="./conversation-quality-batch3.js?v=20260827v1"></script>'
if tag not in s:
    if anchor not in s:raise SystemExit('conversation batch3 anchor missing')
    s=s.replace(anchor,anchor+'\n'+tag,1);p.write_text(s,encoding='utf-8')
mp=ROOT/'data/reference_upgrade_manifest.json';d=json.loads(mp.read_text(encoding='utf-8'))
d['version']='2026-08-27-full-conversation-batch7-v1'
d['qualityDepthBatch7']={'scope':'all 77 conversation scenes / 1,925 dialogues','focus':['full-database template diversification','remove unnatural generic 進める templates','exact duplicate dialogue removal','preserve scene and JLPT counts'],'script':'conversation-quality-batch7.js','audit':'data/full_conversation_batch7_report.json'}
mp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Batch 7 conversation quality layer integrated')
