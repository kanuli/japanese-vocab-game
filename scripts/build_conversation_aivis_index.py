#!/usr/bin/env python3
import json, os
from pathlib import Path
CATALOG=Path(os.environ.get('CATALOG','conversation-audio-catalog.json'))
MANIFEST_DIR=Path(os.environ.get('MANIFEST_DIR','conversation-aivis-out'))
OUT=Path(os.environ.get('OUT','conversation-aivis-index.json'))
REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game'); HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup'); TAG=os.environ.get('RELEASE_TAG','conversation-aivis-v1')
cat=json.loads(CATALOG.read_text(encoding='utf-8'));lines=cat['lines'];text_map=cat['textMap']
model=json.loads((MANIFEST_DIR/'aivis-model.json').read_text(encoding='utf-8'))
voices={}
for st in model['styles']:
    k=st['key'];p=MANIFEST_DIR/f'{k}.json'
    if not p.is_file():raise SystemExit(f'Missing {p}')
    m=json.loads(p.read_text(encoding='utf-8'))
    if int(m.get('count',0))!=1244 or set(m.get('members') or {})!=set(lines):raise SystemExit(f'Coverage mismatch {k}')
    asset=m.get('asset') or f'{k}.tar'
    voices[k]={'speaker':m['speaker'],'style':m['style'],'styleId':m['styleId'],'displayName':f"{m['speaker']}｜{m['style']}",'modelName':m['modelName'],'modelVersion':m['modelVersion'],'modelArchitecture':m['modelArchitecture'],'license':m['license'],'licenseSha256':m['licenseSha256'],'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/conversation/aivis/v1/{asset}?download=true','members':m['members']}
out={'version':2,'status':'ready','engine':'aivisspeech-style-bert-vits2','sceneCount':26,'conversationCount':650,'sourceLineCount':1300,'utteranceCount':1244,'voiceCount':len(voices),'recordingCount':1244*len(voices),'model':{'uuid':model['modelUuid'],'name':model['modelName'],'version':model['modelVersion'],'architecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256']},'lines':text_map,'speakers':voices,'voices':voices}
if not 1<=out['voiceCount']<=4:raise SystemExit('Unexpected Aivis voice count')
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Aivis Conversation coverage:',out['recordingCount'],'recordings /',out['voiceCount'],'styles')
