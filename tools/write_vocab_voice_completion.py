#!/usr/bin/env python3
"""Write the authoritative combined vocabulary + hosted-voice completion marker."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/'audit/vocab/results'

def load(path,required=True):
 p=ROOT/path
 if not p.exists():
  if required:raise SystemExit(f'Missing required completion input: {path}')
  return None
 return json.loads(p.read_text(encoding='utf-8'))

def main():
 vocab=load(Path('audit/vocab/results/vocab_coverage_phase_completion.json'))
 voice=load(Path('audit/vocab/results/voice_coverage_summary.json'))
 delta=load(Path('audit/vocab/results/voice_delta_completion.json'),False)
 vocab_ok=vocab.get('status')=='PASS' and int(vocab.get('actionable_recommended_additions_remaining',-1))==0
 voice_ok=bool(voice.get('hosted_voice_coverage_complete')) and int(voice.get('missing_union_count',-1))==0 and int(voice.get('invalid_reading_count',-1))==0
 base_missing=int(voice.get('base_missing_union_count',voice.get('missing_union_count',-1)))
 delta_required=base_missing>0
 delta_ok=(not delta_required) or (delta is not None and delta.get('status')=='PASS' and int(delta.get('exact_delta_words',-1))==base_missing)
 if vocab_ok and voice_ok and delta_ok:status='PASS'
 elif not vocab_ok:status='INCOMPLETE_VOCABULARY'
 else:status='INCOMPLETE_VOICE'
 out={
  'status':status,
  'completion_rule':'PASS only when reviewed vocabulary has zero actionable additions AND every browser-runtime exact reading|written key has hosted voice coverage after base+delta union.',
  'vocabulary':{
   'status':vocab.get('status'),
   'actionable_additions_remaining':vocab.get('actionable_recommended_additions_remaining'),
   'direct_runtime_covered':(vocab.get('direct_review_phase') or {}).get('runtime_covered'),
   'sourcecheck_runtime_covered':(vocab.get('sourcecheck_phase') or {}).get('approved_runtime_covered'),
   'residual_runtime_covered':(vocab.get('residual_cleanup_phase') or {}).get('runtime_covered'),
  },
  'hosted_voice':{
   'desired_exact_words':voice.get('desired_word_count'),
   'base_missing_exact_words':base_missing,
   'effective_missing_exact_words':voice.get('missing_union_count'),
   'invalid_readings':voice.get('invalid_reading_count'),
   'coverage_complete':voice.get('hosted_voice_coverage_complete'),
   'engines':voice.get('engines'),
  },
  'voice_delta':delta if delta is not None else {'status':'NOT_FINALIZED','exact_delta_words':None},
  'live_main_deployed':False,
  'live_main_note':'Audit completion is separate from selective deployment to main/GitHub Pages.'
 }
 (RES/'overall_vocab_voice_completion.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=False,indent=2))
 return 0
if __name__=='__main__':raise SystemExit(main())
