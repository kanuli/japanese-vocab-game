#!/usr/bin/env python3
import json,os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','word-shared-audio-catalog.json'));MODEL=Path(os.environ.get('MODEL','aivis-model.json'));M=Path(os.environ.get('MANIFEST_DIR','word-aivis-manifests'));OUT=Path(os.environ.get('OUT','word-aivis-catalog.json'));REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game');HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup');TAG=os.environ.get('RELEASE_TAG','word-aivis-v1')
d=json.loads(CAT.read_text(encoding='utf-8'));model=json.loads(MODEL.read_text(encoding='utf-8'));words=d['words'];sc=int(d['shardCount']);voices={}
for st in model['styles']:
 k=st['key'];bundles={};seen=set()
 for shard in range(sc):
  p=M/f'{k}-shard{shard}.json'
  if not p.is_file():raise SystemExit(f'Missing {p}')
  m=json.loads(p.read_text(encoding='utf-8'));expected={x['id'] for x in d['items'] if int(x['shard'])==shard}
  if set(m.get('members') or {})!=expected:raise SystemExit(f'{k} shard {shard} coverage mismatch')
  if m.get('licenseSha256')!=model['licenseSha256']:raise SystemExit('Aivis license changed between shards')
  asset=m.get('asset') or f'{k}-shard{shard}.tar';bundles[str(shard)]={'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/word/aivis/v1/{asset}?download=true','members':m['members']};seen|=expected
 if len(seen)!=22333:raise SystemExit(f'{k}: expected 22333 IDs, got {len(seen)}')
 idx={'version':1,'engine':'aivisspeech-style-bert-vits2','voice':k,'speaker':st['speaker'],'style':st['style'],'styleId':st['styleId'],'displayName':f"{st['speaker']}｜{st['style']}",'modelName':model['modelName'],'modelVersion':model['modelVersion'],'modelArchitecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256'],'wordCount':22333,'shardCount':sc,'bundles':bundles}
 ip=Path(f'word-aivis-{k}-index.json');ip.write_text(json.dumps(idx,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 voices[k]={'speaker':st['speaker'],'style':st['style'],'displayName':idx['displayName'],'modelName':model['modelName'],'modelVersion':model['modelVersion'],'modelArchitecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256'],'indexUrl':f'./{ip.name}?v=1'}
out={'version':1,'status':'ready','engine':'aivisspeech-style-bert-vits2','storage':'github-releases+hf-range-bundles','wordCount':22333,'voiceCount':len(voices),'recordingCount':22333*len(voices),'shardCount':sc,'model':{'uuid':model['modelUuid'],'name':model['modelName'],'version':model['modelVersion'],'architecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256']},'words':words,'voices':voices}
if not 1<=out['voiceCount']<=4:raise SystemExit('Unexpected Aivis voice count')
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print('Word Aivis:',out['recordingCount'],'recordings /',out['voiceCount'],'styles')
