#!/usr/bin/env python3
import json, os, subprocess, tarfile, tempfile
from pathlib import Path
from supertonic import TTS
VOICE=os.environ.get('VOICE','').strip();LEVEL=os.environ.get('LEVEL','').strip().upper();CATALOG=Path(os.environ.get('CATALOG','listening-audio-catalog.json'));OUT=Path(os.environ.get('OUT_DIR','listening-supertonic-out'))
if VOICE not in {'F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'}:raise SystemExit('bad VOICE')
if LEVEL not in {'N1','N2','N3','N4','N5'}:raise SystemExit('bad LEVEL')
d=json.loads(CATALOG.read_text(encoding='utf-8'));rows={k:v for k,v in (d.get('questions') or {}).items() if str(v.get('level','')).upper()==LEVEL}
if not rows:raise SystemExit(f'No {LEVEL} questions')
OUT.mkdir(parents=True,exist_ok=True);tts=TTS(auto_download=True);style=tts.get_voice_style(voice_name=VOICE)
with tempfile.TemporaryDirectory(prefix=f'listen-{VOICE}-{LEVEL}-') as td:
 tmp=Path(td);files=[]
 for n,(qid,rec) in enumerate(rows.items(),1):
  wav,_=tts.synthesize(text=str(rec['text']),voice_style=style,total_steps=8,speed=1.0,max_chunk_length=300,silence_duration=.12,lang='ja',verbose=False)
  wp=tmp/f'{qid}.wav';mp=tmp/f'{qid}.mp3';tts.save_audio(wav,str(wp));subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wp),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(mp)],check=True);wp.unlink(missing_ok=True);files.append((qid,mp))
  if n%100==0 or n==len(rows):print(VOICE,LEVEL,n,'/',len(rows),flush=True)
 tar=OUT/f'{VOICE}-{LEVEL}.tar'
 with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
  for qid,p in files:
   x=tf.gettarinfo(str(p),arcname=f'{qid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
   with p.open('rb') as f:tf.addfile(x,f)
members={}
with tarfile.open(tar,'r:') as tf:
 for x in tf.getmembers():
  if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
if set(members)!=set(rows):raise SystemExit('TAR coverage mismatch')
manifest={'version':1,'engine':'supertonic-3','voice':VOICE,'level':LEVEL,'count':len(members),'asset':tar.name,'members':members}
(OUT/f'{VOICE}-{LEVEL}.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',tar,tar.stat().st_size,'bytes')
