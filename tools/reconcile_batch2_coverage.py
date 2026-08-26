#!/usr/bin/env python3
from pathlib import Path
import json, re

ROOT=Path(__file__).resolve().parents[1]
report_path=ROOT/'data/coverage_gap_audit.json'
report=json.loads(report_path.read_text(encoding='utf-8'))
topup=(ROOT/'conversation-function-topup.js').read_text(encoding='utf-8')

FUNCTIONS={
    'N4':{
        'change_reschedule':['変更','別の時間','改めて','振り替'],
        'recommendation':['ほうがいい','おすすめ','したほう']
    },
    'N3':{
        'procedure':['手続','受付','申請','提出']
    },
    'N2':{
        'exception':['例外','今回に限り','通常の方法以外','事情がある場合']
    }
}

conversation=report.setdefault('conversation',{})
level_functions=conversation.setdefault('levelFunctions',{})
for level,checks in FUNCTIONS.items():
    m=re.findall(rf'\{{"level":"{level}".*?"lines":\[.*?\]\}}',topup,re.S)
    text=' '.join(m)
    row=level_functions.setdefault(level,{'signalCounts':{},'weakExpected':[]})
    counts=row.setdefault('signalCounts',{})
    for fn,keys in checks.items():
        added=sum(text.count(k) for k in keys)
        counts[fn]=int(counts.get(fn,0))+added
    expected=list(row.get('weakExpected',[]))
    row['weakExpected']=[fn for fn in expected if int(counts.get(fn,0))<1]

failures=[]
for level,row in report.get('grammar',{}).items():
    if row.get('missing'):
        failures.append(f'grammar {level}: missing {row["missing"]}')
for level,row in report.get('listening',{}).items():
    if row.get('underrepresented'):
        failures.append(f'listening {level}: subtypes below five {row["underrepresented"]}')
if conversation.get('weakTopics'):
    failures.append(f'conversation weak topics: {conversation["weakTopics"]}')
for level,row in level_functions.items():
    if row.get('weakExpected'):
        failures.append(f'conversation {level}: weak functions {row["weakExpected"]}')

report['version']='2026-08-27-gap-audit-v5'
report.setdefault('methodology',{})['batch2']='Batch 2 raises targeted listening subtypes to at least five unique examples and reconciles remaining conversation communicative-function gaps without increasing scene count.'
report['batch2Validation']={
    'listeningFloor':5,
    'conversationTargets':FUNCTIONS,
    'failures':failures,
    'passed':not failures
}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({
    'listeningUnderrepresented':{k:v.get('underrepresented',[]) for k,v in report.get('listening',{}).items()},
    'weakTopics':conversation.get('weakTopics',[]),
    'weakFunctions':{k:v.get('weakExpected',[]) for k,v in level_functions.items()},
    'failures':failures,
    'passed':not failures
},ensure_ascii=False))
if failures:
    raise SystemExit(1)
