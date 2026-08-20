#!/usr/bin/env python3
"""Build one exact-key delta catalog for hosted vocabulary audio engines.

The delta is accepted only when its exact reading|written key set is identical to
all vocabulary forms published by the current strict review: 337 direct-reviewed
+ 375 source-check-approved + 1 post-review residual = 713 exact keys.
"""
from __future__ import annotations
import json
from pathlib import Path

DESIRED=Path('audit/vocab/results/desired_word_voice_catalog.json')
HOSTED={
 'voicevox':Path('word-voicevox-catalog.json'),
 'supertonic3':Path('word-supertonic3-catalog.json'),
 'aivis':Path('word-aivis-catalog.json'),
}
OUT=Path('word-audio-delta-catalog.json')

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def key(reading,word):return f'{str(reading or "").strip()}|{str(word or reading or "").strip()}'

def reviewed_keys():
 direct_auto=load('data/coverage_additions.json').get('additions') or []
 source_auto=load('data/coverage_sourcecheck_additions.json').get('additions') or []
 canonical=load('data/coverage_manual_meanings.json').get('entries') or []
 source_manual=load('data/coverage_sourcecheck_manual_meanings.json').get('entries') or []
 post_manual=load('data/coverage_postreview_manual_meanings.json').get('entries') or []
 if len(direct_auto)!=152 or len(source_auto)!=309 or len(canonical)<185 or len(source_manual)!=66 or len(post_manual)!=1:
  raise SystemExit(f'Reviewed vocabulary artifact count drift: direct_auto={len(direct_auto)}, source_auto={len(source_auto)}, canonical={len(canonical)}, source_manual={len(source_manual)}, post={len(post_manual)}')
 direct={key(x.get('reading'),x.get('word')) for x in direct_auto}
 direct.update(key(x[1],x[2]) for x in canonical[:185])
 source={key(x.get('reading'),x.get('word')) for x in source_auto}
 source.update(key(x[1],x[2]) for x in source_manual)
 post={key(x[1],x[2]) for x in post_manual}
 if len(direct)!=337 or len(source)!=375 or len(post)!=1:
  raise SystemExit(f'Reviewed exact-key count drift: direct={len(direct)}, source={len(source)}, post={len(post)}')
 overlap=(direct&source)|(direct&post)|(source&post)
 if overlap:raise SystemExit(f'Reviewed phases overlap on {len(overlap)} exact keys')
 return direct|source|post

def main():
 d=load(DESIRED);rows=d.get('words') or [];desired={str(x['key']):x for x in rows}
 if len(desired)!=int(d.get('wordCount',-1)):raise SystemExit('Desired catalog count mismatch')
 missing_sets={}
 for name,path in HOSTED.items():
  h=load(path);words=h.get('words') or {}
  if not isinstance(words,dict):raise SystemExit(f'{name} words mapping invalid')
  missing_sets[name]=set(desired)-set(words)
 base=missing_sets['voicevox']
 for name,s in missing_sets.items():
  if s!=base:raise SystemExit(f'Hosted missing-key sets differ: voicevox={len(base)}, {name}={len(s)}')
 reviewed=reviewed_keys()
 if base!=reviewed:
  missing_reviewed=reviewed-base;unexpected_missing=base-reviewed
  raise SystemExit(f'Hosted missing set is not the reviewed-addition set: reviewed_not_missing={len(missing_reviewed)}, unrelated_missing={len(unexpected_missing)}')
 items=[]
 for k in sorted(base):
  x=desired[k];items.append({'id':str(x['id']),'key':k,'reading':str(x['reading']),'written':str(x['written']),'level':str(x['level']),'estimated':bool(x.get('estimated')),'shard':0})
 if len({x['id'] for x in items})!=len(items):raise SystemExit('Delta stable IDs are not unique')
 out={'version':2,'status':'delta-source','engine':'shared-word-audio-delta','coverageRule':'exact reading|written-form','desiredWordCount':len(desired),'existingHostedWordCount':len(desired)-len(items),'wordCount':len(items),'deltaWordCount':len(items),'reviewedExactKeyCount':len(reviewed),'missingSetEqualsReviewedAdditions':True,'reviewedComponents':{'direct':337,'sourcecheckApproved':375,'postreviewResidual':1},'shardCount':1,'shardCounts':[len(items)],'items':items,'words':{x['key']:[x['id'],0] for x in items}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 print({'desired':len(desired),'delta':len(items),'reviewed':len(reviewed),'set_equality':base==reviewed,'shards':1})
if __name__=='__main__':main()
