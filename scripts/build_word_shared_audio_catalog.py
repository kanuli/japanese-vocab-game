#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
SRC=Path('word-voicevox-catalog.json');OUT=Path('word-shared-audio-catalog.json');SHARDS=20
d=json.loads(SRC.read_text(encoding='utf-8'))
word_count=int(d.get('wordCount',0))
if d.get('status')!='ready' or word_count<22000 or int(d.get('speakerCount',0))!=43:
    raise SystemExit('Completed VOICEVOX word catalog is not ready')
source=d.get('words') or {}
if len(source)!=word_count:
    raise SystemExit(f'Catalog wordCount={word_count}, but words contains {len(source)} keys')
items=[];words={};counts=[0]*SHARDS
for key,lookup in source.items():
    if not isinstance(lookup,list) or len(lookup)<1:raise SystemExit('Bad lookup for '+key)
    wid=str(lookup[0]);reading,written=(key.split('|',1)+[''])[:2]
    if not reading:raise SystemExit('Missing reading for '+key)
    shard=int(hashlib.sha256(wid.encode()).hexdigest()[:8],16)%SHARDS
    counts[shard]+=1;items.append({'id':wid,'key':key,'reading':reading,'written':written,'shard':shard});words[key]=[wid,shard]
if len({x['id'] for x in items})!=word_count:
    raise SystemExit('Word recording IDs are not unique')
# Keep only a broad balance sanity check so future vocabulary growth does not require
# hard-coded count edits. Every item still has to appear exactly once.
avg=word_count/SHARDS
if min(counts)<avg*0.65 or max(counts)>avg*1.35:
    raise SystemExit(f'Unexpected shard balance: {counts}')
out={'version':2,'status':'catalog','engine':'shared-word-audio','language':'ja','wordCount':word_count,'shardCount':SHARDS,'shardCounts':counts,'items':items,'words':words}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Shared word catalog:',len(items),'words /',SHARDS,'shards; min/max',min(counts),max(counts))
