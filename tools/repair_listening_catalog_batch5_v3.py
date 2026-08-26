#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json,re

ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'listening-original-catalog.json';REPORT=ROOT/'data/listening_repair_batch5_report.json'
KANA=re.compile(r'[ぁ-ゖァ-ヺ]');EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不')
ALIASES={'會議室を予約する':'預約會議室','本を圖書館へ返す':'把書歸還圖書館'}

def norm(s):return re.sub(r'[\s，。！？、,.!?「」『』（）()]','',str(s or '')).strip()
def chars(s):return {c for c in norm(s) if '\u3400'<=c<='\u9fff'}
def overlap(a,b):
 A,B=chars(a),chars(b);return 0 if not A or not B else len(A&B)/max(1,min(len(A),len(B)))
def quality(x):
 cs=[str(v or '').strip() for v in x.get('choicesZh',[])];c=str(x.get('correctZh','')).strip();t=norm(c);w=[v for v in cs if norm(v)!=t]
 structural=(len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==t for v in cs)!=1);extreme=sum(bool(EXTREME.search(v)) and not EXTREME.search(c) for v in w);near=sum(overlap(c,v)>=.12 for v in w);base=max(1,len(norm(c)));out=sum((lambda r:r<.45 or r>2.2)(len(norm(v))/base) for v in w)
 return {'pass':not structural and extreme<2 and out<2 and near>=1,'structural':structural,'extremeWrong':extreme,'nearMiss':near,'lengthOutlier':out}
def metrics(items):
 rej=Counter();reason=Counter();trip=Counter();kana=[]
 for x in items:
  q=quality(x);lv=str(x.get('level','')).upper()
  if not q['pass']:rej[lv]+=1
  if q['structural']:reason['structuralBad']+=1
  if q['extremeWrong']>=2:reason['extremeTwoPlus']+=1
  if q['nearMiss']==0:reason['noNearMiss']+=1
  if q['lengthOutlier']>=2:reason['lengthTwoPlusOutlier']+=1
  c=str(x.get('correctZh',''));cs=[str(v or '') for v in x.get('choicesZh',[])]
  for v in [c]+cs:
   if KANA.search(v):kana.append({'id':x.get('id'),'value':v})
  w=sorted(norm(v) for v in cs if norm(v)!=norm(c))
  if len(w)==3:trip['｜'.join(w)]+=1
 total=len(items);bad=sum(rej.values())
 return {'count':total,'qualityEligible':total-bad,'rejected':bad,'eligibleRate':round((total-bad)*100/max(1,total),1),'rejectedByLevel':dict(sorted(rej.items())),'reasons':dict(reason),'kanaChoiceCount':len(kana),'kanaSamples':kana[:10],'maxWrongTripleReuse':max(trip.values(),default=0),'topWrongTriples':[{'count':v,'signature':k} for k,v in trip.most_common(10)]}

SYN={
 '只改地點不改日期':['只改地點不改日期','只更改地點，日期維持原定','日期不變，只調整舉行地點','只換地點，活動日期照舊'],
 '明天按原定安排舉行':['明天按原定安排舉行','明天如期舉行','活動明天照原計畫進行','明天仍按原安排進行'],
 '後天按原定安排舉行':['後天按原定安排舉行','後天如期舉行','活動後天照原計畫進行','後天仍按原安排進行'],
 '星期五的會議取消改到明天':['星期五的會議取消改到明天','原定星期五的會議改至明天','會議由星期五改到明天','星期五不開會，改到明天舉行'],
 '星期五的會議取消改到後天':['星期五的會議取消改到後天','原定星期五的會議改至後天','會議由星期五改到後天','星期五不開會，改到後天舉行']}
def rephrase(s,mode):
 z=str(s or '').strip();period='。' if z.endswith('。') else '';core=z[:-1] if period else z
 # Compare normalized forms so punctuation in the source cannot block the replacement.
 n=norm(core)
 for key,vals in SYN.items():
  if norm(key)==n:return vals[mode%len(vals)]+period
 return z

def diversify(items,threshold=32):
 by={}
 for x in items:
  c=str(x.get('correctZh',''));cs=[str(v or '') for v in x.get('choicesZh',[])];w=sorted(norm(v) for v in cs if norm(v)!=norm(c))
  if len(w)==3:by.setdefault('｜'.join(w),[]).append(x)
 changed=0
 for sig,rows in by.items():
  if len(rows)<=threshold:continue
  for occ,x in enumerate(sorted(rows,key=lambda z:str(z.get('id','')))):
   old=list(x.get('choicesZh',[]));t=norm(x.get('correctZh',''));out=[];wi=0
   for v in old:
    if norm(v)==t:out.append(v);continue
    mode=(occ//(4**wi))%4;out.append(rephrase(v,mode));wi+=1
   if out!=old and len({norm(v) for v in out})==4:
    oldq=quality(x);x['choicesZh']=out
    if oldq['pass'] and not quality(x)['pass']:x['choicesZh']=old
    else:changed+=1
 return changed

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[]);alias_changes=0
for x in items:
 c=str(x.get('correctZh',''));cs=list(x.get('choicesZh',[]));z=c
 for a,b in ALIASES.items():z=z.replace(a,b)
 new=[]
 for v in cs:
  w=str(v)
  for a,b in ALIASES.items():w=w.replace(a,b)
  new.append(w)
 if z!=c or new!=cs:alias_changes+=1
 x['correctZh']=z;x['choicesZh']=new
 if x.get('explanationZh'):
  e=str(x['explanationZh'])
  for a,b in ALIASES.items():e=e.replace(a,b)
  x['explanationZh']=e
before=metrics(items);div=diversify(items,32);after=metrics(items)
r=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {};r['version']='2026-08-27-listening-repair-batch5-v3';r['afterAliasCleanup']=before;r['after']=after;r.setdefault('repairCounts',{})['traditionalizedActionAliases']=alias_changes;r['repairCounts']['finalReuseDiversification']=div;r['notes']=(r.get('notes') or [])+['Batch 5 v3 handles the two Traditional-kanji/Japanese-grammar action aliases left by earlier surface cleanup and lowers high-reuse groups above 32.']
SRC.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'before':{'kana':before['kanaChoiceCount'],'maxTriple':before['maxWrongTripleReuse'],'rate':before['eligibleRate']},'after':{'kana':after['kanaChoiceCount'],'maxTriple':after['maxWrongTripleReuse'],'rate':after['eligibleRate'],'rejected':after['rejected']},'aliasChanges':alias_changes,'diversified':div},ensure_ascii=False))
