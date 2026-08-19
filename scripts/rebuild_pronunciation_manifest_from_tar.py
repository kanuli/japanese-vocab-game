#!/usr/bin/env python3
import json, os, tarfile
from pathlib import Path

KIND=os.environ.get('ENGINE_KIND','').strip().lower()
ASSET=Path(os.environ.get('ASSET_PATH','').strip())
CAT=Path(os.environ.get('CATALOG','pronunciation-original-audio-catalog.json'))
OUT=Path(os.environ.get('MANIFEST_OUT','').strip())
LEVEL=os.environ.get('LEVEL','').strip().upper()

if KIND not in {'supertonic','voicevox'}: raise SystemExit('ENGINE_KIND must be supertonic or voicevox')
if LEVEL not in {'N1','N2','N3','N4','N5'}: raise SystemExit('Invalid LEVEL')
if not ASSET.is_file() or ASSET.stat().st_size < 100000: raise SystemExit(f'Invalid TAR: {ASSET}')
if not OUT: raise SystemExit('MANIFEST_OUT is required')

d=json.loads(CAT.read_text(encoding='utf-8'))
questions=d.get('questions') or {}
rows=[(qid,rec) for qid,rec in questions.items() if str(rec.get('level','')).upper()==LEVEL]
if not rows: raise SystemExit(f'No catalog rows for {LEVEL}')

members={}
with tarfile.open(ASSET,'r:') as tf:
    for x in tf.getmembers():
        if x.isfile() and x.name.endswith('.mp3'):
            qid=Path(x.name).stem
            members[qid]=[int(x.offset_data),int(x.size)]
if not members: raise SystemExit(f'No MP3 members in {ASSET}')

if KIND=='supertonic':
    voice=os.environ.get('VOICE','').strip()
    shard_count=int(os.environ.get('SHARD_COUNT','2'))
    shard_index=int(os.environ.get('SHARD_INDEX','0'))
    expected={qid for qid,_ in rows[shard_index::shard_count]}
    if set(members)!=expected:
        raise SystemExit(f'TAR coverage mismatch {voice}/{LEVEL}/p{shard_index}: {len(members)}/{len(expected)}')
    manifest={
        'version':1,'engine':'supertonic-3','voice':voice,'level':LEVEL,
        'shardIndex':shard_index,'shardCount':shard_count,'count':len(members),
        'asset':ASSET.name,'fallbackCount':0,'fallbacks':{},'members':members,
        'recoveredFromTar':True
    }
else:
    key=os.environ.get('SPEAKER_KEY','').strip()
    name=os.environ.get('SPEAKER_NAME','').strip()
    style=os.environ.get('STYLE_NAME','').strip()
    style_id=int(os.environ.get('STYLE_ID','0'))
    expected={qid for qid,_ in rows}
    if set(members)!=expected:
        raise SystemExit(f'TAR coverage mismatch {key}/{LEVEL}: {len(members)}/{len(expected)}')
    manifest={
        'version':1,'engine':'voicevox','speakerKey':key,'speaker':name,'style':style,
        'styleId':style_id,'credit':f'VOICEVOX:{name}','level':LEVEL,'count':len(members),
        'asset':ASSET.name,'members':members,'recoveredFromTar':True
    }

OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Recovered manifest',OUT,'from',ASSET,'members',len(members))
