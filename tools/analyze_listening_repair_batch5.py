#!/usr/bin/env python3
from pathlib import Path
from collections import Counter, defaultdict
import json, re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json'
OUT=ROOT/'data/listening_repair_batch5_preflight.json'
EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不')
KANA=re.compile(r'[ぁ-ゖァ-ヺ]')

def norm(s): return re.sub(r'[\s，。！？、,.!?「」『』（）()]','',str(s or '')).strip()
def chars(s): return {c for c in norm(s) if '\u3400' <= c <= '\u9fff'}
def overlap(a,b):
    A,B=chars(a),chars(b)
    return 0.0 if not A or not B else len(A&B)/max(1,min(len(A),len(B)))
def inspect(x):
    cs=[str(v or '').strip() for v in x.get('choicesZh',[])];correct=str(x.get('correctZh','')).strip();target=norm(correct)
    wrong=[v for v in cs if norm(v)!=target]
    structural=(len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==target for v in cs)!=1)
    extreme=sum(bool(EXTREME.search(w)) and not EXTREME.search(correct) for w in wrong)
    near=sum(overlap(correct,w)>=.12 for w in wrong);base=max(1,len(norm(correct)))
    outlier=sum((lambda r:r<.45 or r>2.2)(len(norm(w))/base) for w in wrong)
    return {'pass':not structural and extreme<2 and outlier<2 and near>=1,'structural':structural,'extremeWrong':extreme,'nearMiss':near,'lengthOutlier':outlier}

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[])
weak=[];by_level=Counter();by_type=Counter();by_level_type=Counter();triple=Counter();task_values=Counter();n2_values=Counter();kana_weak=Counter()
for x in items:
    q=inspect(x);correct=str(x.get('correctZh','')).strip();cs=[str(v or '').strip() for v in x.get('choicesZh',[])];wrong=sorted(norm(v) for v in cs if norm(v)!=norm(correct))
    if len(wrong)==3: triple['｜'.join(wrong)]+=1
    if not q['pass']:
        row={k:x.get(k) for k in ('id','level','typeZh','type','jp','correctZh','choicesZh','explanationZh')};row['quality']=q;weak.append(row)
        lv=str(x.get('level','')).upper();tp=str(x.get('typeZh') or x.get('type') or '聽解');by_level[lv]+=1;by_type[tp]+=1;by_level_type[(lv,tp)]+=1
        for v in cs:
            if tp=='任務理解': task_values[v]+=1
            if lv=='N2': n2_values[v]+=1
            if KANA.search(v): kana_weak[v]+=1
samples={}
for lv in ['N1','N2','N3','N4','N5']:
    rows=[x for x in weak if str(x.get('level','')).upper()==lv];buckets=defaultdict(list)
    for x in rows:buckets[str(x.get('typeZh') or x.get('type') or '聽解')].append(x)
    picked=[]
    for tp in sorted(buckets):picked.extend(sorted(buckets[tp],key=lambda z:str(z.get('id','')))[:3])
    samples[lv]=picked[:18]
report={
 'version':'2026-08-27-listening-repair-batch5-preflight-v2','catalogCount':len(items),'weakCount':len(weak),'weakByLevel':dict(sorted(by_level.items())),
 'topWeakTypes':[{'type':k,'count':v} for k,v in by_type.most_common(30)],'topWeakLevelTypes':[{'level':k[0],'type':k[1],'count':v} for k,v in by_level_type.most_common(50)],
 'maxWrongTripleReuse':max(triple.values(),default=0),'topWrongTriples':[{'count':v,'signature':k} for k,v in triple.most_common(20)],
 'taskChoiceValues':[{'value':k,'count':v,'hasKana':bool(KANA.search(k))} for k,v in task_values.most_common()],
 'n2ChoiceValues':[{'value':k,'count':v} for k,v in n2_values.most_common(80)],
 'kanaWeakValues':[{'value':k,'count':v} for k,v in kana_weak.most_common()],
 'samples':samples}
OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'weak':len(weak),'byLevel':dict(by_level),'taskValues':len(task_values),'kanaWeakValues':len(kana_weak),'maxTriple':report['maxWrongTripleReuse']},ensure_ascii=False))
