#!/usr/bin/env python3
"""Build lightweight root catalog + one range index per VOICEVOX speaker."""
from __future__ import annotations
import json, os
from pathlib import Path

MANIFEST_DIR=Path(os.environ.get('MANIFEST_DIR','word-voicevox-manifests'))
CATALOG=Path(os.environ.get('CATALOG','word-voicevox-catalog.json'))
OUT_DIR=Path(os.environ.get('OUT_DIR','word-voicevox-publish'))
GITHUB_REPO=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game').strip()
HF_DATASET_REPO=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup').strip()
RELEASE_TAG=os.environ.get('RELEASE_TAG','voicevox-vocab-v1').strip()
EXPECTED_SPEAKERS=int(os.environ.get('EXPECTED_SPEAKERS','43'))

def main():
    catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
    words=catalog['words']; expected_ids={w['id'] for w in words}; shard_count=int(catalog['shardCount'])
    files=sorted(MANIFEST_DIR.glob('*.json'))
    if len(files)!=EXPECTED_SPEAKERS*shard_count:raise RuntimeError(f'Expected {EXPECTED_SPEAKERS*shard_count} manifests, found {len(files)}')
    by={}; ident={}
    for p in files:
        m=json.loads(p.read_text(encoding='utf-8'))
        if m.get('version')!=1:raise RuntimeError(f'bad manifest {p}')
        key=str(m['speakerKey']); shard=int(m['shard'])
        if shard in by.setdefault(key,{}):raise RuntimeError(f'duplicate {key}/{shard}')
        by[key][shard]=m
        who=(str(m['speaker']),str(m['style']),int(m['styleId']),str(m['credit']))
        if key in ident and ident[key]!=who:raise RuntimeError(f'identity mismatch {key}')
        ident[key]=who
    if len(by)!=EXPECTED_SPEAKERS:raise RuntimeError(f'Expected {EXPECTED_SPEAKERS} speakers, found {len(by)}')
    shard_ids={s:{w['id'] for w in words if int(w['shard'])==s} for s in range(shard_count)}
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    speakers={}
    for key in sorted(by):
        if set(by[key])!=set(range(shard_count)):raise RuntimeError(f'{key} missing shards')
        speaker,style,style_id,credit=ident[key]; bundles={}; covered=set()
        for shard in range(shard_count):
            m=by[key][shard]; mids=set(m['members'])
            if mids!=shard_ids[shard]:raise RuntimeError(f'coverage mismatch {key}/shard{shard}: {len(mids)} vs {len(shard_ids[shard])}')
            covered|=mids; asset=str(m['asset'])
            bundles[str(shard)]={
                'asset':asset,
                'githubUrl':f'https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/{asset}',
                'hfUrl':f'https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/voicevox-vocab/v1/{key}/{asset}',
                'members':m['members'],
                'count':int(m['count'])
            }
        if covered!=expected_ids:raise RuntimeError(f'{key} does not cover full catalog')
        speaker_index={'version':1,'speakerKey':key,'speaker':speaker,'style':style,'styleId':style_id,'credit':credit,'wordCount':len(covered),'shardCount':shard_count,'bundles':bundles}
        idx_name=f'{key}-index.json';(OUT_DIR/idx_name).write_text(json.dumps(speaker_index,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        speakers[key]={'speaker':speaker,'style':style,'styleId':style_id,'credit':credit,'wordCount':len(covered),'indexGithubUrl':f'https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/{idx_name}','indexHfUrl':f'https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/voicevox-vocab/v1/indexes/{idx_name}'}
    root={
        'version':2,'status':'ready','storage':'github-releases+hf-range-bundles','primaryStorage':'github-releases','backupStorage':'huggingface-dataset',
        'releaseTag':RELEASE_TAG,'wordCount':len(words),'speakerCount':len(speakers),'recordingCount':len(words)*len(speakers),'shardCount':shard_count,
        'countsByLevel':catalog.get('countsByLevel',{}),'words':{w['key']:[w['id'],int(w['shard'])] for w in words},'speakers':speakers
    }
    if root['recordingCount']!=len(words)*EXPECTED_SPEAKERS:raise RuntimeError('recording count mismatch')
    Path('word-voicevox-catalog.json').write_text(json.dumps(root,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f"Built VOICEVOX vocabulary indexes: {root['speakerCount']} x {root['wordCount']} = {root['recordingCount']} recordings")
    return 0
if __name__=='__main__':raise SystemExit(main())
