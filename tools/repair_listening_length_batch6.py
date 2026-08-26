#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json, re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'listening-original-catalog.json'
REPORT=ROOT/'data/listening_length_batch6_report.json'
PUNCT=re.compile(r'[\s，。！？、,.!?「」『』（）()]')
KANA=re.compile(r'[ぁ-ゖァ-ヺ]')

def norm(s): return PUNCT.sub('',str(s or '')).strip()

def length_bad(x):
    correct=str(x.get('correctZh','')).strip(); base=max(1,len(norm(correct))); target=norm(correct)
    wrong=[str(v or '').strip() for v in x.get('choicesZh',[]) if norm(v)!=target]
    return sum((len(norm(w))/base)<.45 or (len(norm(w))/base)>2.2 for w in wrong)>=2

# Canonical task translations produced by Batch 5. Short forms make every option
# read as an answer to “what should be done first?” without changing the action.
ACTIONS={
 'メールを確認する':('確認電郵','先確認電郵'),
 '予約を変更する':('更改預約','先更改預約'),
 '薬を受け取る':('領取藥物','先領取藥物'),
 '会議室を予約する':('預約會議室','先預約會議室'),
 '本を図書館へ返す':('把書歸還圖書館','先歸還圖書'),
 '切符を買う':('購買車票','先購買車票'),
 '担当者に電話する':('致電負責人','先致電負責人'),
 '荷物を二階へ運ぶ':('把行李搬到二樓','先搬行李到二樓'),
 '申込書に名前を書く':('在申請表上填寫姓名','先填寫申請表姓名'),
 'コピーを三部取る':('影印三份文件','先影印三份文件'),
 '資料を受付に出す':('把資料交到接待處','先把資料交接待處'),
 '鍵を受付へ返す':('把鑰匙交還接待處','先把鑰匙交接待處')
}
INV={zh:jp for jp,(zh,short) in ACTIONS.items()}
NEAR={
 '更改預約':['先保留原預約','先取消原預約','先確認原預約'],
 '確認電郵':['先查看電郵標題','先回覆電郵','稍後確認電郵'],
 '領取藥物':['先詢問藥物','稍後領取藥物','先確認藥物'],
 '購買車票':['先查看車票','稍後購買車票','先確認車票價格'],
 '在申請表上填寫姓名':['先填寫申請表地址','先檢查申請表姓名','稍後填寫申請表姓名']
}
TARGETS=set(NEAR)

def choose_options(x):
    old_correct=str(x.get('correctZh','')).strip()
    if old_correct not in TARGETS: return None
    correct_jp=INV.get(old_correct)
    if not correct_jp: return None
    correct_short=ACTIONS[correct_jp][1]
    jptext=str(x.get('jp',''))
    candidates=[]
    # Prefer actions explicitly mentioned in the audio, because sequence errors are
    # the strongest distractors for task-understanding questions.
    for ajp,(azh,short) in ACTIONS.items():
        if ajp==correct_jp: continue
        if ajp in jptext and short not in candidates: candidates.append(short)
    # Add concise same-action near-misses until there are three plausible wrongs.
    for z in NEAR[old_correct]:
        if z!=correct_short and z not in candidates: candidates.append(z)
    # Last-resort same-domain actions are still valid task distractors, but only
    # used when the source mentions too few actions.
    for ajp,(azh,short) in ACTIONS.items():
        if ajp!=correct_jp and short not in candidates: candidates.append(short)
    base=max(1,len(norm(correct_short)))
    good=[]
    for z in candidates:
        r=len(norm(z))/base
        if .55<=r<=1.8 and z not in good: good.append(z)
    if len(good)<3: return None
    # Deterministic rotation by numeric id keeps repeated sets from clustering.
    m=re.search(r'(\d+)$',str(x.get('id',''))); off=(int(m.group(1)) if m else 0)%len(good)
    rot=good[off:]+good[:off]
    wrong=rot[:3]
    # Ensure at least one same-action near miss survives.
    if not any(z in NEAR[old_correct] for z in wrong):
        wrong[-1]=NEAR[old_correct][0]
    out=[correct_short]+wrong
    # Stable display order varies by id while preserving exact one correct answer.
    shift=(int(m.group(1)) if m else 0)%4
    out=out[shift:]+out[:shift]
    return correct_short,out

data=json.loads(SRC.read_text(encoding='utf-8'))
items=data.get('items',[])
before_ids=[str(x.get('id')) for x in items if length_bad(x)]
before_by=Counter(str(x.get('level','')).upper() for x in items if length_bad(x))
changed=0; failures=[]; samples=[]
for x in items:
    if not length_bad(x): continue
    old={k:x.get(k) for k in ('id','level','correctZh','choicesZh','explanationZh')}
    built=choose_options(x)
    if not built:
        failures.append({'id':x.get('id'),'reason':'no deterministic balanced option set','correct':x.get('correctZh')}); continue
    correct,choices=built
    x['correctZh']=correct
    x['choicesZh']=choices
    tp=str(x.get('typeZh') or x.get('type') or '任務理解')
    x['explanationZh']=f'{tp}：比較錄音中的先後順序與優先事項。正確答案：{correct}'
    if length_bad(x):
        failures.append({'id':x.get('id'),'reason':'still length-outlier after repair','choices':choices}); continue
    if len({norm(v) for v in choices})!=4 or sum(norm(v)==norm(correct) for v in choices)!=1:
        failures.append({'id':x.get('id'),'reason':'structural uniqueness failure','choices':choices}); continue
    if any(KANA.search(str(v)) for v in choices+[correct]):
        failures.append({'id':x.get('id'),'reason':'kana leakage after repair'}); continue
    changed+=1
    if len(samples)<12:samples.append({'id':x.get('id'),'level':x.get('level'),'beforeCorrect':old['correctZh'],'afterCorrect':correct,'beforeChoices':old['choicesZh'],'afterChoices':choices})

after=[x for x in items if length_bad(x)]
after_by=Counter(str(x.get('level','')).upper() for x in after)
report={
 'version':'2026-08-27-listening-length-batch6-v1',
 'before':{'weakCount':len(before_ids),'weakByLevel':dict(sorted(before_by.items()))},
 'repair':{'changed':changed,'failures':failures[:50]},
 'after':{'weakCount':len(after),'weakByLevel':dict(sorted(after_by.items()))},
 'targets':{'weakCountMax':0,'structuralErrorsMax':0,'kanaChoiceCountMax':0},
 'samples':samples,
 'passed':len(after)==0 and not failures
}
SRC.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'before':len(before_ids),'changed':changed,'after':len(after),'failures':len(failures),'passed':report['passed']},ensure_ascii=False))
if not report['passed']: raise SystemExit('Batch 6 listening length repair did not fully converge')
