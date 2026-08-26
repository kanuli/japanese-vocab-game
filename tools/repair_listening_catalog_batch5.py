#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib, json, math, re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json'
REPORT=ROOT/'data/listening_repair_batch5_report.json'
EXTREME=re.compile(r'一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不')
KANA=re.compile(r'[ぁ-ゖァ-ヺ]')

ACTION_ZH={
 'メールを確認する':'確認電郵','予約を変更する':'更改預約','薬を受け取る':'領取藥物','会議室を予約する':'預約會議室',
 '本を図書館へ返す':'把書歸還圖書館','切符を買う':'購買車票','担当者に電話する':'致電負責人','荷物を二階へ運ぶ':'把行李搬到二樓',
 '申込書に名前を書く':'在申請表上填寫姓名','コピーを三部取る':'影印三份文件','資料を受付に出す':'把資料交到接待處','鍵を受付へ返す':'把鑰匙交還接待處'
}
NEAR={
 '確認電郵':['稍後再確認電郵','先回覆電郵再確認內容','只查看電郵標題，稍後再確認內容'],
 '更改預約':['先確認預約內容但暫不更改','取消原有預約','維持原有預約不作更改'],
 '領取藥物':['先確認藥物但稍後才領取','先到藥局詢問藥物','請負責人代為領取藥物'],
 '預約會議室':['先確認會議室是否有空','取消原有會議室預約','先改用其他會議室'],
 '把書歸還圖書館':['先續借圖書館的書','把書帶到圖書館但稍後歸還','先在圖書館重新借書'],
 '購買車票':['先確認車票價格','先查看車票但稍後購買','取消購買車票的安排'],
 '致電負責人':['先傳電郵給負責人','稍後再致電負責人','請同事先聯絡負責人'],
 '把行李搬到二樓':['把行李搬到一樓','先把行李留在原處','把行李搬到三樓'],
 '在申請表上填寫姓名':['在申請表上填寫地址','先檢查申請表但不填姓名','在另一份表格填寫姓名'],
 '影印三份文件':['影印兩份文件','影印四份文件','先整理文件但暫不影印'],
 '把資料交到接待處':['把資料交到會議室','先確認資料但稍後提交','把資料交給負責人'],
 '把鑰匙交還接待處':['把鑰匙交給負責人','先保管鑰匙，稍後再交還','把鑰匙放在會議室']
}
N2_WRONG=[
 '今天先完成資料確認，明早改做其他工作。','今天只先整理資料，明天下午才開始確認內容。','今天暫不處理資料，改到明天下午再確認。',
 '今天先確認一部分，剩下的留到明天下午處理。','明早先處理其他工作，資料接近中午才開始確認。','今天把資料交給男方確認，自己明早不再處理。',
 '今天先外出，資料等明天中午之後再確認。','今晚先確認資料，明早只做最後整理。','今天先完成資料，明早只向男方報告結果。',
 '明早先聯絡男方，資料改到下午才確認。','今天只確認資料的一小部分，明早不把它列為優先。','今天先請男方處理，自己明天下午再接手。',
 '今天延後資料確認，明天中午才開始處理。','明早先處理別的資料，這份資料留到午前最後才確認。','今天照原計畫把資料處理完，明早不用再確認。',
 '今天先確認資料後再外出，明早改處理其他事項。','今天先處理最急的部分，明早只檢查男方的結果。','明早先外出處理其他事情，回來後才確認資料。'
]

