#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json

ROOT=Path(__file__).resolve().parents[1]
LEVELS=['N5','N4','N3','N2','N1']
report_path=ROOT/'data/coverage_gap_audit.json'
qa_path=ROOT/'data/reference_expansion_quality_report.json'
catalog_path=ROOT/'listening-original-catalog.json'

report=json.loads(report_path.read_text(encoding='utf-8'))
qa=json.loads(qa_path.read_text(encoding='utf-8'))
catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
actual=qa.get('listening',{}).get('typeCounts',{})
if not actual:
    raise SystemExit('reference_expansion_quality_report.json has no listening.typeCounts')

out={}
for level in LEVELS:
    counter=Counter()
    base_rows=[x for x in catalog.get('items',[]) if str(x.get('level','')).upper()==level]
    for x in base_rows:
        counter[str(x.get('typeZh') or x.get('type') or '未分類')]+=1
    for typ,n in actual.get(level,{}).items():
        counter[str(typ)]+=int(n)
    expansion_n=int(qa.get('listening',{}).get('perLevel',{}).get(level,0))
    out[level]={
        'catalogCount':len(base_rows),
        'uniqueExpansionCount':expansion_n,
        'combinedDiagnosticCount':len(base_rows)+expansion_n,
        'distinctTypes':len(counter),
        'topTypes':counter.most_common(20),
        'underrepresented':sorted([[k,v] for k,v in counter.items() if v<5],key=lambda x:(x[1],x[0]))
    }
report['version']='2026-08-27-gap-audit-v4'
report['listening']=out
report.setdefault('methodology',{})['listeningDedup']='Listening subtype counts are reconciled from the QA-executed, sentence-deduplicated expansion pool; duplicate candidate templates are not counted as database growth.'
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'listening':{k:{'uniqueExpansionCount':v['uniqueExpansionCount'],'underrepresented':v['underrepresented']} for k,v in out.items()}},ensure_ascii=False))
