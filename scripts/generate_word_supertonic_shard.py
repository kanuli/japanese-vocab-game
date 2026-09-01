#!/usr/bin/env python3
import hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
from supertonic import TTS

VOICE=os.environ.get('VOICE','').strip()
SHARD=int(os.environ.get('SHARD','-1'))
CAT=Path(os.environ.get('CATALOG','word-shared-audio-catalog.json'))
OUT=Path(os.environ.get('OUT_DIR','word-supertonic-out'))
VALID={'F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'}
if VOICE not in VALID: raise SystemExit('bad VOICE')

def env_int(name,default):
    try:return int(os.environ.get(name,str(default)))
    except Exception:return int(default)
def env_float(name,default):
    try:return float(os.environ.get(name,str(default)))
    except Exception:return float(default)
def env_bool(name,default):
    raw=str(os.environ.get(name,'1' if default else '0')).strip().lower()
    return raw not in {'0','false','no','off'}

# Learning production defaults: every voice gets the same high-quality treatment.
STEPS=env_int('TOTAL_STEPS',16)
SPEED=env_float('SPEED',0.95)
ADD_STOP=env_bool('ADD_TERMINAL_PUNCT',True)
BITRATE=os.environ.get('MP3_BITRATE','96k').strip() or '96k'
MANIFEST_VERSION=env_int('MANIFEST_VERSION',3)
QA_SAMPLE_COUNT=max(0,env_int('QA_SAMPLE_COUNT',12))
QA_DIR=Path(os.environ['QA_SAMPLE_DIR']) if os.environ.get('QA_SAMPLE_DIR') else None

# Known regressions must always be included in QA when their shard is generated.
KNOWN_REGRESSIONS={'あんさつ','ごみばこ'}

d=json.loads(CAT.read_text(encoding='utf-8'));sc=int(d.get('shardCount',0))
if SHARD not in range(sc): raise SystemExit('bad SHARD')
rows=[x for x in d.get('items',[]) if int(x['shard'])==SHARD]
if not rows: raise SystemExit('empty shard')

# Deterministic per-shard pronunciation sample: short/medium words are the most
# vulnerable to neural-TTS ending drops, so sample them more heavily.
def qa_rank(w):
    r=str(w.get('reading','')).strip()
    short_penalty=0 if 2<=len(r)<=10 else 1
    h=hashlib.sha256((VOICE+'|'+str(w['id'])+'|pron-qa-v3').encode()).hexdigest()
    return (short_penalty,h)
qa_ids={w['id'] for w in sorted(rows,key=qa_rank)[:QA_SAMPLE_COUNT]}
qa_ids|={w['id'] for w in rows if str(w.get('reading','')).strip() in KNOWN_REGRESSIONS}

OUT.mkdir(parents=True,exist_ok=True)
if QA_DIR: QA_DIR.mkdir(parents=True,exist_ok=True)
tts=TTS(auto_download=True);style=tts.get_voice_style(voice_name=VOICE)
qa_rows=[]

with tempfile.TemporaryDirectory(prefix=f'word-st3-{VOICE}-{SHARD}-') as td:
    tmp=Path(td);files=[]
    for n,w in enumerate(rows,1):
        reading=str(w['reading']).strip()
        if not reading: raise RuntimeError(f'Empty reading for {w["id"]}')
        text=reading
        if ADD_STOP and text[-1] not in '。！？!?': text+='。'
        wav,_=tts.synthesize(
            text=text,voice_style=style,total_steps=STEPS,speed=SPEED,
            max_chunk_length=100,silence_duration=.10,lang='ja',verbose=False
        )
        wp=tmp/f"{w['id']}.wav";mp=tmp/f"{w['id']}.mp3"
        tts.save_audio(wav,str(wp))
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wp),
            '-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a',BITRATE,str(mp)
        ],check=True)
        wp.unlink(missing_ok=True)
        if not mp.is_file() or mp.stat().st_size<1500:
            raise RuntimeError(f'Invalid MP3 {w["id"]}')
        files.append((w['id'],mp))
        if QA_DIR and w['id'] in qa_ids:
            qname=f'{VOICE}-s{SHARD}-{w["id"]}.mp3'
            shutil.copy2(mp,QA_DIR/qname)
            qa_rows.append({
                'voice':VOICE,'shard':SHARD,'id':w['id'],'reading':reading,
                'written':str(w.get('written','')),'file':qname,
                'knownRegression':reading in KNOWN_REGRESSIONS
            })
        if n%100==0 or n==len(rows):
            print(VOICE,SHARD,n,'/',len(rows),'steps',STEPS,'speed',SPEED,flush=True)

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
if set(members)!=expected: raise SystemExit('TAR coverage mismatch')

manifest={
    'version':MANIFEST_VERSION,'engine':'supertonic-3','voice':VOICE,'shard':SHARD,
    'count':len(rows),'asset':tar.name,'members':members,
    'synthesis':{'steps':STEPS,'speed':SPEED,'terminalPunctuation':ADD_STOP,'bitrate':BITRATE},
    'pronunciationQaSampleCount':len(qa_rows)
}
(OUT/f'{VOICE}-shard{SHARD}.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
if QA_DIR:
    (QA_DIR/f'{VOICE}-s{SHARD}.json').write_text(json.dumps(qa_rows,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
print('Built',tar,tar.stat().st_size,'bytes; QA samples',len(qa_rows))
