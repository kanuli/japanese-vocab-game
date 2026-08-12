#!/usr/bin/env python3
"""Generate one full-coverage VOICEVOX audio sprite for one speaker + JLPT level.

All questions in the selected level are synthesized with one canonical speaker style,
concatenated as PCM with a short silence gap, then encoded once as CBR MP3. The
manifest records start/end times for every question so browsers can seek within
one cross-origin media asset without JavaScript byte-range fetches.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

ENGINE=os.environ.get('VOICEVOX_ENGINE_URL','http://127.0.0.1:50021').rstrip('/')
LEVEL=os.environ.get('JLPT','').upper().strip()
SPEAKER_KEY=os.environ.get('SPEAKER_KEY','').strip()
SPEAKER_NAME=os.environ.get('SPEAKER_NAME','').strip()
STYLE_ID_RAW=os.environ.get('STYLE_ID','').strip()
STYLE_NAME=os.environ.get('STYLE_NAME','').strip()
OUTPUT_DIR=Path(os.environ.get('OUTPUT_DIR','voicevox-sprite-out'))
GAP_MS=int(os.environ.get('GAP_MS','180'))
FILES={
 'N5':'grammar_ja_N5_full_alphabetical_0001.json','N4':'grammar_ja_N4_full_alphabetical_0001.json',
 'N3':'grammar_ja_N3_full_alphabetical_0001.json','N2':'grammar_ja_N2_full_alphabetical_0001.json',
 'N1':'grammar_ja_N1_full_alphabetical_0001.json'}
HANABIRA_BASE='https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/'


def http_json(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=180) as r:return json.loads(r.read().decode('utf-8'))

def http_bytes(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    with urllib.request.urlopen(req,timeout=240) as r:return r.read()

def wait_engine():
    last=None
    for _ in range(90):
        try:http_bytes(f'{ENGINE}/version');return
        except Exception as exc:last=exc;time.sleep(2)
    raise RuntimeError(f'VOICEVOX Engine did not become ready: {last}')

def verify_voice():
    if not SPEAKER_KEY or not SPEAKER_NAME or not STYLE_ID_RAW:raise RuntimeError('Speaker identity is required')
    sid=int(STYLE_ID_RAW); speakers=http_json(f'{ENGINE}/speakers')
    sp=next((s for s in speakers if str(s.get('name','')).strip()==SPEAKER_NAME),None)
    if not sp:raise RuntimeError(f'Speaker not found: {SPEAKER_NAME}')
    st=next((x for x in sp.get('styles') or [] if int(x.get('id',-1))==sid),None)
    if not st:raise RuntimeError(f'Style {sid} not found for {SPEAKER_NAME}')
    actual=str(st.get('name','')).strip()
    if STYLE_NAME and actual!=STYLE_NAME:raise RuntimeError(f'Style mismatch: {STYLE_NAME} != {actual}')
    return sid,actual

def questions():
    if LEVEL not in FILES:raise RuntimeError(f'Invalid level: {LEVEL}')
    data=http_json(HANABIRA_BASE+FILES[LEVEL]); rows=[]
    for pi,p in enumerate(data):
        grammar=str(p.get('title','')).strip()
        for ei,e in enumerate(p.get('examples') or []):
            jp=str(e.get('jp','')).strip()
            if 5<=len(jp)<=95:rows.append({'id':f'{LEVEL}-{pi}-{ei}','text':jp,'grammar':grammar})
    return rows

def synth(text,sid):
    last=None
    for attempt in range(4):
        try:
            qs=urllib.parse.urlencode({'text':text,'speaker':sid})
            q=http_json(f'{ENGINE}/audio_query?{qs}',method='POST',body=b'')
            payload=json.dumps(q,ensure_ascii=False).encode('utf-8')
            return http_bytes(f"{ENGINE}/synthesis?{urllib.parse.urlencode({'speaker':sid})}",method='POST',body=payload,headers={'Content-Type':'application/json'})
        except Exception as exc:
            last=exc
            if attempt<3:time.sleep(2*(attempt+1))
    raise RuntimeError(f'Synthesis failed: {last}')

def probe_mp3(path):
    out=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True).strip()
    return float(out)

def main():
    wait_engine(); sid,style=verify_voice(); rows=questions()
    if not rows:raise RuntimeError('No questions')
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    wav_path=OUTPUT_DIR/f'{SPEAKER_KEY}-{LEVEL}.wav'
    mp3_path=OUTPUT_DIR/f'{SPEAKER_KEY}-{LEVEL}.mp3'
    manifest_path=OUTPUT_DIR/f'{SPEAKER_KEY}-{LEVEL}.json'
    sample_rate=None; channels=None; sampwidth=None; cursor_frames=0; timings={}
    gap_frames=None
    print(f'Building sprite: {SPEAKER_NAME}/{style} {LEVEL} {len(rows)} questions')
    with wave.open(str(wav_path),'wb') as outwav:
        for i,q in enumerate(rows,1):
            raw=synth(q['text'],sid)
            with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp:
                tmp.write(raw); tmp_path=Path(tmp.name)
            try:
                with wave.open(str(tmp_path),'rb') as w:
                    if w.getcomptype()!='NONE':raise RuntimeError('VOICEVOX WAV is unexpectedly compressed')
                    params=(w.getnchannels(),w.getsampwidth(),w.getframerate())
                    if sample_rate is None:
                        channels,sampwidth,sample_rate=params
                        outwav.setnchannels(channels);outwav.setsampwidth(sampwidth);outwav.setframerate(sample_rate)
                        gap_frames=round(sample_rate*GAP_MS/1000)
                    elif params!=(channels,sampwidth,sample_rate):raise RuntimeError(f'WAV format changed: {params}')
                    frames=w.readframes(w.getnframes()); n=w.getnframes()
                    start=cursor_frames/sample_rate
                    outwav.writeframesraw(frames);cursor_frames+=n
                    end=cursor_frames/sample_rate
                    timings[q['id']]={'text':q['text'],'grammar':q['grammar'],'start':round(start,4),'end':round(end,4),'duration':round(end-start,4)}
                    if gap_frames:
                        outwav.writeframesraw(b'\x00'*(gap_frames*channels*sampwidth));cursor_frames+=gap_frames
            finally:tmp_path.unlink(missing_ok=True)
            if i%25==0 or i==len(rows):print(f'[{i}/{len(rows)}] {q["id"]}')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(wav_path),'-ac','1','-ar','24000','-codec:a','libmp3lame','-b:a','48k','-write_xing','1',str(mp3_path)],check=True)
    wav_path.unlink(missing_ok=True)
    encoded_duration=probe_mp3(mp3_path); expected=cursor_frames/sample_rate
    if abs(encoded_duration-expected)>0.25:raise RuntimeError(f'Encoded sprite duration drift too large: {encoded_duration} vs {expected}')
    manifest={'version':2,'format':'audio-sprite-mp3','speakerKey':SPEAKER_KEY,'speaker':SPEAKER_NAME,'style':style,'styleId':sid,'credit':f'VOICEVOX:{SPEAKER_NAME}','level':LEVEL,'count':len(rows),'asset':mp3_path.name,'gapMs':GAP_MS,'duration':round(encoded_duration,4),'questions':timings}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'Done {mp3_path.name}: {mp3_path.stat().st_size} bytes, {encoded_duration:.2f}s')
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (RuntimeError,urllib.error.URLError,subprocess.CalledProcessError,ValueError,wave.Error) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);raise SystemExit(1)
