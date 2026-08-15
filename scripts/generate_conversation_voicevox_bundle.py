#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, tarfile, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

ENGINE=os.environ.get('VOICEVOX_ENGINE_URL','http://127.0.0.1:50021').rstrip('/')
CATALOG=Path(os.environ.get('CATALOG','conversation-audio-catalog.json'))
SPEAKER_KEY=os.environ.get('SPEAKER_KEY','').strip(); SPEAKER_NAME=os.environ.get('SPEAKER_NAME','').strip()
STYLE_ID=int(os.environ.get('STYLE_ID','-1')); STYLE_NAME=os.environ.get('STYLE_NAME','').strip()
OUT=Path(os.environ.get('OUTPUT_DIR','conversation-voicevox-out'))

def req_json(url,method='GET',body=None,headers=None):
    with urllib.request.urlopen(urllib.request.Request(url,data=body,method=method,headers=headers or {}),timeout=180) as r:return json.loads(r.read().decode('utf-8'))
def req_bytes(url,method='GET',body=None,headers=None):
    with urllib.request.urlopen(urllib.request.Request(url,data=body,method=method,headers=headers or {}),timeout=240) as r:return r.read()
def wait():
    for i in range(120):
        try:req_bytes(f'{ENGINE}/version');return
        except Exception:
            if i==119:raise
            time.sleep(2)
def synth(text):
    q=urllib.parse.urlencode({'text':text,'speaker':STYLE_ID})
    query=req_json(f'{ENGINE}/audio_query?{q}',method='POST',body=b'')
    return req_bytes(f"{ENGINE}/synthesis?{urllib.parse.urlencode({'speaker':STYLE_ID})}",method='POST',body=json.dumps(query,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
def mp3(wav,dest):
    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);tmp=Path(f.name)
    try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),'-ac','1','-ar','24000','-codec:a','libmp3lame','-b:a','64k',str(dest)],check=True)
    finally:tmp.unlink(missing_ok=True)

def main():
    wait(); data=json.loads(CATALOG.read_text(encoding='utf-8')); lines=data.get('lines') or {}
    if len(lines)!=1244:raise RuntimeError(f'Expected 1244 utterances, got {len(lines)}')
    speakers=req_json(f'{ENGINE}/speakers');sp=next((x for x in speakers if str(x.get('name','')).strip()==SPEAKER_NAME),None)
    if not sp:raise RuntimeError('speaker missing')
    st=next((x for x in sp.get('styles') or [] if int(x.get('id',-1))==STYLE_ID),None)
    if not st:raise RuntimeError('style missing')
    actual=str(st.get('name','')).strip()
    if STYLE_NAME and actual!=STYLE_NAME:raise RuntimeError(f'style mismatch {STYLE_NAME} != {actual}')
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'vv-{SPEAKER_KEY}-') as td:
        d=Path(td); files=[]
        for i,(uid,rec) in enumerate(lines.items(),1):
            dest=d/f'{uid}.mp3';mp3(synth(str(rec['text']).strip()),dest);files.append((uid,dest))
            if i%100==0 or i==len(lines):print(SPEAKER_KEY,i,'/',len(lines))
        tar=OUT/f'{SPEAKER_KEY}.tar'
        with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
            for uid,p in files:
                info=tf.gettarinfo(str(p),arcname=f'{uid}.mp3');info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
                with p.open('rb') as f:tf.addfile(info,f)
    members={}
    with tarfile.open(tar,'r:') as tf:
        for m in tf.getmembers():
            if m.isfile():members[Path(m.name).stem]=[int(m.offset_data),int(m.size)]
    if set(members)!=set(lines):raise RuntimeError('TAR coverage mismatch')
    manifest={'version':1,'speakerKey':SPEAKER_KEY,'speaker':SPEAKER_NAME,'style':actual,'styleId':STYLE_ID,'credit':f'VOICEVOX:{SPEAKER_NAME}','count':len(members),'asset':tar.name,'members':members}
    (OUT/f'{SPEAKER_KEY}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Built',tar,tar.stat().st_size,'bytes')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR',e,file=sys.stderr);raise
