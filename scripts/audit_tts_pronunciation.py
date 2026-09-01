#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re,tempfile,urllib.parse,urllib.request,wave
from pathlib import Path

TESTS=[
 ('ごみばこ','ごみばこ'),('あんさつ','あんさつ'),('たまご','たまご'),('れいぞうこ','れいぞうこ'),
 ('くつした','くつした'),('えんぴつ','えんぴつ'),('しんぶん','しんぶん'),('でんしゃ','でんしゃ'),
 ('びょういん','びょういん'),('きょうしつ','きょうしつ'),('けしごむ','けしごむ'),('まどぐち','まどぐち')]

def req_json(url,method='GET',body=None):
    r=urllib.request.Request(url,data=body,method=method)
    with urllib.request.urlopen(r,timeout=180) as x:return json.loads(x.read().decode('utf-8'))
def req_bytes(url,method='GET',body=None,headers=None):
    r=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(r,timeout=240) as x:return x.read()
def kata_to_hira(s):
    return ''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c for c in (s or ''))
def norm(s):
    return re.sub(r'[^ぁ-んー]','',kata_to_hira(s or ''))
def query_for(base,text,sid):
    q=urllib.parse.urlencode({'text':text+'。','speaker':sid})
    return req_json(f'{base}/audio_query?{q}',method='POST',body=b'')
def parsed_reading(aq):
    kana=norm(str(aq.get('kana') or ''))
    if kana:return kana
    out=[]
    for phrase in aq.get('accent_phrases') or []:
        for mora in phrase.get('moras') or []:
            out.append(str(mora.get('text') or ''))
        pm=phrase.get('pause_mora') or {}
        if pm.get('text'):out.append(str(pm['text']))
    return norm(''.join(out))
def synth_from_query(base,aq,sid):
    body=json.dumps(aq,ensure_ascii=False).encode('utf-8')
    return req_bytes(f"{base}/synthesis?{urllib.parse.urlencode({'speaker':sid})}",method='POST',body=body,headers={'Content-Type':'application/json'})
def wav_seconds(raw):
    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(raw);p=Path(f.name)
    try:
        with wave.open(str(p),'rb') as w:return w.getnframes()/float(w.getframerate())
    finally:p.unlink(missing_ok=True)
def canonical_voicevox(base):
    preferred=('ノーマル','Normal','NORMAL','通常');out=[]
    for sp in req_json(base+'/speakers'):
        styles=list(sp.get('styles') or [])
        if not styles:continue
        st=next((x for x in styles if str(x.get('name','')).strip() in preferred),styles[0])
        out.append({'name':str(sp.get('name','')).strip(),'style':str(st.get('name','')).strip(),'id':int(st['id'])})
    return out[:43]
def all_aivis(base):
    out=[]
    for sp in req_json(base+'/speakers'):
        for st in sp.get('styles') or []:
            out.append({'name':str(sp.get('name','')).strip(),'style':str(st.get('name','')).strip(),'id':int(st['id'])})
    return out[:4]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--engine',choices=['voicevox','aivis'],required=True);ap.add_argument('--base',required=True);ap.add_argument('--out',required=True);ap.add_argument('--start',type=int,default=0);ap.add_argument('--limit',type=int,default=999)
    a=ap.parse_args();voices=canonical_voicevox(a.base) if a.engine=='voicevox' else all_aivis(a.base)
    voices=voices[a.start:a.start+a.limit]
    if not voices:raise SystemExit('no voices selected')
    rows=[];hard=[]
    for v in voices:
        for text,expected in TESTS:
            aq=query_for(a.base,text,int(v['id']));parsed=parsed_reading(aq);exp=norm(expected)
            wav=synth_from_query(a.base,aq,int(v['id']));secs=wav_seconds(wav)
            # Hard gate is deterministic engine parsing plus a very loose non-truncation duration floor.
            # ASR is intentionally not a hard gate for isolated Japanese words because it caused massive false failures.
            ending_ok=len(exp)<2 or parsed.endswith(exp[-2:])
            parse_ok=(parsed==exp or exp in parsed) and ending_ok
            duration_ok=secs>=max(0.18,0.045*len(exp))
            ok=parse_ok and duration_ok
            row={'engine':a.engine,**v,'text':text,'expected':expected,'parsed':parsed,'durationSec':round(secs,3),'parseOk':parse_ok,'durationOk':duration_ok,'ok':ok}
            rows.append(row)
            if not ok:hard.append(row)
    summary={'version':2,'engine':a.engine,'voiceStart':a.start,'voiceCount':len(voices),'testCount':len(TESTS),'recordingChecks':len(rows),'hardFailures':len(hard),'status':'FAIL' if hard else 'PASS','hardFailureRows':hard,'rows':rows}
    Path(a.out).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('engine','voiceStart','voiceCount','recordingChecks','hardFailures','status')},ensure_ascii=False))
    if hard:raise SystemExit(2)
if __name__=='__main__':main()
