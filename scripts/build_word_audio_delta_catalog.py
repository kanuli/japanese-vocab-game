#!/usr/bin/env python3
"""Build one exact-key delta catalog for hosted vocabulary audio engines."""
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

def main():
 d=json.loads(DESIRED.read_text(encoding='utf-8'));rows=d.get('words') or []
 desired={str(x['key']):x for x in rows}
 if len(desired)!=int(d.get('wordCount',-1)):raise SystemExit('Desired catalog count mismatch')
 missing_sets={}
 for name,path in HOSTED.items():
  h=json.loads(path.read_text(encoding='utf-8'));words=h.get('words') or {}
  if not isinstance(words,dict):raise SystemExit(f'{name} words mapping invalid')
  missing_sets[name]=set(desired)-set(words)
 base=missing_sets['voicevox']
 for name,s in missing_sets.items():
  if s!=base:raise SystemExit(f'Hosted missing-key sets differ: voicevox={len(base)}, {name}={len(s)}')
 if not base:
  print('No missing hosted vocabulary audio keys.');items=[]
 else:
  items=[]
  for key in sorted(base):
   x=desired[key];items.append({'id':str(x['id']),'key':key,'reading':str(x['reading']),'written':str(x['written']),'level':str(x['level']),'estimated':bool(x.get('estimated'))})
 if len({x['id'] for x in items})!=len(items):raise SystemExit('Delta stable IDs are not unique')
 out={'version':1,'status':'delta-source','coverageRule':'exact reading|written-form','desiredWordCount':len(desired),'existingHostedWordCount':len(desired)-len(items),'deltaWordCount':len(items),'items':items,'words':{x['key']:[x['id'],0] for x in items}}
 OUT.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 print({'desired':len(desired),'delta':len(items)})
if __name__=='__main__':main()
