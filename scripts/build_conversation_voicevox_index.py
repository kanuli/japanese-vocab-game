#!/usr/bin/env python3
import json, os
from pathlib import Path
CATALOG=Path(os.environ.get('CATALOG','conversation-audio-catalog.json'))
MANIFEST_DIR=Path(os.environ.get('MANIFEST_DIR','conversation-voicevox-manifests'))
OUT=Path(os.environ.get('OUT','conversation-voicevox-index.json'))
REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game')
HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup')
TAG=os.environ.get('RELEASE_TAG','conversation-voicevox-v2')
HF_FOLDER=os.environ.get('HF_FOLDER','conversation/voicevox/v2').strip('/')
cat=json.loads(CATALOG.read_text(encoding='utf-8')); lines=cat['lines']; text_map=cat['textMap']; expected=len(lines)
files=sorted(MANIFEST_DIR.glob('*.json'))
if len(files)!=43:raise SystemExit(f'Expected 43 speaker manifests, got {len(files)}')
speakers={}
for p in files:
    m=json.loads(p.read_text(encoding='utf-8'));k=m['speakerKey']
    if int(m.get('count',0))!=expected or set(m.get('members') or {})!=set(lines):raise SystemExit(f'coverage mismatch {k}: {m.get("count")}/{expected}')
    asset=m.get('asset') or f'{k}.tar'
    speakers[k]={'speaker':m['speaker'],'style':m['style'],'styleId':m['styleId'],'credit':m.get('credit',f"VOICEVOX:{m['speaker']}"),'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/{HF_FOLDER}/{asset}?download=true','members':m['members']}
out={'version':2,'status':'ready','engine':'voicevox','coverage':'full-conversation-per-speaker','sceneCount':int(cat.get('sceneCount',0)),'conversationCount':int(cat.get('conversationCount',0)),'sourceLineCount':int(cat.get('sourceLineCount',0)),'utteranceCount':expected,'speakerCount':43,'recordingCount':43*expected,'lines':text_map,'speakers':speakers}
if out['sceneCount']!=61 or out['conversationCount']!=1525 or out['sourceLineCount']!=3050:raise SystemExit(f"Unexpected catalog coverage: {out['sceneCount']} / {out['conversationCount']} / {out['sourceLineCount']}")
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('VOICEVOX conversation coverage:',out['recordingCount'])
