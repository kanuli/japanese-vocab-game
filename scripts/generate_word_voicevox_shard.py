#!/usr/bin/env python3
"""Generate one vocabulary shard for one canonical VOICEVOX speaker/style."""
from __future__ import annotations
import json, os, subprocess, sys, tarfile, tempfile, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ENGINE=os.environ.get('VOICEVOX_ENGINE_URL','http://127.0.0.1:50021').rstrip('/')
CATALOG=Path(os.environ.get('CATALOG','word-voicevox-catalog.json'))
SHARD=int(os.environ.get('SHARD','-1'))
SPEAKER_KEY=os.environ.get('SPEAKER_KEY','').strip(); SPEAKER_NAME=os.environ.get('SPEAKER_NAME','').strip()
STYLE_ID_RAW=os.environ.get('STYLE_ID','').strip(); STYLE_NAME=os.environ.get('STYLE_NAME','').strip()
OUTPUT_DIR=Path(os.environ.get('OUTPUT_DIR','word-voicevox-out'))

def http_json(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=180) as r:return json.loads(r.read().decode('utf-8'))
def http_bytes(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=240) as r:return r.read()
def wait_engine():
    last=None
    for _ in range(120):
        try:http_bytes(f'{ENGINE}/version');return
        except Exception as e:last=e;time.sleep(2)
    raise RuntimeError(f'VOICEVOX Engine not ready: {last}')
def verify_voice():
    if not SPEAKER_KEY or not SPEAKER_NAME or not STYLE_ID_RAW:raise RuntimeError('speaker identity is required')
    sid=int(STYLE_ID_RAW); speakers=http_json(f'{ENGINE}/speakers')
    sp=next((x for x in speakers if str(x.get('name','')).strip()==SPEAKER_NAME),None)
    if not sp:raise RuntimeError(f'speaker not found: {SPEAKER_NAME}')
    style=next((x for x in sp.get('styles') or [] if int(x.get('id',-1))==sid),None)
    if not style:raise RuntimeError(f'style id {sid} missing for {SPEAKER_NAME}')
    actual=str(style.get('name','')).strip()
    if STYLE_NAME and actual!=STYLE_NAME:raise RuntimeError(f'style mismatch: {STYLE_NAME} != {actual}')
    return sid,actual
def synthesize(text,sid):
    last=None
    for attempt in range(1,5):
        try:
            qs=urllib.parse.urlencode({'text':text,'speaker':sid})
            query=http_json(f'{ENGINE}/audio_query?{qs}',method='POST',body=b'')
            payload=json.dumps(query,ensure_ascii=False).encode('utf-8')
            return http_bytes(f"{ENGINE}/synthesis?{urllib.parse.urlencode({'speaker':sid})}",method='POST',body=payload,headers={'Content-Type':'application/json'})
        except Exception as e:
            last=e
            if attempt<4:time.sleep(min(8,attempt*2))
    raise RuntimeError(f'synthesis failed: {last}')
def wav_to_mp3(wav,out):
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as f:f.write(wav);tmp=Path(f.name)
    try:subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp),'-ac','1','-ar','24000','-b:a','48k',str(out)],check=True)
    finally:tmp.unlink(missing_ok=True)
def build_tar(mp3_dir,ids,tar_path):
    tar_path.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(tar_path,'w',format=tarfile.USTAR_FORMAT) as tf:
        for wid in ids:
            src=mp3_dir/f'{wid}.mp3'
            if not src.is_file() or src.stat().st_size<400:raise RuntimeError(f'invalid MP3: {src}')
            info=tf.gettarinfo(str(src),arcname=f'{wid}.mp3');info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
            with src.open('rb') as fh:tf.addfile(info,fh)
    members={}
    with tarfile.open(tar_path,'r:') as tf:
        for m in tf.getmembers():
            if m.isfile() and m.name.endswith('.mp3'):members[Path(m.name).stem]=[int(m.offset_data),int(m.size)]
    if set(members)!=set(ids):raise RuntimeError('TAR members do not match IDs')
    return members

def catalog_rows(data):
    sc=int(data.get('shardCount') or 0)
    if SHARD not in range(sc):raise RuntimeError(f'invalid shard {SHARD} / {sc}')
    items=data.get('items')
    if isinstance(items, list) and items:
        rows=[w for w in items if int(w['shard'])==SHARD]
        return rows, sc, 'items'
    words=data.get('words')
    if isinstance(words, list):
        if data.get('version')!=1 or sc!=5:raise RuntimeError('unsupported lemma catalog')
        rows=[w for w in words if int(w['shard'])==SHARD]
        if len(rows)<4000:raise RuntimeError(f'shard unexpectedly small: {len(rows)}')
        return rows, sc, 'lemma'
    raise RuntimeError('catalog has neither items nor lemma words list')

def main():
    wait_engine();sid,style=verify_voice()
    data=json.loads(CATALOG.read_text(encoding='utf-8'))
    words,sc,kind=catalog_rows(data)
    if not words:raise RuntimeError(f'empty shard {SHARD} ({kind})')
    work=OUTPUT_DIR/'mp3';work.mkdir(parents=True,exist_ok=True)
    print(f'Generating {len(words)} vocabulary items for {SPEAKER_NAME}/{style}, shard {SHARD}')
    for i,w in enumerate(words,1):
        dest=work/f"{w['id']}.mp3"
        if not(dest.is_file() and dest.stat().st_size>=400):wav_to_mp3(synthesize(w['reading'],sid),dest)
        if i%100==0 or i==len(words):print(f'[{i}/{len(words)}] {w["reading"]}')
    asset=f'{SPEAKER_KEY}-shard{SHARD}.tar';tar_path=OUTPUT_DIR/asset;ids=[w['id'] for w in words]
    members=build_tar(work,ids,tar_path)
    manifest={'version':1,'speakerKey':SPEAKER_KEY,'speaker':SPEAKER_NAME,'style':style,'styleId':sid,'credit':f'VOICEVOX:{SPEAKER_NAME}','shard':SHARD,'count':len(words),'asset':asset,'members':members}
    mpath=OUTPUT_DIR/f'{SPEAKER_KEY}-shard{SHARD}.json';mpath.write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    for f in work.glob('*.mp3'):f.unlink(missing_ok=True)
    try:work.rmdir()
    except OSError:pass
    print('Bundle',tar_path,tar_path.stat().st_size,'bytes; manifest',mpath)
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (RuntimeError,urllib.error.URLError,subprocess.CalledProcessError,ValueError) as e:print('ERROR:',e,file=sys.stderr);raise SystemExit(1)