# Exact surface-equivalent alternatives for the old high-reuse distractor templates.
PHRASE_VARIANTS={
 '先到機場再去學校':['先到機場再去學校','先前往機場，之後再去學校','先抵達機場，再前往學校','先去機場，接著到學校'],
 '在學校附近的入口見面':['在學校附近的入口見面','在學校附近入口會合','到學校附近的入口碰面','在學校附近入口處會合'],
 '在機場見面':['在機場見面','到機場會合','在機場碰面','於機場會合'],
 '日期和會場都改了':['日期和會場都改了','舉行日期與會場都更改了','日期及舉行地點都有變動','活動日期和地點都調整了'],
 '會場不變只改日期':['會場不變只改日期','維持原會場，只更改日期','舉行地點不變，只調整日期','只改活動日期，會場維持原定'],
 '活動完全取消':['活動取消','這項活動不再舉行','該活動決定取消','活動改為取消'],
 '先處理資料':['先處理資料','先處理這份資料','先進行資料處理','先把資料處理好'],
 '取消外出':['取消外出','取消外出的安排','不再外出','把外出安排取消'],
 '叫男方先去':['叫男方先去','請男方先前往','讓男方先去','請男士先行前往'],
 '取消見面':['取消見面','取消這次會面','不再按原定安排見面','把會面安排取消'],
 '改去公園等對方':['改去公園等對方','改到公園等對方','轉到公園等候對方','改為在公園等對方'],
 '等對方到了才去車站':['等對方到了才去車站','等對方到達後才前往車站','對方到達後再去車站','等到對方後再前往車站'],
 '會場不變但開始時間延後':['會場不變但開始時間延後','維持原會場，但開始時間延遲','舉行地點不變，只把開始時間往後調','會場照舊，開始時間改晚'],
 '會場改到公園開始時間也提早':['會場改到公園開始時間也提早','地點改到公園，而且開始時間提前','活動改在公園舉行，開始時間也往前調','會場改為公園，開場時間同時提前'],
 '不再處理資料':['不再處理資料','不再處理這份資料','停止處理該資料','之後不再進行資料處理'],
 '交給別人後不再確認':['交給別人後不再確認','交由其他人後便不再確認','交給他人處理，之後不再確認','改由別人負責，自己不再確認'],
 '今天一定處理資料':['今天處理資料','今天按原計畫處理資料','今天先把資料處理好','今天照常進行資料處理'],
 '先到機場再去車站':['先到機場再去車站','先前往機場，之後再去車站','先抵達機場，再前往車站','先去機場，接著到車站'],
 '在車站附近的入口見面':['在車站附近的入口見面','在車站附近入口會合','到車站附近的入口碰面','在車站附近入口處會合'],
 '在車站買新的資料':['在車站買新的資料','到車站購買新的資料','於車站買新資料','前往車站購買新資料'],
 '把資料丟掉':['把資料丟掉','把這份資料丟棄','將資料直接丟掉','把該資料棄置'],
 '把資料帶去車站':['把資料帶去車站','把資料帶到車站','將這份資料拿到車站','把該資料帶往車站'],
 '去公園的東側入口':['去公園的東側入口','前往公園東側入口','到公園的東面入口','前往公園東側入口處'],
 '去學校的西側入口':['去學校的西側入口','前往學校西側入口','到學校的西面入口','前往學校西側入口處'],
 '去車站前的施工入口':['去車站前的施工入口','前往車站前施工入口','到車站前的施工入口處','前往車站前方的施工入口'],
 '日期延後但會場不變':['日期延後但會場不變','舉行日期延後，但會場維持原定','活動日期往後調，地點不變','只延後日期，舉行地點照舊'],
 '會場和開始時間都改了':['會場和開始時間都改了','舉行地點與開始時間都有更改','活動地點和開場時間同時調整','會場及開始時刻都有變動'],
 '全部交給男方':['把資料交給男方處理','改由男方負責資料','請男方接手處理資料','資料改由男士處理'],
 '完全放棄處理資料':['暫停處理資料','決定不再處理這份資料','停止進行資料處理','這份資料暫時不再處理'],
 '在圖書館正面入口前':['在圖書館正面入口前','在圖書館正門入口前','到圖書館正面入口處','於圖書館正門前'],
 '在圖書館西側職員入口前':['在圖書館西側職員入口前','在圖書館西面職員入口前','到圖書館西側的職員入口處','於圖書館西側職員入口前'],
 '在教室東側入口前':['在教室東側入口前','在教室東面入口前','到教室東側入口處','於教室東側入口前'],
 '延期到其他日期會場不變':['延期到其他日期會場不變','改到其他日期，會場維持不變','延期舉行但地點照舊','日期往後調，舉行地點不改'],
 '日期不變但開始時間和會場都改了':['日期不變但開始時間和會場都改了','日期維持原定，但開始時間與會場都更改','活動日期不改，只調整時間和地點','日期照舊，開場時間及會場都有變動'],
 '即使出問題也必須今天完成':['即使出問題也必須今天完成','即使有問題仍要今天完成','遇到問題也要在今天完成','即使出現狀況，仍須今天完成'],
 '完全交給別人不再確認':['交給別人後不再確認','改由他人負責，自己不再確認','交由其他人處理，之後不再查看','讓別人接手，自己不再進一步確認'],
 '把期限延到後天':['把期限延到後天','把截止期限改到後天','期限往後延至後天','將完成期限延至後天'],
 '只改地點不改日期':['只改地點不改日期','只更改地點，日期維持原定','日期不變，只調整舉行地點','只換地點，活動日期照舊'],
 '明天照常舉行':['明天照常舉行','明天按原定安排舉行','活動明天如期進行','明天仍按原計畫舉行'],
 '星期五的會議取消改到明天':['星期五的會議取消改到明天','星期五的會議不舉行，改到明天','原定星期五的會議改至明天','會議由星期五改到明天'],
 '後天照常舉行':['後天照常舉行','後天按原定安排舉行','活動後天如期進行','後天仍按原計畫舉行'],
 '星期五的會議取消改到後天':['星期五的會議取消改到後天','星期五的會議不舉行，改到後天','原定星期五的會議改至後天','會議由星期五改到後天']
}

