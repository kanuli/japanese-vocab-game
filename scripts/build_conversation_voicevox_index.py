#!/usr/bin/env python3
import json, os
from pathlib import Path
CATALOG=Path(os.environ.get('CATALOG','conversation-audio-catalog.json'))
MANIFEST_DIR=Path(os.environ.get('MANIFEST_DIR','conversation-voicevox-manifests'))
OUT=Path(os.environ.get('OUT','conversation-voicevox-index.json'))
REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game')
HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup')
TAG=os.environ.get('RELEASE_TAG','conversation-voicevox-v1')
cat=json.loads(CATALOG.read_text(encoding='utf-8')); lines=cat['lines']; text_map=cat['textMap']
files=sorted(MANIFEST_DIR.glob('*.json'))
if len(files)!=43:raise SystemExit(f'Expected 43 speaker manifests, got {len(files)}')
speakers={}
for p in files:
    m=json.loads(p.read_text(encoding='utf-8'));k=m['speakerKey']
    if int(m.get('count',0))!=1244 or set(m.get('members') or {})!=set(lines):raise SystemExit(f'coverage mismatch {k}')
    asset=m.get('asset') or f'{k}.tar'
    speakers[k]={'speaker':m['speaker'],'style':m['style'],'styleId':m['styleId'],'credit':m.get('credit',f"VOICEVOX:{m['speaker']}"),'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/conversation/voicevox/v1/{asset}?download=true','members':m['members']}
out={'version':1,'status':'ready','engine':'voicevox','coverage':'full-conversation-per-speaker','sceneCount':26,'conversationCount':650,'sourceLineCount':1300,'utteranceCount':1244,'speakerCount':43,'recordingCount':43*1244,'lines':text_map,'speakers':speakers}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('VOICEVOX conversation coverage:',out['recordingCount'])
