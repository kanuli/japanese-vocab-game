#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json,re

ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'listening-original-catalog.json';REPORT=ROOT/'data/listening_repair_batch5_report.json'
EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不');KANA=re.compile(r'[ぁ-ゖァ-ヺ]')
ACTION_ZH={
 'メールを確認する':'確認電郵','予約を変更する':'更改預約','薬を受け取る':'領取藥物','会議室を予約する':'預約會議室','本を図書館へ返す':'把書歸還圖書館','切符を買う':'購買車票','担当者に電話する':'致電負責人','荷物を二階へ運ぶ':'把行李搬到二樓','申込書に名前を書く':'在申請表上填寫姓名','コピーを三部取る':'影印三份文件','資料を受付に出す':'把資料交到接待處','鍵を受付へ返す':'把鑰匙交還接待處'}
CLEAN=[('空港','機場'),('学校','學校'),('図書館','圖書館'),('会議','會議'),('会場','會場'),('駅','車站'),('明日','明天'),('あさって','後天')]
CONNECT=[('の後で','之後再'),('の前に','之前先'),('より先に','之前先'),('より前に','之前先')]

def norm(s):return re.sub(r'[\s，。！？、,.!?「」『』（）()]','',str(s or '')).strip()
def chars(s):return {c for c in norm(s) if '\u3400'<=c<='\u9fff'}
def overlap(a,b):
 A,B=chars(a),chars(b);return 0 if not A or not B else len(A&B)/max(1,min(len(A),len(B)))
def cleanup(z):
 z=str(z or '').strip()
 # Replace action substrings, not only whole-field matches. This repairs combinations such as Aの後でB.
 for ja,zh in sorted(ACTION_ZH.items(),key=lambda p:-len(p[0])):z=z.replace(ja,zh)
 for a,b in CONNECT:z=z.replace(a,b)
 for a,b in CLEAN:z=z.replace(a,b)
 z=z.replace('照常先做','照常先做')
 return z

def quality(x):
 cs=[str(v or '').strip() for v in x.get('choicesZh',[])];correct=str(x.get('correctZh','')).strip();target=norm(correct);wrong=[v for v in cs if norm(v)!=target]
 structural=(len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==target for v in cs)!=1)
 extreme=sum(bool(EXTREME.search(w)) and not EXTREME.search(correct) for w in wrong);near=sum(overlap(correct,w)>=.12 for w in wrong);base=max(1,len(norm(correct)));outlier=sum((lambda r:r<.45 or r>2.2)(len(norm(w))/base) for w in wrong)
 return {'pass':not structural and extreme<2 and outlier<2 and near>=1,'structural':structural,'extremeWrong':extreme,'nearMiss':near,'lengthOutlier':outlier}
def metrics(items):
 rej=Counter();reason=Counter();trip=Counter();kana=[]
 for x in items:
  q=quality(x);lv=str(x.get('level','')).upper()
  if not q['pass']:rej[lv]+=1
  if q['structural']:reason['structuralBad']+=1
  if q['extremeWrong']>=2:reason['extremeTwoPlus']+=1
  if q['nearMiss']==0:reason['noNearMiss']+=1
  if q['lengthOutlier']>=2:reason['lengthTwoPlusOutlier']+=1
  correct=str(x.get('correctZh',''));cs=[str(v or '') for v in x.get('choicesZh',[])]
  for v in [correct]+cs:
   if KANA.search(v):kana.append({'id':x.get('id'),'value':v})
  wrong=sorted(norm(v) for v in cs if norm(v)!=norm(correct))
  if len(wrong)==3:trip['｜'.join(wrong)]+=1
 total=len(items);bad=sum(rej.values())
 return {'count':total,'qualityEligible':total-bad,'rejected':bad,'eligibleRate':round((total-bad)*100/max(1,total),1),'rejectedByLevel':dict(sorted(rej.items())),'reasons':dict(reason),'kanaChoiceCount':len(kana),'kanaSamples':kana[:12],'maxWrongTripleReuse':max(trip.values(),default=0),'topWrongTriples':[{'count':v,'signature':k} for k,v in trip.most_common(12)]}

