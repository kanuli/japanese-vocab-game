#!/usr/bin/env python3
"""Audit hosted vocabulary voice catalogs against the exact runtime word inventory.

The desired inventory is produced by scripts/build_word_voicevox_catalog.mjs, which
uses the same core + reviewed advanced layers as the browser runtime. Coverage is
exact reading|written-form; related spellings never substitute for each other.
"""
from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path

KANA=re.compile(r'^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$')

def load_desired(path:Path):
    d=json.loads(path.read_text(encoding='utf-8'))
    rows=d.get('words') or []
    out={}
    for r in rows:
        key=str(r.get('key') or '')
        if not key or '|' not in key: raise SystemExit(f'Bad desired key: {key!r}')
        reading,written=key.split('|',1)
        out[key]={'reading':reading,'written':written,'level':r.get('level'),'id':r.get('id')}
    if len(out)!=int(d.get('wordCount',-1)): raise SystemExit('Desired catalog count mismatch')
    return d,out

def load_hosted(path:Path):
    d=json.loads(path.read_text(encoding='utf-8'))
    words=d.get('words') or {}
    if not isinstance(words,dict): raise SystemExit(f'{path}: hosted words is not a mapping')
    if len(words)!=int(d.get('wordCount',-1)): raise SystemExit(f'{path}: wordCount mismatch')
    return d,set(words)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--desired',default='audit/vocab/results/desired_word_voice_catalog.json')
    ap.add_argument('--voicevox',default='word-voicevox-catalog.json')
    ap.add_argument('--supertonic',default='word-supertonic3-catalog.json')
    ap.add_argument('--aivis',default='word-aivis-catalog.json')
    ap.add_argument('--results',default='audit/vocab/results')
    args=ap.parse_args();out=Path(args.results);out.mkdir(parents=True,exist_ok=True)
    desired_meta,desired=load_desired(Path(args.desired));desired_keys=set(desired)
    invalid=[k for k,v in desired.items() if not v['reading'] or not KANA.fullmatch(v['reading'])]
    engines={}
    missing_union=set()
    for name,path in [('voicevox',args.voicevox),('supertonic3',args.supertonic),('aivis',args.aivis)]:
        meta,keys=load_hosted(Path(path));missing=desired_keys-keys;extra=keys-desired_keys;missing_union|=missing
        engines[name]={
            'status':meta.get('status'),
            'hosted_word_count':len(keys),
            'desired_word_count':len(desired_keys),
            'missing_hosted_exact_keys':len(missing),
            'extra_hosted_exact_keys':len(extra),
            'voice_count':meta.get('speakerCount',meta.get('voiceCount')),
            'recording_count':meta.get('recordingCount'),
        }
        with (out/f'voice_missing_{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['key','reading','written','level'])
            for k in sorted(missing):
                x=desired[k];w.writerow([k,x['reading'],x['written'],x['level']])
    with (out/'voice_missing_union.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['key','reading','written','level'])
        for k in sorted(missing_union):
            x=desired[k];w.writerow([k,x['reading'],x['written'],x['level']])
    summary={
        'coverage_rule':'exact reading|written-form',
        'desired_word_count':len(desired_keys),
        'desired_source':desired_meta.get('source'),
        'invalid_or_non_kana_readings':invalid,
        'invalid_reading_count':len(invalid),
        'engines':engines,
        'missing_union_count':len(missing_union),
        'hosted_voice_coverage_complete':all(x['missing_hosted_exact_keys']==0 for x in engines.values()) and not invalid,
        'fallback_note':'Browser/device synthesis may still speak hosted misses, but hosted coverage is not considered complete until missing_hosted_exact_keys is zero.'
    }
    (out/'voice_coverage_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
