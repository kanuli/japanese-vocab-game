#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
import json, re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json'
OUT=ROOT/'data/listening_length_batch6_preflight.json'

PUNCT=re.compile(r'[\s，。！？、,.!?「」『』（）()]')

def norm(s):
    return PUNCT.sub('',str(s or '')).strip()

def inspect(x):
    cs=[str(v or '').strip() for v in x.get('choicesZh',[])]
    correct=str(x.get('correctZh','')).strip(); target=norm(correct)
    wrong=[v for v in cs if norm(v)!=target]
    base=max(1,len(norm(correct)))
    rows=[]
    for w in wrong:
        ratio=len(norm(w))/base
        rows.append({'text':w,'len':len(norm(w)),'ratio':round(ratio,3),'outlier':ratio<.45 or ratio>2.2})
    return rows

data=json.loads(SRC.read_text(encoding='utf-8'))
items=data.get('items',[])
weak=[]; by_level=Counter(); by_type=Counter(); by_lt=Counter(); corrects=Counter(); patterns=Counter()
for x in items:
    rows=inspect(x)
    if sum(r['outlier'] for r in rows)>=2:
        lv=str(x.get('level','')).upper(); tp=str(x.get('typeZh') or x.get('type') or '聽解')
        rec={k:x.get(k) for k in ('id','level','typeZh','type','jp','correctZh','choicesZh','explanationZh')}
        rec['choiceLengths']=rows
        weak.append(rec); by_level[lv]+=1; by_type[tp]+=1; by_lt[(lv,tp)]+=1; corrects[str(x.get('correctZh',''))]+=1
        shape=[]
        base=max(1,len(norm(x.get('correctZh',''))))
        for v in x.get('choicesZh',[]):
            if norm(v)==norm(x.get('correctZh','')): continue
            r=len(norm(v))/base
            shape.append('S' if r<.45 else ('L' if r>2.2 else 'M'))
        patterns[''.join(sorted(shape))]+=1

samples={}
for lv in ['N1','N2','N3','N4','N5']:
    rows=[x for x in weak if str(x.get('level','')).upper()==lv]
    buckets=defaultdict(list)
    for x in rows:buckets[str(x.get('typeZh') or x.get('type') or '聽解')].append(x)
    picked=[]
    for tp in sorted(buckets):picked.extend(sorted(buckets[tp],key=lambda z:str(z.get('id','')))[:6])
    samples[lv]=picked[:24]

report={
 'version':'2026-08-27-listening-length-batch6-preflight-v1',
 'catalogCount':len(items),'weakCount':len(weak),
 'weakByLevel':dict(sorted(by_level.items())),
 'weakByType':dict(by_type.most_common()),
 'weakByLevelType':[{'level':k[0],'type':k[1],'count':v} for k,v in by_lt.most_common()],
 'lengthShapes':dict(patterns.most_common()),
 'topCorrectAnswers':[{'value':k,'count':v,'len':len(norm(k))} for k,v in corrects.most_common(30)],
 'samples':samples
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'weak':len(weak),'byLevel':dict(by_level),'shapes':dict(patterns)},ensure_ascii=False))
