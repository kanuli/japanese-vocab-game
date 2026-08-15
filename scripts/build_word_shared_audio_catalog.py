#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
SRC=Path('word-voicevox-catalog.json');OUT=Path('word-shared-audio-catalog.json');SHARDS=20
d=json.loads(SRC.read_text(encoding='utf-8'))
if d.get('status')!='ready' or int(d.get('wordCount',0))!=22333 or int(d.get('speakerCount',0))!=43:raise SystemExit('Completed VOICEVOX word catalog is not ready')
source=d.get('words') or {}
if len(source)!=22333:raise SystemExit(f'Expected 22,333 word keys, got {len(source)}')
items=[];words={};counts=[0]*SHARDS
for key,lookup in source.items():
    if not isinstance(lookup,list) or len(lookup)<1:raise SystemExit('Bad lookup for '+key)
    wid=str(lookup[0]);reading,written=(key.split('|',1)+[''])[:2]
    if not reading:raise SystemExit('Missing reading for '+key)
    shard=int(hashlib.sha256(wid.encode()).hexdigest()[:8],16)%SHARDS
    counts[shard]+=1;items.append({'id':wid,'key':key,'reading':reading,'written':written,'shard':shard});words[key]=[wid,shard]
if len({x['id'] for x in items})!=22333:raise SystemExit('Word recording IDs are not unique')
if min(counts)<900 or max(counts)>1300:raise SystemExit(f'Unexpected shard balance: {counts}')
out={'version':1,'status':'catalog','engine':'shared-word-audio','language':'ja','wordCount':22333,'shardCount':SHARDS,'shardCounts':counts,'items':items,'words':words}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Shared word catalog:',len(items),'words /',SHARDS,'shards; min/max',min(counts),max(counts))
