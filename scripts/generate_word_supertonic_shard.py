#!/usr/bin/env python3
import json,os,subprocess,tarfile,tempfile
from pathlib import Path
from supertonic import TTS
VOICE=os.environ.get('VOICE','').strip();SHARD=int(os.environ.get('SHARD','-1'));CAT=Path(os.environ.get('CATALOG','word-shared-audio-catalog.json'));OUT=Path(os.environ.get('OUT_DIR','word-supertonic-out'))
VALID={'F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'}
if VOICE not in VALID:raise SystemExit('bad VOICE')
d=json.loads(CAT.read_text(encoding='utf-8'));sc=int(d.get('shardCount',0))
if SHARD not in range(sc):raise SystemExit('bad SHARD')
rows=[x for x in d.get('items',[]) if int(x['shard'])==SHARD]
if not rows:raise SystemExit('empty shard')
OUT.mkdir(parents=True,exist_ok=True);tts=TTS(auto_download=True);style=tts.get_voice_style(voice_name=VOICE)
with tempfile.TemporaryDirectory(prefix=f'word-st3-{VOICE}-{SHARD}-') as td:
 tmp=Path(td);files=[]
 for n,w in enumerate(rows,1):
  wav,_=tts.synthesize(text=str(w['reading']),voice_style=style,total_steps=8,speed=1.0,max_chunk_length=100,silence_duration=.08,lang='ja',verbose=False)
  wp=tmp/f"{w['id']}.wav";mp=tmp/f"{w['id']}.mp3";tts.save_audio(wav,str(wp));subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wp),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','64k',str(mp)],check=True);wp.unlink(missing_ok=True);files.append((w['id'],mp))
  if n%100==0 or n==len(rows):print(VOICE,SHARD,n,'/',len(rows),flush=True)
 tar=OUT/f'{VOICE}-shard{SHARD}.tar'
 with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as tf:
  for wid,p in files:
   x=tf.gettarinfo(str(p),arcname=f'{wid}.mp3');x.mtime=0;x.uid=x.gid=0;x.uname=x.gname=''
   with p.open('rb') as f:tf.addfile(x,f)
members={}
with tarfile.open(tar,'r:') as tf:
 for x in tf.getmembers():
  if x.isfile():members[Path(x.name).stem]=[int(x.offset_data),int(x.size)]
expected={x['id'] for x in rows}
if set(members)!=expected:raise SystemExit('TAR coverage mismatch')
manifest={'version':1,'engine':'supertonic-3','voice':VOICE,'shard':SHARD,'count':len(rows),'asset':tar.name,'members':members}
(OUT/f'{VOICE}-shard{SHARD}.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',tar,tar.stat().st_size,'bytes')
