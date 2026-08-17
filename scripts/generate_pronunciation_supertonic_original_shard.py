#!/usr/bin/env python3
import json,os,re,subprocess,tarfile,tempfile
from pathlib import Path
import numpy as np
from supertonic import TTS
VOICE=os.environ.get('VOICE','').strip(); LEVEL=os.environ.get('LEVEL','').strip().upper()
SHARD_COUNT=max(1,int(os.environ.get('SHARD_COUNT','2'))); SHARD_INDEX=int(os.environ.get('SHARD_INDEX','0'))
CATALOG=Path(os.environ.get('CATALOG','pronunciation-original-audio-catalog.json')); OUT=Path(os.environ.get('OUT_DIR','pronunciation-supertonic-original-out'))
VOICES={'F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'}; LEVELS={'N1','N2','N3','N4','N5'}
if VOICE not in VOICES or LEVEL not in LEVELS: raise SystemExit('Invalid voice/level')
if not 0<=SHARD_INDEX<SHARD_COUNT: raise SystemExit('Invalid shard')
d=json.loads(CATALOG.read_text(encoding='utf-8'))
all_rows=[(k,v) for k,v in (d.get('questions') or {}).items() if str(v.get('level','')).upper()==LEVEL]
rows=all_rows[SHARD_INDEX::SHARD_COUNT]
if not rows: raise SystemExit(f'No rows for {VOICE}/{LEVEL}/p{SHARD_INDEX}')
OUT.mkdir(parents=True,exist_ok=True); tts=TTS(auto_download=True); style=tts.get_voice_style(voice_name=VOICE); sr=int(getattr(tts,'sample_rate',44100) or 44100)
SPEEDS=(1.0,1.01,.99,1.02,.98,1.05,.95)
def synth(text,speed):
    return tts.synthesize(text=text,voice_style=style,total_steps=8,speed=speed,max_chunk_length=300,silence_duration=.12,lang='ja',verbose=False)
def clauses(text):
    p=[x.strip() for x in re.findall(r'.+?(?:[。！？!?]|$)',text) if x.strip()]
    if len(p)>1:return p
    p=[x.strip() for x in re.findall(r'.+?(?:[、，,；;：:]|$)',text) if x.strip()]
    if len(p)>1:return p
    if len(text)>=12:
        m=len(text)//2; return [text[:m].strip(),text[m:].strip()]
    return [text]
def resilient(qid,text):
    errs=[]
    for speed in SPEEDS:
        try:
            wav,dur=synth(text,speed)
            return wav,dur,{'mode':'direct','speed':speed}
        except Exception as e:
            errs.append(f'{type(e).__name__}: {e}'); print(VOICE,LEVEL,qid,'retry speed',speed,type(e).__name__,flush=True)
    parts=[x for x in clauses(text) if x]
    if len(parts)<=1: raise RuntimeError(str(errs[-3:]))
    rendered=[]; used=[]
    for part in parts:
        ok=False
        for speed in SPEEDS:
            try:
                wav,_=synth(part,speed); a=np.asarray(wav,dtype=np.float32)
                if a.ndim==1:a=a.reshape(1,-1)
                rendered.append(a);used.append(speed);ok=True;break
            except Exception: pass
        if not ok: raise RuntimeError('clause fallback failed')
    silence=np.zeros((1,max(1,int(sr*.12))),dtype=np.float32); joined=[]
    for i,a in enumerate(rendered):
        joined.append(a)
        if i+1<len(rendered):joined.append(silence)
    combo=np.concatenate(joined,axis=1); dur=np.asarray([combo.shape[-1]/sr],dtype=np.float32)
    return combo,dur,{'mode':'clauses','pieces':len(parts),'speeds':used}
asset=f'{VOICE}-{LEVEL}-p{SHARD_INDEX}.tar'; tar_path=OUT/asset; fallbacks={}
with tempfile.TemporaryDirectory(prefix=f'pron-{VOICE}-{LEVEL}-p{SHARD_INDEX}-') as td:
    tmp=Path(td); files=[]
    for n,(qid,rec) in enumerate(rows,1):
        text=str(rec.get('text') or '').strip()
        wav,_dur,recovery=resilient(qid,text)
        if recovery.get('mode')!='direct' or float(recovery.get('speed',1))!=1: fallbacks[qid]={'text':text,**recovery}
        wp=tmp/f'{qid}.wav'; mp=tmp/f'{qid}.mp3'; tts.save_audio(wav,str(wp))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wp),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(mp)],check=True)
        wp.unlink(missing_ok=True)
        if not mp.is_file() or mp.stat().st_size<1000: raise RuntimeError(f'Invalid MP3 {qid}')
        files.append((qid,mp))
        if n%50==0 or n==len(rows): print(VOICE,LEVEL,f'p{SHARD_INDEX}',n,'/',len(rows),flush=True)
    with tarfile.open(tar_path,'w',format=tarfile.USTAR_FORMAT) as tf:
        for qid,p in files:
            x=tf.gettarinfo(str(p),arcname=f'{qid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
            with p.open('rb') as f:tf.addfile(x,f)
members={}
with tarfile.open(tar_path,'r:') as tf:
    for x in tf.getmembers():
        if x.isfile() and x.name.endswith('.mp3'): members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
expected={k for k,_ in rows}
if set(members)!=expected: raise RuntimeError('TAR coverage mismatch')
manifest={'version':1,'engine':'supertonic-3','voice':VOICE,'level':LEVEL,'shardIndex':SHARD_INDEX,'shardCount':SHARD_COUNT,'count':len(members),'asset':asset,'fallbackCount':len(fallbacks),'fallbacks':fallbacks,'members':members}
(OUT/f'{VOICE}-{LEVEL}-p{SHARD_INDEX}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',asset,len(members),'fallbacks',len(fallbacks),tar_path.stat().st_size)
