#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json, re, sys

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json';REPORT=ROOT/'data/listening_repair_batch5_report.json'
EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不')
KANA=re.compile(r'[ぁ-ゖァ-ヺ]')
JP_SURFACE=re.compile(r'空港|学校|図書館|会議|会場|駅|あさって')

def norm(s):return re.sub(r'[\s，。！？、,.!?「」『』（）()]','',str(s or '')).strip()

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[]);r=json.loads(REPORT.read_text(encoding='utf-8'));a=r.get('after',{});fail=[]
if len(items)!=6690:fail.append(f'catalog count {len(items)} != 6690')
if float(a.get('eligibleRate',0))<95:fail.append(f"eligible rate {a.get('eligibleRate')} < 95")
if int(a.get('reasons',{}).get('structuralBad',0))!=0:fail.append('structural errors remain')
if int(a.get('kanaChoiceCount',0))!=0:fail.append(f"kana remains in Chinese answer fields: {a.get('kanaChoiceCount')}")
if int(a.get('maxWrongTripleReuse',9999))>40:fail.append(f"wrong-choice triple reuse {a.get('maxWrongTripleReuse')} > 40")
if int(a.get('reasons',{}).get('extremeTwoPlus',0))!=0:fail.append(f"two-plus extreme distractor rows remain: {a.get('reasons',{}).get('extremeTwoPlus')}")
struct=0;surface=[];task_bad=[];n2_bad=[]
for x in items:
    correct=str(x.get('correctZh','')).strip();cs=[str(v or '').strip() for v in x.get('choicesZh',[])];target=norm(correct)
    if len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==target for v in cs)!=1:struct+=1
    for v in [correct]+cs:
        if KANA.search(v) or JP_SURFACE.search(v):surface.append((x.get('id'),v))
    tp=str(x.get('typeZh') or x.get('type') or '')
    if tp=='任務理解' and str(x.get('level','')).upper() in ('N1','N3','N4'):
        if KANA.search(correct) or any(KANA.search(v) for v in cs):task_bad.append(x.get('id'))
    if str(x.get('level','')).upper()=='N2' and tp=='推論／意圖理解':
        wrong=[v for v in cs if norm(v)!=target]
        if sum(bool(EXTREME.search(v)) for v in wrong)>0:n2_bad.append(x.get('id'))
if struct:fail.append(f'live structural validation failed for {struct} rows')
if surface:fail.append(f'Japanese/simplified surface leakage remains in {len(surface)} answer values; sample={surface[:5]}')
if task_bad:fail.append(f'task answer translation incomplete: {len(task_bad)} rows')
if n2_bad:fail.append(f'N2 inference extreme wording remains: {len(n2_bad)} rows')
# Historical baseline protects against silently redefining the original problem away.
b=r.get('baseline',{})
if int(b.get('count',0))!=6690 or int(b.get('rejected',-1))!=904 or round(float(b.get('eligibleRate',0)),1)!=86.5:
    fail.append(f"historical baseline changed unexpectedly: {b}")
print(json.dumps({'passed':not fail,'after':a,'historicalBaseline':{'rejected':b.get('rejected'),'eligibleRate':b.get('eligibleRate')},'failures':fail},ensure_ascii=False))
if fail:sys.exit(1)
