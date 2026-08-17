#!/usr/bin/env python3
import json,os,subprocess,sys,tarfile,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
ENGINE=os.environ.get('VOICEVOX_ENGINE_URL','http://127.0.0.1:50021').rstrip('/')
LEVEL=os.environ.get('JLPT','').upper().strip(); KEY=os.environ.get('SPEAKER_KEY','').strip(); NAME=os.environ.get('SPEAKER_NAME','').strip(); STYLE_ID=int(os.environ.get('STYLE_ID','0')); STYLE_NAME=os.environ.get('STYLE_NAME','').strip()
CAT=Path(os.environ.get('CATALOG','pronunciation-original-audio-catalog.json')); OUT=Path(os.environ.get('OUTPUT_DIR','pronunciation-voicevox-original-out'))
if LEVEL not in {'N1','N2','N3','N4','N5'} or not KEY or not NAME: raise SystemExit('Invalid environment')
def http_bytes(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=240) as r:return r.read()
def http_json(url,method='GET',body=None,headers=None): return json.loads(http_bytes(url,method,body,headers).decode('utf-8'))
def wait():
    last=None
    for _ in range(90):
        try:http_bytes(ENGINE+'/version');return
        except Exception as e:last=e;time.sleep(2)
    raise RuntimeError(last)
def verify():
    sp=next((s for s in http_json(ENGINE+'/speakers') if str(s.get('name','')).strip()==NAME),None)
    if not sp: raise RuntimeError('speaker missing')
    st=next((s for s in sp.get('styles') or [] if int(s.get('id',-1))==STYLE_ID),None)
    if not st: raise RuntimeError('style missing')
    actual=str(st.get('name','')).strip()
    if STYLE_NAME and actual!=STYLE_NAME: raise RuntimeError(f'style mismatch {STYLE_NAME}/{actual}')
    return actual
def synth(text):
    last=None
    for attempt in range(1,5):
        try:
            qs=urllib.parse.urlencode({'text':text,'speaker':STYLE_ID}); q=http_json(ENGINE+'/audio_query?'+qs,method='POST',body=b'')
            payload=json.dumps(q,ensure_ascii=False).encode('utf-8')
            return http_bytes(ENGINE+'/synthesis?'+urllib.parse.urlencode({'speaker':STYLE_ID}),method='POST',body=payload,headers={'Content-Type':'application/json'})
        except Exception as e:
            last=e
            if attempt<4:time.sleep(min(8,attempt*2))
    raise RuntimeError(last)
def wav_to_mp3(wav,out):
    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);tmp=Path(f.name)
    try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),'-ac','1','-ar','24000','-b:a','48k',str(out)],check=True)
    finally:tmp.unlink(missing_ok=True)
wait(); style=verify(); d=json.loads(CAT.read_text(encoding='utf-8')); rows=[(k,v) for k,v in (d.get('questions') or {}).items() if v.get('level')==LEVEL]
if not rows: raise RuntimeError('No rows')
OUT.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix=f'pron-vv-{KEY}-{LEVEL}-') as td:
    tmp=Path(td); files=[]
    for n,(qid,rec) in enumerate(rows,1):
        mp=tmp/f'{qid}.mp3'; wav_to_mp3(synth(str(rec['text'])),mp)
        if not mp.is_file() or mp.stat().st_size<500: raise RuntimeError(f'Invalid {qid}')
        files.append((qid,mp))
        if n%100==0 or n==len(rows):print(KEY,LEVEL,n,'/',len(rows),flush=True)
    asset=f'{KEY}-{LEVEL}.tar'; tar=OUT/asset
    with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
        for qid,p in files:
            x=tf.gettarinfo(str(p),arcname=f'{qid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
            with p.open('rb') as f:tf.addfile(x,f)
members={}
with tarfile.open(tar,'r:') as tf:
    for x in tf.getmembers():
        if x.isfile() and x.name.endswith('.mp3'):members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
if set(members)!={k for k,_ in rows}:raise RuntimeError('TAR coverage mismatch')
manifest={'version':1,'engine':'voicevox','speakerKey':KEY,'speaker':NAME,'style':style,'styleId':STYLE_ID,'credit':f'VOICEVOX:{NAME}','level':LEVEL,'count':len(members),'asset':asset,'members':members}
(OUT/f'{KEY}-{LEVEL}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',asset,len(members),tar.stat().st_size)
