#!/usr/bin/env python3
"""Generate one VOICEVOX speaker bundle for only the missing vocabulary delta."""
from __future__ import annotations
import json,os,subprocess,sys,tarfile,tempfile,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ENGINE=os.environ.get('VOICEVOX_ENGINE_URL','http://127.0.0.1:50021').rstrip('/')
CATALOG=Path(os.environ.get('CATALOG','word-audio-delta-catalog.json'))
SPEAKER_KEY=os.environ.get('SPEAKER_KEY','').strip();SPEAKER_NAME=os.environ.get('SPEAKER_NAME','').strip();STYLE_ID_RAW=os.environ.get('STYLE_ID','').strip();STYLE_NAME=os.environ.get('STYLE_NAME','').strip();OUT=Path(os.environ.get('OUTPUT_DIR','word-voicevox-delta-out'))
def j(url,method='GET',body=None,headers=None):
 req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
 with urllib.request.urlopen(req,timeout=240) as r:return json.loads(r.read().decode())
def b(url,method='GET',body=None,headers=None):
 req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
 with urllib.request.urlopen(req,timeout=300) as r:return r.read()
def wait():
 last=None
 for _ in range(120):
  try:b(ENGINE+'/version');return
  except Exception as e:last=e;time.sleep(2)
 raise RuntimeError(last)
def verify():
 if not SPEAKER_KEY or not SPEAKER_NAME or not STYLE_ID_RAW:raise RuntimeError('speaker identity required')
 sid=int(STYLE_ID_RAW);sp=next((x for x in j(ENGINE+'/speakers') if str(x.get('name','')).strip()==SPEAKER_NAME),None)
 if not sp:raise RuntimeError('speaker missing '+SPEAKER_NAME)
 st=next((x for x in sp.get('styles') or [] if int(x.get('id',-1))==sid),None)
 if not st:raise RuntimeError('style missing')
 actual=str(st.get('name','')).strip()
 if STYLE_NAME and actual!=STYLE_NAME:raise RuntimeError(f'style mismatch {STYLE_NAME} != {actual}')
 return sid,actual
def synth(text,sid):
 last=None
 for n in range(4):
  try:
   qs=urllib.parse.urlencode({'text':text,'speaker':sid});q=j(ENGINE+'/audio_query?'+qs,'POST',b'');payload=json.dumps(q,ensure_ascii=False).encode()
   return b(ENGINE+'/synthesis?'+urllib.parse.urlencode({'speaker':sid}),'POST',payload,{'Content-Type':'application/json'})
  except Exception as e:last=e;time.sleep(2*(n+1))
 raise RuntimeError(last)
def mp3(wav,dest):
 with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);p=Path(f.name)
 try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(p),'-ac','1','-ar','24000','-b:a','48k',str(dest)],check=True)
 finally:p.unlink(missing_ok=True)
def main():
 wait();sid,style=verify();d=json.loads(CATALOG.read_text(encoding='utf-8'));rows=d.get('items') or []
 if int(d.get('wordCount',-1))!=len(rows) or not rows:raise RuntimeError('empty/bad delta catalog')
 OUT.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix=f'vv-delta-{SPEAKER_KEY}-') as td:
  tmp=Path(td);files=[]
  for n,w in enumerate(rows,1):
   p=tmp/f"{w['id']}.mp3";mp3(synth(str(w['reading']),sid),p);files.append((str(w['id']),p))
   if n%100==0 or n==len(rows):print(SPEAKER_KEY,n,'/',len(rows),flush=True)
  tar=OUT/f'{SPEAKER_KEY}-delta.tar'
  with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
   for wid,p in files:
    x=tf.gettarinfo(str(p),arcname=f'{wid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
    with p.open('rb') as f:tf.addfile(x,f)
 members={}
 with tarfile.open(tar,'r:') as tf:
  for x in tf.getmembers():
   if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
 expected={str(x['id']) for x in rows}
 if set(members)!=expected:raise RuntimeError('delta TAR coverage mismatch')
 man={'version':1,'engine':'voicevox','speakerKey':SPEAKER_KEY,'speaker':SPEAKER_NAME,'style':style,'styleId':sid,'credit':f'VOICEVOX:{SPEAKER_NAME}','shard':0,'count':len(rows),'asset':tar.name,'members':members}
 (OUT/f'{SPEAKER_KEY}-delta.json').write_text(json.dumps(man,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 print('Built',tar,len(rows),'missing words')
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERROR:',e,file=sys.stderr);raise
