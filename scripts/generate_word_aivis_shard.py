#!/usr/bin/env python3
from __future__ import annotations
import json,os,subprocess,tarfile,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
ENGINE=os.environ.get('AIVIS_ENGINE_URL','http://127.0.0.1:10101').rstrip('/');SHARD=int(os.environ.get('SHARD','-1'));CAT=Path(os.environ.get('CATALOG','word-shared-audio-catalog.json'));MODEL=Path(os.environ.get('MODEL','aivis-model.json'));OUT=Path(os.environ.get('OUT_DIR','word-aivis-out'))
def get(path):
 with urllib.request.urlopen(ENGINE+path,timeout=180) as r:return json.loads(r.read().decode('utf-8'))
def postj(path):
 with urllib.request.urlopen(urllib.request.Request(ENGINE+path,data=b'',method='POST'),timeout=240) as r:return json.loads(r.read().decode('utf-8'))
def postb(path,obj):
 body=json.dumps(obj,ensure_ascii=False).encode();req=urllib.request.Request(ENGINE+path,data=body,method='POST',headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=300) as r:return r.read()
def synth(text,sid):
 q=urllib.parse.urlencode({'text':text,'speaker':sid});last=None
 for n in range(4):
  try:return postb('/synthesis?'+urllib.parse.urlencode({'speaker':sid}),postj('/audio_query?'+q))
  except Exception as e:last=e;time.sleep(2*(n+1))
 raise RuntimeError(last)
def mp3(wav,dest):
 with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);w=Path(f.name)
 try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(w),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','64k',str(dest)],check=True)
 finally:w.unlink(missing_ok=True)
def validate_model(expected):
 current=get('/aivm_models');defaults=[x for x in current.values() if x.get('is_default_model')]
 if not defaults:raise RuntimeError('No default AIVMX')
 man=defaults[0].get('manifest') or {}
 if str(man.get('uuid') or '')!=expected['modelUuid'] or str(man.get('version') or '')!=expected['modelVersion']:raise RuntimeError('AIVMX identity changed')
 speakers=get('/speakers');g=next((x for x in speakers if str(x.get('name') or '').strip()==expected['speaker']),None)
 if not g:raise RuntimeError('Expected Aivis speaker missing')
 actual={int(x['id']):str(x.get('name') or '') for x in g.get('styles') or []}
 for st in expected['styles']:
  if actual.get(int(st['styleId']))!=st['style']:raise RuntimeError('Aivis style changed: '+str(st))
def main():
 d=json.loads(CAT.read_text(encoding='utf-8'));sc=int(d['shardCount'])
 if SHARD not in range(sc):raise RuntimeError('Bad shard')
 rows=[x for x in d['items'] if int(x['shard'])==SHARD]
 model=json.loads(MODEL.read_text(encoding='utf-8'));validate_model(model);OUT.mkdir(parents=True,exist_ok=True)
 for st in model['styles']:
  key=st['key'];sid=int(st['styleId'])
  with tempfile.TemporaryDirectory(prefix=f'word-aivis-{key}-{SHARD}-') as td:
   tmp=Path(td);files=[]
   for n,w in enumerate(rows,1):
    dest=tmp/f"{w['id']}.mp3";mp3(synth(str(w['reading']),sid),dest);files.append((w['id'],dest))
    if n%100==0 or n==len(rows):print(key,SHARD,n,'/',len(rows),flush=True)
   tar=OUT/f'{key}-shard{SHARD}.tar'
   with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
    for wid,p in files:
     x=tf.gettarinfo(str(p),arcname=f'{wid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
     with p.open('rb') as f:tf.addfile(x,f)
  members={}
  with tarfile.open(tar,'r:') as tf:
   for x in tf.getmembers():
    if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
  if set(members)!={x['id'] for x in rows}:raise RuntimeError(f'{key} shard coverage mismatch')
  manifest={'version':1,**st,'shard':SHARD,'modelName':model['modelName'],'modelVersion':model['modelVersion'],'modelArchitecture':model['modelArchitecture'],'license':model['license'],'licenseSha256':model['licenseSha256'],'count':len(members),'asset':tar.name,'members':members}
  (OUT/f'{key}-shard{SHARD}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
  print('Built',tar,tar.stat().st_size,'bytes',flush=True)
if __name__=='__main__':main()