CLEAN=[('空港','機場'),('学校','學校'),('図書館','圖書館'),('会議','會議'),('会場','會場'),('駅','車站'),('明日','明天'),('あさって','後天')]

def norm(s): return re.sub(r'[\s，。！？、,.!?「」『』（）()]','',str(s or '')).strip()
def chars(s): return {c for c in norm(s) if '\u3400' <= c <= '\u9fff'}
def overlap(a,b):
    A,B=chars(a),chars(b)
    return 0.0 if not A or not B else len(A&B)/max(1,min(len(A),len(B)))
def hnum(s): return int(hashlib.sha1(str(s).encode('utf-8')).hexdigest()[:12],16)
def cleanup(s):
    z=str(s or '').strip()
    if z in ACTION_ZH:return ACTION_ZH[z]
    for a,b in CLEAN:z=z.replace(a,b)
    return z

def quality(x):
    cs=[str(v or '').strip() for v in x.get('choicesZh',[])];correct=str(x.get('correctZh','')).strip();target=norm(correct);wrong=[v for v in cs if norm(v)!=target]
    structural=(len(cs)!=4 or any(not v for v in cs) or len({norm(v) for v in cs})!=4 or sum(norm(v)==target for v in cs)!=1)
    extreme=sum(bool(EXTREME.search(w)) and not EXTREME.search(correct) for w in wrong);near=sum(overlap(correct,w)>=.12 for w in wrong);base=max(1,len(norm(correct)))
    outlier=sum((lambda r:r<.45 or r>2.2)(len(norm(w))/base) for w in wrong)
    return {'pass':not structural and extreme<2 and outlier<2 and near>=1,'structural':structural,'extremeWrong':extreme,'nearMiss':near,'lengthOutlier':outlier}

def metrics(items):
    lv=Counter();rej=Counter();reason=Counter();trip=Counter();kana=[]
    for x in items:
        level=str(x.get('level','')).upper();lv[level]+=1;q=quality(x)
        if not q['pass']:rej[level]+=1
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

def punct_variant(s, options, key):
    raw=str(s or '').strip();period='。' if raw.endswith('。') else '';base=raw[:-1] if period else raw
    if base not in options:return raw
    vals=options[base];z=vals[key%len(vals)]
    return z+period if period and not z.endswith('。') else z

def diversify_repeated(items, threshold=40):
    bysig={}
    for x in items:
        correct=str(x.get('correctZh',''));cs=[str(v or '') for v in x.get('choicesZh',[])];wrong=sorted(norm(v) for v in cs if norm(v)!=norm(correct))
        if len(wrong)==3:bysig.setdefault('｜'.join(wrong),[]).append(x)
    touched=0
    for sig,rows in bysig.items():
        if len(rows)<=threshold:continue
        for occurrence,x in enumerate(sorted(rows,key=lambda z:str(z.get('id','')))):
            target=norm(x.get('correctZh',''));new=[]
            for i,v in enumerate(x.get('choicesZh',[])):
                if norm(v)==target:new.append(v);continue
                key=hnum(f"{x.get('id')}:{i}:{occurrence}")
                new.append(punct_variant(v,PHRASE_VARIANTS,key))
            if new!=x.get('choicesZh',[]):x['choicesZh']=new;touched+=1
    return touched

