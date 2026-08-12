#!/usr/bin/env python3
"""Build final 43-speaker x 3310-question VOICEVOX audio-sprite index."""
from __future__ import annotations
import json, os
from pathlib import Path

MANIFEST_DIR=Path(os.environ.get('MANIFEST_DIR','voicevox-sprite-manifests'))
OUT=Path(os.environ.get('INDEX_OUT','voicevox-full-index.json'))
HF=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup')
GH=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game')
NS=os.environ.get('RELEASE_NAMESPACE','voicevox-full-v2')
LEVELS={'N1','N2','N3','N4','N5'}
EXPECTED_SPEAKERS=int(os.environ.get('EXPECTED_SPEAKERS','43'))
EXPECTED_QUESTIONS=int(os.environ.get('EXPECTED_QUESTIONS','3310'))


def main():
    paths=sorted(MANIFEST_DIR.glob('*.json'))
    if len(paths)!=EXPECTED_SPEAKERS*5:raise RuntimeError(f'Expected {EXPECTED_SPEAKERS*5} manifests, found {len(paths)}')
    by={}; identity={}
    for path in paths:
        m=json.loads(path.read_text(encoding='utf-8'))
        if m.get('version')!=2 or m.get('format')!='audio-sprite-mp3':raise RuntimeError(f'Bad sprite manifest: {path}')
        key=m['speakerKey']; level=m['level']
        if level not in LEVELS:raise RuntimeError(f'Bad level: {level}')
        if level in by.setdefault(key,{}):raise RuntimeError(f'Duplicate {key}/{level}')
        by[key][level]=m
        ident=(m['speaker'],m['style'],int(m['styleId']),m['credit'])
        if key in identity and identity[key]!=ident:raise RuntimeError(f'Identity mismatch for {key}')
        identity[key]=ident
    if len(by)!=EXPECTED_SPEAKERS:raise RuntimeError(f'Expected {EXPECTED_SPEAKERS} speakers, found {len(by)}')
    for key,levels in by.items():
        if set(levels)!=LEVELS:raise RuntimeError(f'{key} missing levels {LEVELS-set(levels)}')
    base=sorted(by)[0]
    baseline={level:set(by[base][level]['questions']) for level in LEVELS}
    questions={}
    for level in LEVELS:
        for qid,q in by[base][level]['questions'].items():questions[qid]={'level':level,'text':q['text'],'grammar':q.get('grammar','')}
    if len(questions)!=EXPECTED_QUESTIONS:raise RuntimeError(f'Expected {EXPECTED_QUESTIONS} questions, found {len(questions)}')
    speakers={}
    for key in sorted(by):
        speaker,style,sid,credit=identity[key]; sprites={}; total=0
        for level in sorted(LEVELS):
            m=by[key][level]; qset=set(m['questions'])
            if qset!=baseline[level]:raise RuntimeError(f'Unequal coverage {key}/{level}')
            asset=m['asset']; tag=f'{NS}-{key}-{level.lower()}'
            sprites[level]={
                'asset':asset,'release':tag,
                'githubUrl':f'https://github.com/{GH}/releases/download/{tag}/{asset}',
                'hfUrl':f'https://huggingface.co/datasets/{HF}/resolve/main/voicevox-full/{key}/{asset}',
                'duration':m['duration'],'count':m['count'],
                'segments':{qid:[q['start'],q['end']] for qid,q in m['questions'].items()}
            }
            total+=m['count']
        if total!=EXPECTED_QUESTIONS:raise RuntimeError(f'{key} total {total}')
        speakers[key]={'speaker':speaker,'style':style,'styleId':sid,'credit':credit,'questionCount':total,'sprites':sprites}
    out={'version':4,'storage':'github-releases+hf-audio-sprites','primaryStorage':'github-releases','backupStorage':'huggingface-dataset','coverage':'full-per-speaker','indexed':len(questions),'speakerCount':len(speakers),'recordingCount':len(questions)*len(speakers),'githubRepository':GH,'huggingFaceDataset':HF,'releaseNamespace':NS,'questions':questions,'speakers':speakers}
    if out['recordingCount']!=142330:raise RuntimeError(f"Wrong total {out['recordingCount']}")
    OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f"Built {OUT}: {out['speakerCount']} x {out['indexed']} = {out['recordingCount']}")
    return 0

if __name__=='__main__':raise SystemExit(main())
