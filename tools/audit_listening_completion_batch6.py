#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json, re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json'
OUT=ROOT/'data/listening_completion_batch6_report.json'
PUNCT=re.compile(r'[\s，。！？、,.!?「」『』（）()]')
KANA=re.compile(r'[ぁ-ゖァ-ヺ]')
EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不')

def norm(s):return PUNCT.sub('',str(s or '')).strip()
def chars(s):return {c for c in norm(s) if '\u3400'<=c<='\u9fff'}
def overlap(a,b):
    A,B=chars(a),chars(b)
    if not A or not B:return 0.0
    return len(A&B)/max(1,min(len(A),len(B)))

def inspect(x):
    cs=[str(v or '').strip() for v in x.get('choicesZh',[])]
    correct=str(x.get('correctZh','')).strip(); target=norm(correct)
    structural=len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==target for v in cs)!=1
    wrong=[v for v in cs if norm(v)!=target]
    extreme=sum(bool(EXTREME.search(w)) and not bool(EXTREME.search(correct)) for w in wrong)
    near=sum(overlap(correct,w)>=.12 for w in wrong)
    base=max(1,len(norm(correct)))
    length=sum((len(norm(w))/base)<.45 or (len(norm(w))/base)>2.2 for w in wrong)
    kana=any(KANA.search(v) for v in cs+[correct])
    return {'structural':structural,'extremeTwoPlus':extreme>=2,'noNearMiss':near==0,'lengthTwoPlus':length>=2,'kana':kana}

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[])
counts=Counter();by_level={lv:Counter() for lv in ['N1','N2','N3','N4','N5']};bad=[];triples=Counter()
for x in items:
    q=inspect(x);lv=str(x.get('level','')).upper()
    for k,v in q.items():
        if v:counts[k]+=1;by_level.setdefault(lv,Counter())[k]+=1
    if any(q.values()) and len(bad)<50:bad.append({'id':x.get('id'),'level':lv,'typeZh':x.get('typeZh'),'quality':q,'correctZh':x.get('correctZh'),'choicesZh':x.get('choicesZh')})
    correct=norm(x.get('correctZh'));wrong=sorted(norm(v) for v in x.get('choicesZh',[]) if norm(v)!=correct)
    if len(wrong)==3:triples['｜'.join(wrong)]+=1
max_triple=max(triples.values(),default=0)
level_counts=Counter(str(x.get('level','')).upper() for x in items)
failures=[]
if len(items)!=6690:failures.append(f'catalog count {len(items)} != 6690')
for lv in ['N1','N2','N3','N4','N5']:
    if not level_counts.get(lv):failures.append(f'missing level {lv}')
for key in ['structural','extremeTwoPlus','noNearMiss','lengthTwoPlus','kana']:
    if counts[key]:failures.append(f'{key}={counts[key]}')
if max_triple>40:failures.append(f'maxWrongTripleReuse={max_triple} > 40')
report={
 'version':'2026-08-27-listening-completion-batch6-v1',
 'catalogCount':len(items),'levelCounts':dict(sorted(level_counts.items())),
 'qualityFailures':dict(counts),'perLevelFailures':{lv:dict(c) for lv,c in by_level.items()},
 'qualityEligible':len(items)-len({str(x.get('id')) for x in items if any(inspect(x).values())}),
 'eligibleRate':round(100*(len(items)-len({str(x.get('id')) for x in items if any(inspect(x).values())}))/max(1,len(items)),1),
 'maxWrongTripleReuse':max_triple,
 'topWrongTriples':[{'count':v,'signature':k} for k,v in triples.most_common(12)],
 'badSamples':bad,'failures':failures,'passed':not failures
}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':report['passed'],'eligibleRate':report['eligibleRate'],'failures':failures,'maxTriple':max_triple},ensure_ascii=False))
if failures:raise SystemExit('Batch 6 completion audit failed')