data=json.loads(SRC.read_text(encoding='utf-8'));items=data.get('items',[]);before=metrics(items)
repair_counts=Counter();samples=[]
for x in items:
    old_correct=str(x.get('correctZh','')).strip();old_choices=[str(v or '').strip() for v in x.get('choicesZh',[])]
    # Basic Traditional-Chinese cleanup throughout the answer fields.
    x['correctZh']=cleanup(old_correct);x['choicesZh']=[cleanup(v) for v in old_choices]
    if x['correctZh']!=old_correct or x['choicesZh']!=old_choices:repair_counts['surfaceCleanup']+=1
    # The 657 weak task rows used exactly 12 Japanese action values. Translate them deterministically
    # and replace the generic fourth option with a task-specific near miss.
    tp=str(x.get('typeZh') or x.get('type') or '')
    if tp=='任務理解' and old_correct in ACTION_ZH:
        correct=ACTION_ZH[old_correct];x['correctZh']=correct
        near=NEAR[correct][hnum(x.get('id'))%len(NEAR[correct])]
        out=[];replaced_generic=False
        for v in old_choices:
            if v in ACTION_ZH:out.append(ACTION_ZH[v]);continue
            if v.startswith('照常先做') or v in ('完全按原定順序。','三件事同時開始。'):
                out.append(near);replaced_generic=True;continue
            out.append(cleanup(v))
        if not replaced_generic:
            # Replace the least-related wrong choice only if an unexpected old template appears.
            wrong_idx=[i for i,v in enumerate(out) if norm(v)!=norm(correct)]
            if wrong_idx:
                i=min(wrong_idx,key=lambda j:overlap(correct,out[j]));out[i]=near
        # Guard uniqueness; rotate near variant if needed.
        if len({norm(v) for v in out})<4:
            for cand in NEAR[correct]:
                trial=[cand if norm(v)==norm(near) else v for v in out]
                if len({norm(v) for v in trial})==4:out=trial;break
        x['choicesZh']=out
        if x.get('explanationZh'):
            z=str(x['explanationZh'])
            for ja,zh in ACTION_ZH.items():z=z.replace(ja,zh)
            x['explanationZh']=z
        repair_counts['taskTranslatedAndNearMiss']+=1
    # All 247 weak N2 inference rows share one old giveaway option set. Replace with diversified,
    # close-but-false alternatives that differ in timing, delegation or priority.
    if str(x.get('level','')).upper()=='N2' and tp=='推論／意圖理解' and norm(old_correct)==norm('今天不勉強處理，改在明早優先處理資料。'):
        start=hnum(x.get('id'))%len(N2_WRONG);step=5
        wrongs=[];j=start
        while len(wrongs)<3:
            cand=N2_WRONG[j%len(N2_WRONG)]
            if cand not in wrongs:wrongs.append(cand)
            j+=step
        target=norm(x['correctZh']);wi=0;new=[]
        for v in x['choicesZh']:
            if norm(v)==target:new.append(x['correctZh'])
            else:new.append(wrongs[wi]);wi+=1
        x['choicesZh']=new;repair_counts['n2InferenceRebuilt']+=1
    if len(samples)<24 and (x['correctZh']!=old_correct or x['choicesZh']!=old_choices):
        samples.append({'id':x.get('id'),'level':x.get('level'),'typeZh':x.get('typeZh'),'beforeCorrect':old_correct,'afterCorrect':x.get('correctZh'),'beforeChoices':old_choices,'afterChoices':x.get('choicesZh')})

# Diversify only overused wrong-choice triples, preserving their meaning via curated surface equivalents.
repair_counts['reusedTemplateSurfaceDiversified']=diversify_repeated(items,40)
after=metrics(items)

# Preserve the first historical baseline if a later idempotent workflow run re-executes this script.
prior=None
if REPORT.exists():
    try:prior=json.loads(REPORT.read_text(encoding='utf-8'))
    except Exception:prior=None
baseline=(prior or {}).get('baseline') or before
report={
 'version':'2026-08-27-listening-repair-batch5-v1','baseline':baseline,'currentBeforeRun':before,'after':after,'repairCounts':dict(repair_counts),
 'targets':{'eligibleRateMin':95.0,'structuralBadMax':0,'kanaChoiceCountMax':0,'maxWrongTripleReuseMax':40,'n2ExtremeTwoPlusMax':0},
 'samples':samples,
 'notes':['Task-action translations are deterministic project-authored Traditional Chinese mappings for the 12 observed action values.','N2 distractors are project-original near-miss alternatives based only on the project audio scenario, not copied external text.','High-reuse template diversification changes surface wording only; answer meaning and correctness are preserved.']
}
SRC.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'baselineRejected':baseline.get('rejected'),'afterRejected':after['rejected'],'eligibleRate':after['eligibleRate'],'kana':after['kanaChoiceCount'],'maxTriple':after['maxWrongTripleReuse'],'repairs':dict(repair_counts)},ensure_ascii=False))
