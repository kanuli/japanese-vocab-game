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
def synth(base,text,sid):
    q=urllib.parse.urlencode({'text':text+'。','speaker':sid})
    aq=req_json(f'{base}/audio_query?{q}',method='POST',body=b'')
    body=json.dumps(aq,ensure_ascii=False).encode('utf-8')
    return req_bytes(f"{base}/synthesis?{urllib.parse.urlencode({'speaker':sid})}",method='POST',body=body,headers={'Content-Type':'application/json'})
def norm(s):
    return re.sub(r'[^ぁ-んァ-ン一-龯ー]','',s or '')
def lev(a,b):
    if len(a)<len(b):a,b=b,a
    prev=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        cur=[i]
        for j,cb in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ca!=cb)))
        prev=cur
    return prev[-1]
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
    ap=argparse.ArgumentParser();ap.add_argument('--engine',choices=['voicevox','aivis'],required=True);ap.add_argument('--base',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    from faster_whisper import WhisperModel
    model=WhisperModel('small',device='cpu',compute_type='int8')
    voices=canonical_voicevox(a.base) if a.engine=='voicevox' else all_aivis(a.base)
    if not voices:raise SystemExit('no voices')
    rows=[];hard_fail=[]
    for v in voices:
        for text,expected in TESTS:
            wav=synth(a.base,text,int(v['id']))
            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);p=Path(f.name)
            try:
                segs,_=model.transcribe(str(p),language='ja',beam_size=5,vad_filter=False,condition_on_previous_text=False)
                heard=''.join(x.text for x in segs).strip();nheard=norm(heard);nexp=norm(expected);d=lev(nheard,nexp)
                dropped=len(nheard)<=max(1,len(nexp)-2) or (len(nexp)>=3 and nexp[-2:] not in nheard)
                known=text in {'ごみばこ','あんさつ'}
                ok=(d<=1 and not dropped)
                rows.append({'engine':a.engine,**v,'text':text,'expected':expected,'heard':heard,'distance':d,'droppedEnding':dropped,'ok':ok})
                if known and not ok:hard_fail.append(rows[-1])
            finally:p.unlink(missing_ok=True)
    summary={'engine':a.engine,'voiceCount':len(voices),'testCount':len(TESTS),'recordingChecks':len(rows),'hardFailures':len(hard_fail),'failedChecks':sum(not r['ok'] for r in rows),'status':'FAIL' if hard_fail else 'PASS','hardFailureRows':hard_fail,'rows':rows}
    Path(a.out).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('engine','voiceCount','recordingChecks','hardFailures','failedChecks','status')},ensure_ascii=False))
    if hard_fail:raise SystemExit(2)
if __name__=='__main__':main()
