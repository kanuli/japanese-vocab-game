#!/usr/bin/env python3
import json,os
from pathlib import Path
CAT=Path(os.environ.get('CATALOG','pronunciation-original-audio-catalog.json'))
MAN=Path(os.environ.get('MANIFEST_DIR','pronunciation-voicevox-original-manifests'))
OUT=Path(os.environ.get('INDEX_OUT','pronunciation-voicevox-original-index.json'))
GH=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game'); HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup'); NS=os.environ.get('RELEASE_NAMESPACE','pronunciation-voicevox-original-v1')
levels=['N1','N2','N3','N4','N5']; cat=json.loads(CAT.read_text(encoding='utf-8')); questions=cat.get('questions') or {}
if len(questions)!=6690: raise SystemExit(f'Expected 6690 questions, got {len(questions)}')
rows=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(MAN.glob('*.json'))]
if len(rows)!=215: raise SystemExit(f'Expected 215 manifests, got {len(rows)}')
by={}; ident={}
for m in rows:
    k=str(m['speakerKey']); l=str(m['level']).upper(); key=(k,l)
    if key in by: raise SystemExit(f'Duplicate {key}')
    by[key]=m; ident.setdefault(k,(m['speaker'],m['style'],int(m['styleId']),m['credit']))
if len(ident)!=43: raise SystemExit(f'Expected 43 speakers, got {len(ident)}')
speakers={}
for k in sorted(ident):
    bundles={}; total=0
    for level in levels:
        m=by.get((k,level))
        if not m:raise SystemExit(f'Missing {k}/{level}')
        expected={qid for qid,q in questions.items() if q['level']==level}; members={qid:[int(x[0]),int(x[1])] for qid,x in m['members'].items()}
        if set(members)!=expected:raise SystemExit(f'Coverage mismatch {k}/{level}: {len(members)}/{len(expected)}')
        asset=m['asset']; tag=f'{NS}-{k}-{level.lower()}'
        bundles[level]={'asset':asset,'release':tag,'githubUrl':f'https://github.com/{GH}/releases/download/{tag}/{asset}','hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/pronunciation/voicevox/original-v1/{k}/{asset}','count':len(members),'members':members}
        total+=len(members)
    if total!=6690:raise SystemExit(f'{k} total {total}')
    name,style,style_id,credit=ident[k]
    speakers[k]={'speaker':name,'style':style,'styleId':style_id,'credit':credit,'questionCount':total,'bundles':bundles}
out={'version':1,'status':'ready','engine':'voicevox','scope':'pronunciation-original-6690','storage':'github-releases+huggingface-range-tar','questionCount':6690,'speakerCount':43,'recordingCount':287670,'questions':questions,'textMap':cat.get('textMap') or {},'speakers':speakers}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',OUT,'43 x 6690 =',out['recordingCount'])
