#!/usr/bin/env python3
import json,os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','pronunciation-original-audio-catalog.json'))
MAN=Path(os.environ.get('MANIFEST_DIR','pronunciation-supertonic-original-manifests'))
OUT=Path(os.environ.get('INDEX_OUT','pronunciation-supertonic-original-index.json'))
GH=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game'); HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup'); TAG=os.environ.get('RELEASE_TAG','pronunciation-supertonic-original-v1')
voices=['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5']; levels=['N1','N2','N3','N4','N5']; shards=2
cat=json.loads(CAT.read_text(encoding='utf-8')); questions=cat.get('questions') or {}
if len(questions)!=6690: raise SystemExit(f'Expected 6690 questions, got {len(questions)}')
rows=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(MAN.glob('*.json'))]
if len(rows)!=len(voices)*len(levels)*shards: raise SystemExit(f'Expected 100 manifests, got {len(rows)}')
lookup={}
for m in rows:
    k=(m['voice'],m['level'],int(m['shardIndex']))
    if k in lookup: raise SystemExit(f'Duplicate {k}')
    lookup[k]=m
outvoices={}
for v in voices:
    bundles={}; total=0
    for level in levels:
        parts=[]; seen=set()
        expected={qid for qid,q in questions.items() if q['level']==level}
        for shard in range(shards):
            m=lookup.get((v,level,shard))
            if not m: raise SystemExit(f'Missing {v}/{level}/p{shard}')
            members={qid:[int(x[0]),int(x[1])] for qid,x in m['members'].items()}
            if seen.intersection(members): raise SystemExit(f'Duplicate qids {v}/{level}')
            seen.update(members); asset=m['asset']
            parts.append({'asset':asset,'release':TAG,'githubUrl':f'https://github.com/{GH}/releases/download/{TAG}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/pronunciation/supertonic/original-v1/{asset}','count':len(members),'members':members})
        if seen!=expected: raise SystemExit(f'Coverage mismatch {v}/{level}: {len(seen)}/{len(expected)}')
        bundles[level]=parts; total+=len(seen)
    if total!=6690: raise SystemExit(f'{v} total {total}')
    outvoices[v]={'questionCount':total,'bundles':bundles}
out={'version':1,'status':'ready','engine':'supertonic-3','scope':'pronunciation-original-6690','storage':'github-releases+huggingface-range-tar','questionCount':6690,'voiceCount':10,'recordingCount':66900,'questions':questions,'textMap':cat.get('textMap') or {},'voices':outvoices}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',OUT,'10 x 6690 =',out['recordingCount'])
