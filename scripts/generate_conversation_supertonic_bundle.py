import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from supertonic import TTS

VOICE = os.environ.get('VOICE', '').strip()
CATALOG = Path(os.environ.get('CATALOG', 'conversation-audio-catalog.json'))
OUT_DIR = Path(os.environ.get('OUT_DIR', 'conversation-supertonic-out'))

if VOICE not in {'F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'}:
    raise SystemExit(f'Invalid VOICE: {VOICE!r}')
if not CATALOG.is_file():
    raise SystemExit(f'Catalog not found: {CATALOG}')

catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
lines = catalog.get('lines') or {}
if not (200 <= len(lines) <= 260):
    raise SystemExit(f'Unexpected utterance count: {len(lines)}')
label = (catalog.get('voices') or {}).get(VOICE, VOICE)

OUT_DIR.mkdir(parents=True, exist_ok=True)
tar_path = OUT_DIR / f'{VOICE}.tar'
manifest_path = OUT_DIR / f'{VOICE}.json'

# Supertonic 3 is CPU-native. One model instance is reused for the whole voice bundle.
tts = TTS(auto_download=True)
style = tts.get_voice_style(voice_name=VOICE)

with tempfile.TemporaryDirectory(prefix=f'supertonic-{VOICE}-') as td:
    tmp = Path(td)
    mp3_files = []
    for n, (uid, rec) in enumerate(lines.items(), 1):
        text = str(rec.get('text') or '').strip()
        if not text:
            raise SystemExit(f'Empty text for {uid}')
        wav, duration = tts.synthesize(
            text=text,
            voice_style=style,
            total_steps=8,
            speed=1.0,
            max_chunk_length=300,
            silence_duration=0.12,
            lang='ja',
            verbose=False,
        )
        wav_path = tmp / f'{uid}.wav'
        mp3_path = tmp / f'{uid}.mp3'
        tts.save_audio(wav, str(wav_path))
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-i',str(wav_path),'-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(mp3_path)
        ], check=True)
        if not mp3_path.is_file() or mp3_path.stat().st_size < 1000:
            raise SystemExit(f'Invalid MP3 for {uid}')
        wav_path.unlink(missing_ok=True)
        mp3_files.append((uid, mp3_path))
        if n % 25 == 0 or n == len(lines):
            print(f'{VOICE}: generated {n}/{len(lines)}')

    with tarfile.open(tar_path, 'w') as tf:
        for uid, path in mp3_files:
            info = tf.gettarinfo(str(path), arcname=f'{uid}.mp3')
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            with path.open('rb') as f:
                tf.addfile(info, f)

members = {}
with tarfile.open(tar_path, 'r:') as tf:
    for member in tf.getmembers():
        if not member.isfile() or not member.name.endswith('.mp3'):
            continue
        uid = Path(member.name).stem
        members[uid] = [int(member.offset_data), int(member.size)]

if set(members) != set(lines):
    missing = sorted(set(lines) - set(members))[:10]
    extra = sorted(set(members) - set(lines))[:10]
    raise SystemExit(f'TAR member mismatch missing={missing} extra={extra}')
if tar_path.stat().st_size < 100000:
    raise SystemExit('TAR unexpectedly small')

manifest = {
    'version': 1,
    'engine': 'supertonic-3',
    'voice': VOICE,
    'label': label,
    'language': 'ja',
    'sampleRate': 44100,
    'codec': 'mp3',
    'bitrateKbps': 96,
    'qualitySteps': 8,
    'synthesisSpeed': 1.0,
    'asset': tar_path.name,
    'count': len(members),
    'members': members,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
print(f'Built {tar_path} ({tar_path.stat().st_size:,} bytes), {len(members)} recordings')
