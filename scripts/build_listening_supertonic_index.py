#!/usr/bin/env python3
import json, os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','listening-audio-catalog.json'));M=Path(os.environ.get('MANIFEST_DIR','listening-supertonic-manifests'));OUT=Path(os.environ.get('OUT','listening-supertonic-index.json'));REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game');HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup');TAG=os.environ.get('RELEASE_TAG','listening-supertonic-v1')
d=json.loads(CAT.read_text(encoding='utf-8'));q=d['questions'];voices={};labels={'F1':'🌙 沉穩低柔女聲（F1）','F2':'🌸 明亮活潑女聲（F2）','F3':'🎙️ 專業播音女聲（F3）','F4':'✨ 清晰自信女聲（F4）','F5':'💕 溫柔療癒女聲（F5）','M1':'⚡ 活力自信男聲（M1）','M2':'🌑 低沉穩重男聲（M2）','M3':'🧭 權威專業男聲（M3）','M4':'🙂 柔和親切男聲（M4）','M5':'📖 溫暖舒緩男聲（M5）'}
for v,label in labels.items():
 bundles={};seen=set()
 for lv in ['N1','N2','N3','N4','N5']:
  p=M/f'{v}-{lv}.json';
  if not p.is_file():raise SystemExit(f'Missing {p}')
  m=json.loads(p.read_text(encoding='utf-8'));expected={k for k,x in q.items() if x['level']==lv}
  if set(m.get('members') or {})!=expected:raise SystemExit(f'{v}-{lv} coverage mismatch')
  asset=m.get('asset') or f'{v}-{lv}.tar';bundles[lv]={'githubUrl':f'https://github.com/{REPO}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/listening/supertonic/v1/{asset}?download=true','members':m['members']};seen|=expected
 if seen!=set(q):raise SystemExit(f'{v}: total coverage mismatch')
 voices[v]={'label':label,'bundles':bundles}
out={'version':1,'status':'ready','engine':'supertonic-3','questionCount':len(q),'voiceCount':10,'recordingCount':len(q)*10,'questions':q,'voices':voices}
if out['questionCount']!=3310 or out['recordingCount']!=33100:raise SystemExit('coverage totals wrong')
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print('Listening Supertonic 3:',out['recordingCount'],'recordings')
