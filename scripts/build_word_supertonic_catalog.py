#!/usr/bin/env python3
import json,os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','word-shared-audio-catalog.json'));M=Path(os.environ.get('MANIFEST_DIR','word-supertonic-manifests'));OUT=Path(os.environ.get('OUT','word-supertonic3-catalog.json'));REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game');HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup');TAG=os.environ.get('RELEASE_TAG','word-supertonic3-v1')
d=json.loads(CAT.read_text(encoding='utf-8'));words=d['words'];sc=int(d['shardCount']);word_count=int(d['wordCount']);labels={'F1':'🌙 沉穩低柔女聲（F1）','F2':'🌸 明亮活潑女聲（F2）','F3':'🎙️ 專業播音女聲（F3）','F4':'✨ 清晰自信女聲（F4）','F5':'💕 溫柔療癒女聲（F5）','M1':'⚡ 活力自信男聲（M1）','M2':'🌑 低沉穩重男聲（M2）','M3':'🧭 權威專業男聲（M3）','M4':'🙂 柔和親切男聲（M4）','M5':'📖 溫暖舒緩男聲（M5）'}
if word_count!=len(words) or word_count<22000:raise SystemExit('Bad shared word catalog count')
voices={}
for v,label in labels.items():
 bundles={};seen=set()
 for shard in range(sc):
  p=M/f'{v}-shard{shard}.json'
  if not p.is_file():raise SystemExit(f'Missing {p}')
  m=json.loads(p.read_text(encoding='utf-8'));expected={x['id'] for x in d['items'] if int(x['shard'])==shard}
  if set(m.get('members') or {})!=expected:raise SystemExit(f'{v} shard {shard} coverage mismatch')
  asset=m.get('asset') or f'{v}-shard{shard}.tar';bundles[str(shard)]={'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/word/supertonic3/v1/{asset}?download=true','members':m['members']};seen|=expected
 if len(seen)!=word_count:raise SystemExit(f'{v}: expected {word_count} IDs, got {len(seen)}')
 idx={'version':2,'engine':'supertonic-3','voice':v,'label':label,'wordCount':word_count,'shardCount':sc,'bundles':bundles}
 ip=Path(f'word-supertonic3-{v}-index.json');ip.write_text(json.dumps(idx,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 voices[v]={'label':label,'indexUrl':f'./{ip.name}?v=2'}
out={'version':2,'status':'ready','engine':'supertonic-3','storage':'github-releases+hf-range-bundles','wordCount':word_count,'voiceCount':len(voices),'recordingCount':word_count*len(voices),'shardCount':sc,'words':words,'voices':voices}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print('Word Supertonic 3:',out['recordingCount'],'recordings')