# Semantic-preserving surface alternatives. Each rule keeps the same proposition but changes wording.
SYN={
 '會場':['會場','舉行地點','活動地點','場地'],
 '開始時間':['開始時間','開場時間','開始時刻','活動開始時間'],
 '日期':['日期','舉行日期','活動日期','日期安排'],
 '延後':['延後','延遲','往後調','改晚'],
 '提早':['提早','提前','往前調','改早'],
 '不變':['不變','維持不變','保持原定','照舊'],
 '見面':['見面','會合','碰面','會面'],
 '先到':['先到','先前往','先抵達','先去'],
 '再去':['再去','再前往','接著去','之後前往'],
 '入口':['入口','入口處','出入口','入口位置'],
 '活動取消':['活動取消','活動不再舉行','該活動取消','取消這項活動'],
 '處理資料':['處理資料','處理這份資料','進行資料處理','把資料處理好'],
 '確認資料':['確認資料','確認這份資料','核對資料內容','查看資料內容'],
 '把資料':['把資料','把這份資料','將資料','將這份資料'],
 '交給別人':['交給別人','交由其他人','交給他人','改由別人負責'],
 '照常舉行':['照常舉行','按原定安排舉行','如期進行','按原計畫舉行']}
ORDER=sorted(SYN,key=len,reverse=True)
def rephrase(s,mode):
 z=str(s or '').strip();period='。' if z.endswith('。') else '';core=z[:-1] if period else z
 # Apply several same-meaning surface substitutions. Mode 0 deliberately retains original wording.
 for key in ORDER:
  if key in core:
   vals=SYN[key];core=core.replace(key,vals[mode%len(vals)])
 return core+period

def diversify(items,threshold=40):
 by={}
 for x in items:
  c=str(x.get('correctZh',''));cs=[str(v or '') for v in x.get('choicesZh',[])];w=sorted(norm(v) for v in cs if norm(v)!=norm(c))
  if len(w)==3:by.setdefault('｜'.join(w),[]).append(x)
 changed=0;reverted=0
 for sig,rows in by.items():
  if len(rows)<=threshold:continue
  for occ,x in enumerate(sorted(rows,key=lambda z:str(z.get('id','')))):
   original=list(x.get('choicesZh',[]));target=norm(x.get('correctZh',''));out=[];wi=0
   for v in original:
    if norm(v)==target:out.append(v);continue
    # Cartesian cycle across three wrong positions: up to 4^3=64 distinct triples.
    mode=(occ//(4**wi))%4;out.append(rephrase(v,mode));wi+=1
   if len({norm(v) for v in out})==4:
    oldq=quality(x);x['choicesZh']=out;newq=quality(x)
    # Surface diversity must never turn a previously eligible item into a rejected one.
    if oldq['pass'] and not newq['pass']:
     x['choicesZh']=original;reverted+=1
    elif out!=original:changed+=1
 return changed,reverted

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[])
# Repair every Chinese answer field compositionally.
cleaned=0
for x in items:
 oldc=str(x.get('correctZh',''));old=list(x.get('choicesZh',[]));x['correctZh']=cleanup(oldc);x['choicesZh']=[cleanup(v) for v in old]
 if x['correctZh']!=oldc or x['choicesZh']!=old:cleaned+=1
 if x.get('explanationZh'):
  z=str(x['explanationZh'])
  for ja,zh in sorted(ACTION_ZH.items(),key=lambda p:-len(p[0])):z=z.replace(ja,zh)
  for a,b in CLEAN:z=z.replace(a,b)
  x['explanationZh']=z
mid=metrics(items);changed,reverted=diversify(items,40);after=metrics(items)
prior=json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {}
prior['version']='2026-08-27-listening-repair-batch5-v2';prior['afterCompositeCleanup']=mid;prior['after']=after;prior.setdefault('repairCounts',{})['compositeAnswerCleanup']=cleaned;prior['repairCounts']['normalizedTemplateDiversified']=changed;prior['repairCounts']['diversityRevertedForQuality']=reverted
prior['notes']=(prior.get('notes') or [])+['Batch 5 v2 translates embedded action combinations such as Aの後でB into Traditional Chinese.','Template diversification now operates on normalized propositions and uses a 64-combination Cartesian cycle, while reverting any wording change that would make a previously eligible item fail the quality gate.']
SRC.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');REPORT.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'mid':{'rejected':mid['rejected'],'rate':mid['eligibleRate'],'kana':mid['kanaChoiceCount'],'maxTriple':mid['maxWrongTripleReuse']},'after':{'rejected':after['rejected'],'rate':after['eligibleRate'],'kana':after['kanaChoiceCount'],'maxTriple':after['maxWrongTripleReuse']},'cleaned':cleaned,'diversified':changed,'reverted':reverted},ensure_ascii=False))
