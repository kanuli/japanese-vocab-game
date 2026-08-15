#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, tarfile, tempfile, time, urllib.parse, urllib.request
from pathlib import Path
ENGINE=os.environ.get('AIVIS_ENGINE_URL','http://127.0.0.1:10101').rstrip('/')
CATALOG=Path(os.environ.get('CATALOG','conversation-audio-catalog.json'))
OUT=Path(os.environ.get('OUTPUT_DIR','conversation-aivis-out')); MAX_STYLES=int(os.environ.get('MAX_STYLES','4'))

def jget(path):
    with urllib.request.urlopen(ENGINE+path,timeout=180) as r:return json.loads(r.read().decode('utf-8'))
def post_json(path):
    req=urllib.request.Request(ENGINE+path,data=b'',method='POST')
    with urllib.request.urlopen(req,timeout=240) as r:return json.loads(r.read().decode('utf-8'))
def post_bytes(path,obj):
    b=json.dumps(obj,ensure_ascii=False).encode('utf-8');req=urllib.request.Request(ENGINE+path,data=b,method='POST',headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=300) as r:return r.read()
def synth(text,sid):
    q=urllib.parse.urlencode({'text':text,'speaker':sid});last=None
    for attempt in range(4):
        try:
            query=post_json('/audio_query?'+q)
            # Keep the engine-produced AudioQuery intact; Aivis documents semantic differences from VOICEVOX.
            return post_bytes('/synthesis?'+urllib.parse.urlencode({'speaker':sid}),query)
        except Exception as e:
            last=e;time.sleep(2*(attempt+1))
    raise RuntimeError(f'Aivis synthesis failed: {last}')
def to_mp3(wav,dest):
    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);tmp=Path(f.name)
    try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(dest)],check=True)
    finally:tmp.unlink(missing_ok=True)
def model_and_styles():
    models=jget('/aivm_models'); speakers=jget('/speakers')
    defaults=[x for x in models.values() if x.get('is_default_model')]
    if not defaults:raise RuntimeError('AivisSpeech exposes no default model')
    m=defaults[0];manifest=m.get('manifest') or {};lic=str(manifest.get('license') or '')
    accepted=('ACML','Aivis Common Model License','CC0','Creative Commons Zero','パブリックドメイン')
    if not any(x.lower() in lic.lower() for x in accepted):
        preview=re.sub(r'\s+',' ',lic)[:500]
        raise RuntimeError('Default Aivis model license did not pass the publish allowlist: '+preview)
    arch=str(manifest.get('model_architecture') or '')
    if 'Style-Bert-VITS2' not in arch:raise RuntimeError('Expected Style-Bert-VITS2 AIVMX model, got '+arch)
    ms=(manifest.get('speakers') or [])
    if not ms:raise RuntimeError('Default model manifest has no speakers')
    msp=ms[0];name=str(msp.get('name') or '').strip();global_sp=next((x for x in speakers if str(x.get('name') or '').strip()==name),None)
    if not global_sp:raise RuntimeError('Default model speaker missing from /speakers: '+name)
    styles=list(global_sp.get('styles') or []); preferred=['ノーマル','Normal','通常']
    styles.sort(key=lambda x:(0 if str(x.get('name','')) in preferred else 1,int(x.get('id',0))))
    styles=styles[:MAX_STYLES]
    if not styles:raise RuntimeError('No Aivis talk styles found')
    info={'modelUuid':str(manifest.get('uuid') or ''),'modelName':str(manifest.get('name') or name),'modelVersion':str(manifest.get('version') or ''),'modelArchitecture':arch,'license':lic,'licenseSha256':hashlib.sha256(lic.encode()).hexdigest(),'speaker':name,'styles':[]}
    for i,st in enumerate(styles,1):info['styles'].append({'key':f'a{i:02d}','speaker':name,'style':str(st.get('name') or ''),'styleId':int(st['id'])})
    return info

def main():
    cat=json.loads(CATALOG.read_text(encoding='utf-8'));lines=cat.get('lines') or {}
    if len(lines)!=1244 or int(cat.get('sourceLineCount',0))!=1300:raise RuntimeError('Conversation catalog mismatch')
    info=model_and_styles();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'aivis-model.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for style in info['styles']:
        key=style['key'];sid=style['styleId']
        with tempfile.TemporaryDirectory(prefix=f'aivis-{key}-') as td:
            d=Path(td);files=[]
            for n,(uid,rec) in enumerate(lines.items(),1):
                dest=d/f'{uid}.mp3';to_mp3(synth(str(rec['text']).strip(),sid),dest);files.append((uid,dest))
                if n%100==0 or n==len(lines):print(key,n,'/',len(lines),flush=True)
            tar=OUT/f'{key}.tar'
            with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
                for uid,p in files:
                    x=tf.gettarinfo(str(p),arcname=f'{uid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
                    with p.open('rb') as fh:tf.addfile(x,fh)
        members={}
        with tarfile.open(tar,'r:') as tf:
            for x in tf.getmembers():
                if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
        if set(members)!=set(lines):raise RuntimeError(f'{key}: TAR coverage mismatch')
        manifest={'version':1,**style,'modelName':info['modelName'],'modelVersion':info['modelVersion'],'modelArchitecture':info['modelArchitecture'],'license':info['license'],'licenseSha256':info['licenseSha256'],'count':len(members),'asset':tar.name,'members':members}
        (OUT/f'{key}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
        print('Built',key,tar.stat().st_size,'bytes',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR:',e,file=sys.stderr);raise
