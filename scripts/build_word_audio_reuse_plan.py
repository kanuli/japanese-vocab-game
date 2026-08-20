#!/usr/bin/env python3
"""Plan exact-key hosted audio coverage by reusing identical readings first.

Vocabulary identity remains exact reading|written-form. Audio identity is the spoken
kana reading: if a new exact key has a reading already recorded in a hosted base
library, the existing recording is a lossless pronunciation reuse and no synthesis
is required. Only readings absent from the base library need new recordings.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

DELTA=Path('word-audio-delta-catalog.json')
BASES={
    'voicevox':Path('word-voicevox-catalog.json'),
    'supertonic3':Path('word-supertonic3-catalog.json'),
    'aivis':Path('word-aivis-catalog.json'),
}
OUT=Path('audit/vocab/results/voice_delta_reuse_plan.json')
SYNTH=Path('word-audio-synthesis-delta-catalog.json')

def load_base(path:Path):
    d=json.loads(path.read_text(encoding='utf-8'))
    words=d.get('words') or {}
    if not isinstance(words,dict) or len(words)!=int(d.get('wordCount',-1)):
        raise SystemExit(f'Bad base catalog: {path}')
    by_reading=defaultdict(list)
    for key,lookup in words.items():
        reading,sep,written=str(key).partition('|')
        if not sep or not reading: raise SystemExit(f'Bad base key in {path}: {key}')
        by_reading[reading].append((key,lookup))
    for reading in by_reading:
        by_reading[reading].sort(key=lambda x:x[0])
    return d,words,by_reading

def main():
    delta=json.loads(DELTA.read_text(encoding='utf-8'))
    items=list(delta.get('items') or [])
    if len(items)!=713 or int(delta.get('wordCount',-1))!=713:
        raise SystemExit('Expected the reviewed 713-key delta source')
    bases={name:load_base(path) for name,path in BASES.items()}
    base_key_sets={name:set(data[1]) for name,data in bases.items()}
    if len({frozenset(x) for x in base_key_sets.values()})!=1:
        raise SystemExit('Hosted base exact-key sets differ across engines')

    reuse=[];synth=[]
    for item in items:
        key=str(item['key']);reading=str(item['reading'])
        targets={}
        for name,(_,_,by_reading) in bases.items():
            candidates=by_reading.get(reading) or []
            if candidates:
                target_key,lookup=candidates[0]
                targets[name]={'target_key':target_key,'lookup':lookup}
        if len(targets)==len(bases):
            reuse.append({'key':key,'reading':reading,'written':item['written'],'targets':targets})
        elif not targets:
            synth.append(dict(item))
        else:
            raise SystemExit(f'Partial same-reading availability across engines: {key} -> {sorted(targets)}')

    synth_words={x['key']:[x['id'],0] for x in synth}
    synth_catalog={
        'version':1,'status':'synthesis-delta-source','engine':'shared-word-audio-synthesis-delta',
        'coverageRule':'exact reading|written-form; synthesize only readings absent from all base hosted catalogs',
        'reviewedExactKeyCount':len(items),'reuseBaseReadingCount':len(reuse),
        'wordCount':len(synth),'deltaWordCount':len(synth),'shardCount':1,'shardCounts':[len(synth)],
        'items':synth,'words':synth_words,
    }
    SYNTH.write_text(json.dumps(synth_catalog,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    out={
        'status':'PASS','reviewed_exact_keys':len(items),'reuse_base_reading_count':len(reuse),
        'synthesis_required_exact_keys':len(synth),'coverage_after_reuse_and_synthesis':len(reuse)+len(synth),
        'engines':{name:{'base_word_count':len(data[1]),'base_unique_readings':len(data[2])} for name,data in bases.items()},
        'reuse':reuse,'synthesis_keys':[x['key'] for x in synth],
    }
    if out['coverage_after_reuse_and_synthesis']!=713: raise SystemExit('Audio coverage plan does not account for all reviewed keys')
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k not in ('reuse','synthesis_keys')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
