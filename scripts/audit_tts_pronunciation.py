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

# VOICEVOX/Aivis audio_query exposes a phonetic kana representation rather than
# always preserving dictionary spelling. Japanese long vowels therefore have
# equivalent spellings such as ぞう/ぞお, びょう/びょお and せい/せえ.
# Canonicalize both sides phonetically before applying the hard gate. This must
# NOT hide missing morae: ごみばこ -> ごみば remains different and still fails.
A=set('あかさたなはまやらわがざだばぱぁゃ')
I=set('いきしちにひみりぎじぢびぴぃ')
U=set('うくすつぬふむゆるぐずづぶぷぅゅ')
E=set('えけせてねへめれげぜでべぺぇ')
O=set('おこそとのほもよろをごぞどぼぽぉょ')
def vowel_of(c):
    if c in A:return 'a'
    if c in I:return 'i'
    if c in U:return 'u'
    if c in E:return 'e'
    if c in O:return 'o'
    return None
def phonetic_norm(s):
    src=norm(s);out=[];prev_vowel=None
    for c in src:
        if c=='う' and prev_vowel=='o':
            out.append('お');prev_vowel='o';continue
        if c=='い' and prev_vowel=='e':
            out.append('え');prev_vowel='e';continue
        out.append(c)
        v=vowel_of(c)
        if v:prev_vowel=v
        elif c not in {'っ','ん','ー'}:prev_vowel=None
    return ''.join(out)

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
            aq=query_for(a.base,text,int(v['id']));parsed=parsed_reading(aq)
            exp=norm(expected);pexp=phonetic_norm(exp);pparsed=phonetic_norm(parsed)
            wav=synth_from_query(a.base,aq,int(v['id']));secs=wav_seconds(wav)
            # Hard gate: engine parsing must preserve the complete phonetic mora sequence,
            # plus a loose duration floor to catch empty/severely truncated audio.
            ending_ok=len(pexp)<2 or pparsed.endswith(pexp[-2:])
            parse_ok=(pparsed==pexp or pexp in pparsed) and ending_ok
            duration_ok=secs>=max(0.18,0.045*len(exp))
            ok=parse_ok and duration_ok
            row={'engine':a.engine,**v,'text':text,'expected':expected,'parsed':parsed,'expectedPhonetic':pexp,'parsedPhonetic':pparsed,'durationSec':round(secs,3),'parseOk':parse_ok,'durationOk':duration_ok,'ok':ok}
            rows.append(row)
            if not ok:hard.append(row)
    summary={'version':3,'engine':a.engine,'voiceStart':a.start,'voiceCount':len(voices),'testCount':len(TESTS),'recordingChecks':len(rows),'hardFailures':len(hard),'status':'FAIL' if hard else 'PASS','hardFailureRows':hard,'rows':rows}
    Path(a.out).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('engine','voiceStart','voiceCount','recordingChecks','hardFailures','status')},ensure_ascii=False))
    if hard:raise SystemExit(2)
if __name__=='__main__':main()
