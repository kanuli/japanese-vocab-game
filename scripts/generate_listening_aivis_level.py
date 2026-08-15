#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,re,subprocess,tarfile,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
ENGINE=os.environ.get('AIVIS_ENGINE_URL','http://127.0.0.1:10101').rstrip('/');LEVEL=os.environ.get('LEVEL','').upper();CAT=Path(os.environ.get('CATALOG','listening-audio-catalog.json'));OUT=Path(os.environ.get('OUT_DIR','listening-aivis-out'));MAX_STYLES=int(os.environ.get('MAX_STYLES','4'))
if LEVEL not in {'N1','N2','N3','N4','N5'}:raise SystemExit('bad LEVEL')
def get(path):
 with urllib.request.urlopen(ENGINE+path,timeout=180) as r:return json.loads(r.read().decode())
def postj(path):
 with urllib.request.urlopen(urllib.request.Request(ENGINE+path,data=b'',method='POST'),timeout=240) as r:return json.loads(r.read().decode())
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
 try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(w),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(dest)],check=True)
 finally:w.unlink(missing_ok=True)
def model():
 models=get('/aivm_models');speakers=get('/speakers');defaults=[x for x in models.values() if x.get('is_default_model')]
 if not defaults:raise RuntimeError('No default AIVMX')
 m=defaults[0];man=m.get('manifest') or {};lic=str(man.get('license') or '');arch=str(man.get('model_architecture') or '')
 if not any(x in lic.lower() for x in ('acml','aivis common model license','cc0','creative commons zero','パブリックドメイン')):raise RuntimeError('License not allowed: '+re.sub(r'\s+',' ',lic)[:500])
 if 'Style-Bert-VITS2' not in arch:raise RuntimeError('Not Style-Bert-VITS2: '+arch)
 msp=(man.get('speakers') or [None])[0]
 if not msp:raise RuntimeError('No speaker metadata')
 name=str(msp.get('name') or '').strip();g=next((x for x in speakers if str(x.get('name') or '').strip()==name),None)
 if not g:raise RuntimeError('Speaker not in /speakers')
 styles=list(g.get('styles') or []);pref=('ノーマル','Normal','通常');styles.sort(key=lambda x:(0 if str(x.get('name') or '') in pref else 1,int(x.get('id',0))));styles=styles[:MAX_STYLES]
 return {'modelUuid':str(man.get('uuid') or ''),'modelName':str(man.get('name') or name),'modelVersion':str(man.get('version') or ''),'modelArchitecture':arch,'license':lic,'licenseSha256':hashlib.sha256(lic.encode()).hexdigest(),'speaker':name,'styles':[{'key':f'a{i:02d}','speaker':name,'style':str(x.get('name') or ''),'styleId':int(x['id'])} for i,x in enumerate(styles,1)]}
def main():
 d=json.loads(CAT.read_text(encoding='utf-8'));rows={k:v for k,v in d['questions'].items() if v['level']==LEVEL}
 if not rows:raise RuntimeError('No questions')
 info=model();OUT.mkdir(parents=True,exist_ok=True);(OUT/'aivis-model.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for st in info['styles']:
  k=st['key'];sid=st['styleId']
  with tempfile.TemporaryDirectory(prefix=f'aivis-listen-{k}-{LEVEL}-') as td:
   tmp=Path(td);files=[]
   for n,(qid,rec) in enumerate(rows.items(),1):
    dest=tmp/f'{qid}.mp3';mp3(synth(str(rec['text']),sid),dest);files.append((qid,dest))
    if n%100==0 or n==len(rows):print(k,LEVEL,n,'/',len(rows),flush=True)
   tar=OUT/f'{k}-{LEVEL}.tar'
   with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
    for qid,p in files:
     x=tf.gettarinfo(str(p),arcname=f'{qid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
     with p.open('rb') as f:tf.addfile(x,f)
  members={}
  with tarfile.open(tar,'r:') as tf:
   for x in tf.getmembers():
    if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
  if set(members)!=set(rows):raise RuntimeError(f'{k}-{LEVEL} coverage mismatch')
  m={'version':1,**st,'level':LEVEL,'modelName':info['modelName'],'modelVersion':info['modelVersion'],'modelArchitecture':info['modelArchitecture'],'license':info['license'],'licenseSha256':info['licenseSha256'],'count':len(members),'asset':tar.name,'members':members}
  (OUT/f'{k}-{LEVEL}.json').write_text(json.dumps(m,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
if __name__=='__main__':main()
