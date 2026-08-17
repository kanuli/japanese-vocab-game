#!/usr/bin/env python3
import json,re
from pathlib import Path
SRC=Path('listening-original-catalog.json')
OUT=Path('pronunciation-original-audio-catalog.json')
d=json.loads(SRC.read_text(encoding='utf-8'))
items=list(d.get('items') or [])
if len(items)!=6690:
    raise SystemExit(f'Expected 6,690 original pronunciation sentences, got {len(items)}')
levels={'N1':0,'N2':0,'N3':0,'N4':0,'N5':0}
questions={}; text_map={}; seq={k:0 for k in levels}
def norm(s):
    return re.sub(r'[\s　。、，,.！？!?「」『』（）()]','',str(s or '').strip().lower())
for row in items:
    level=str(row.get('level') or '').upper().strip()
    text=str(row.get('jp') or '').strip()
    if level not in levels or not text:
        raise SystemExit(f'Invalid original row: level={level!r} text={text!r}')
    seq[level]+=1; levels[level]+=1
    qid=f'{level}-O-{seq[level]:05d}'
    if '/' in qid or '\\' in qid:
        raise SystemExit('Unsafe qid')
    questions[qid]={'text':text,'level':level,'sourceId':str(row.get('id') or '')}
    k=norm(text)
    if k and k not in text_map: text_map[k]=qid
out={'version':1,'status':'catalog','engine':'pronunciation-original-hosted','language':'ja','questionCount':len(questions),'levels':levels,'questions':questions,'textMap':text_map}
OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Pronunciation original catalog:',len(questions),levels,'unique normalized=',len(text_map))
