#!/usr/bin/env python3
import json,re,sys,unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from faster_whisper import WhisperModel
from pykakasi import kakasi

ROOT=Path(sys.argv[1] if len(sys.argv)>1 else 'word-supertonic3-v3-qa')
META=sorted(ROOT.glob('*.json'))
if not META: raise SystemExit('No QA metadata found')
rows=[]
for p in META:
    x=json.loads(p.read_text(encoding='utf-8'))
    if isinstance(x,list): rows.extend(x)
if not rows: raise SystemExit('No QA rows found')

kks=kakasi()
def norm(s):
    s=unicodedata.normalize('NFKC',str(s or ''))
    try:s=''.join(x['hira'] for x in kks.convert(s))
    except Exception:pass
    s=s.replace('ゔ','う゛')
    return ''.join(re.findall(r'[ぁ-ゖー]',s))

def sim(a,b):
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0

# Base is materially more reliable than tiny for isolated Japanese vocabulary,
# while remaining practical for the deterministic QA sample rather than all 223k files.
model=WhisperModel('base',device='cpu',compute_type='int8')
results=[];by_voice=defaultdict(list);hard=[]
for i,r in enumerate(rows,1):
    f=ROOT/r['file']
    if not f.is_file(): raise SystemExit(f'Missing QA audio: {f}')
    segments,_=model.transcribe(str(f),language='ja',beam_size=1,temperature=0.0,
        vad_filter=False,condition_on_previous_text=False)
    heard=''.join(seg.text for seg in segments).strip()
    exp=norm(r['reading']);got=norm(heard);score=sim(exp,got)
    prefix_drop=bool(got and exp.startswith(got) and len(got)<len(exp))
    severe_short=bool(got and len(got)<=max(1,len(exp)-2) and score<0.80)
    known=bool(r.get('knownRegression'))
    # Known production failures must transcribe very closely; sampled words use
    # a looser threshold because ASR itself is imperfect on isolated short words.
    ok=(score>=0.72 and not prefix_drop and not severe_short)
    if known: ok=(score>=0.88 and not prefix_drop and not severe_short)
    rec={**r,'expectedNormalized':exp,'transcript':heard,'heardNormalized':got,
         'similarity':round(score,3),'prefixDrop':prefix_drop,'severeShort':severe_short,'ok':ok}
    results.append(rec);by_voice[r['voice']].append(rec)
    if known and not ok: hard.append(rec)
    if i%100==0 or i==len(rows): print('QA',i,'/',len(rows),flush=True)

summary={}
failed=False
for voice,items in sorted(by_voice.items()):
    usable=[x for x in items if x['heardNormalized']]
    passed=[x for x in usable if x['ok']]
    rate=len(passed)/max(1,len(usable))
    prefix=sum(1 for x in usable if x['prefixDrop'])
    severe=sum(1 for x in usable if x['severeShort'])
    summary[voice]={'samples':len(items),'usable':len(usable),'passed':len(passed),
                    'passRate':round(rate,4),'prefixDrops':prefix,'severeShort':severe}
    # Fail publication on a systematic ending-drop signal or poor voice-level sample quality.
    if prefix>1 or severe>2 or (len(usable)>=80 and rate<0.82): failed=True
    print(voice,summary[voice])
if hard:
    failed=True
    print('Known regression failures:')
    for x in hard: print(x['voice'],x['reading'],'=>',x['transcript'],x['similarity'])

out={'version':1,'status':'fail' if failed else 'pass','sampleCount':len(results),
     'voices':summary,'knownRegressionFailures':hard,'results':results}
Path('word-supertonic3-pronunciation-qa.json').write_text(
    json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
if failed: raise SystemExit('Pronunciation QA FAILED; production switch blocked')
print('Pronunciation QA PASS:',len(results),'samples across',len(summary),'voices')
