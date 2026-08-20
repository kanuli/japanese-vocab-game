#!/usr/bin/env python3
"""Audit hosted vocabulary voice catalogs against the exact browser runtime inventory.

Base catalogs remain immutable; optional delta catalogs are unioned with base coverage.
Coverage is exact reading|written-form. The report preserves both the original base
missing count and the effective missing count after any ready delta catalog.
"""
from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
KANA=re.compile(r'^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$')

def load_desired(path:Path):
 d=json.loads(path.read_text(encoding='utf-8'));rows=d.get('words') or [];out={}
 for r in rows:
  key=str(r.get('key') or '')
  if not key or '|' not in key:raise SystemExit(f'Bad desired key: {key!r}')
  reading,written=key.split('|',1);out[key]={'reading':reading,'written':written,'level':r.get('level'),'id':r.get('id')}
 if len(out)!=int(d.get('wordCount',-1)):raise SystemExit('Desired catalog count mismatch')
 return d,out

def load_hosted(path:Path,required=True):
 if not path.exists():
  if required:raise SystemExit(f'Missing required hosted catalog: {path}')
  return None,set()
 d=json.loads(path.read_text(encoding='utf-8'));words=d.get('words') or {}
 if not isinstance(words,dict):raise SystemExit(f'{path}: hosted words is not a mapping')
 if len(words)!=int(d.get('wordCount',-1)):raise SystemExit(f'{path}: wordCount mismatch')
 return d,set(words)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--desired',default='audit/vocab/results/desired_word_voice_catalog.json');ap.add_argument('--voicevox',default='word-voicevox-catalog.json');ap.add_argument('--supertonic',default='word-supertonic3-catalog.json');ap.add_argument('--aivis',default='word-aivis-catalog.json');ap.add_argument('--voicevox-delta',default='word-voicevox-delta-catalog.json');ap.add_argument('--supertonic-delta',default='word-supertonic3-delta-catalog.json');ap.add_argument('--aivis-delta',default='word-aivis-delta-catalog.json');ap.add_argument('--results',default='audit/vocab/results');args=ap.parse_args();out=Path(args.results);out.mkdir(parents=True,exist_ok=True)
 desired_meta,desired=load_desired(Path(args.desired));desired_keys=set(desired);invalid=[k for k,v in desired.items() if not v['reading'] or not KANA.fullmatch(v['reading'])]
 specs=[('voicevox',Path(args.voicevox),Path(args.voicevox_delta)),('supertonic3',Path(args.supertonic),Path(args.supertonic_delta)),('aivis',Path(args.aivis),Path(args.aivis_delta))]
 engines={};missing_union=set();base_missing_union=set()
 for name,base_path,delta_path in specs:
  meta,base_keys=load_hosted(base_path,True);delta_meta,delta_keys=load_hosted(delta_path,False)
  if delta_meta is not None and delta_meta.get('status')!='ready':raise SystemExit(f'{delta_path}: delta catalog exists but is not ready')
  overlap=base_keys&delta_keys
  if overlap:raise SystemExit(f'{name}: base/delta overlap contains {len(overlap)} exact keys')
  base_missing=desired_keys-base_keys;combined=base_keys|delta_keys;missing=desired_keys-combined;extra=combined-desired_keys;base_missing_union|=base_missing;missing_union|=missing
  engines[name]={
   'status':meta.get('status'),'base_hosted_word_count':len(base_keys),'delta_status':delta_meta.get('status') if delta_meta else 'not-generated','delta_hosted_word_count':len(delta_keys),'combined_hosted_exact_keys':len(combined),'desired_word_count':len(desired_keys),'base_missing_hosted_exact_keys':len(base_missing),'missing_hosted_exact_keys':len(missing),'extra_hosted_exact_keys':len(extra),'voice_count':meta.get('speakerCount',meta.get('voiceCount')),'base_recording_count':meta.get('recordingCount'),'delta_recording_count':delta_meta.get('recordingCount') if delta_meta else 0,
  }
  with (out/f'voice_missing_{name}.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['key','reading','written','level'])
   for k in sorted(missing):x=desired[k];w.writerow([k,x['reading'],x['written'],x['level']])
 with (out/'voice_missing_union.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['key','reading','written','level'])
  for k in sorted(missing_union):x=desired[k];w.writerow([k,x['reading'],x['written'],x['level']])
 summary={'coverage_rule':'exact reading|written-form','desired_word_count':len(desired_keys),'desired_source':desired_meta.get('source'),'invalid_or_non_kana_readings':invalid,'invalid_reading_count':len(invalid),'engines':engines,'base_missing_union_count':len(base_missing_union),'missing_union_count':len(missing_union),'hosted_voice_coverage_complete':all(x['missing_hosted_exact_keys']==0 and x['combined_hosted_exact_keys']==len(desired_keys) for x in engines.values()) and not invalid,'fallback_note':'Browser/device synthesis may speak hosted misses, but completion requires combined base+delta hosted coverage for every exact key.'}
 (out/'voice_coverage_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
