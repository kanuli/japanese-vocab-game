#!/usr/bin/env python3
import json,os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','listening-audio-catalog.json'));M=Path(os.environ.get('MANIFEST_DIR','listening-aivis-manifests'));OUT=Path(os.environ.get('OUT','listening-aivis-index.json'));REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game');HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup');TAG=os.environ.get('RELEASE_TAG','listening-aivis-v1')
d=json.loads(CAT.read_text(encoding='utf-8'));q=d['questions'];model=json.loads((M/'aivis-model.json').read_text(encoding='utf-8'));voices={}
for st in model['styles']:
 k=st['key'];bundles={};seen=set()
 for lv in ['N1','N2','N3','N4','N5']:
  p=M/f'{k}-{lv}.json'
  if not p.is_file():raise SystemExit(f'Missing {p}')
  m=json.loads(p.read_text(encoding='utf-8'));expected={qid for qid,x in q.items() if x['level']==lv}
  if set(m.get('members') or {})!=expected:raise SystemExit(f'{k}-{lv} coverage mismatch')
  if m.get('licenseSha256')!=model['licenseSha256']:raise SystemExit('license metadata changed across shards')
  asset=m.get('asset') or f'{k}-{lv}.tar';bundles[lv]={'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/listening/aivis/v1/{asset}?download=true','members':m['members']};seen|=expected
 if seen!=set(q):raise SystemExit(f'{k} total coverage mismatch')
 voices[k]={'speaker':st['speaker'],'style':st['style'],'styleId':st['styleId'],'displayName':f"{st['speaker']}｜{st['style']}",'modelName':model['modelName'],'modelVersion':model['modelVersion'],'modelArchitecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256'],'bundles':bundles}
out={'version':2,'status':'ready','engine':'aivisspeech-style-bert-vits2','questionCount':len(q),'voiceCount':len(voices),'recordingCount':len(q)*len(voices),'questions':q,'model':{'uuid':model['modelUuid'],'name':model['modelName'],'version':model['modelVersion'],'architecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256']},'voices':voices}
if out['questionCount']!=3310 or not 1<=out['voiceCount']<=4:raise SystemExit('invalid totals')
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print('Listening Aivis:',out['recordingCount'],'recordings')
