import json
import os
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

import numpy as np
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
if len(lines) < 2600:
    raise SystemExit(f'Expected expanded conversation catalog with at least 2600 utterances, got {len(lines)}')
label = (catalog.get('voices') or {}).get(VOICE, VOICE)

OUT_DIR.mkdir(parents=True, exist_ok=True)
tar_path = OUT_DIR / f'{VOICE}.tar'
manifest_path = OUT_DIR / f'{VOICE}.json'

# One Supertonic 3 model instance is reused for the complete expanded catalog.
tts = TTS(auto_download=True)
style = tts.get_voice_style(voice_name=VOICE)
sample_rate = int(getattr(tts, 'sample_rate', 44100) or 44100)

# Supertonic can occasionally predict a duration that lands exactly on a frame
# boundary, producing a one-frame latent/mask mismatch. A tiny speed adjustment
# changes the duration quantisation without changing the wording. If all direct
# retries fail, synthesize shorter punctuation-delimited clauses and concatenate
# them with a short pause. No dialogue text is dropped or substituted.
DIRECT_SPEEDS = (1.0, 1.01, 0.99, 1.02, 0.98, 1.05, 0.95)

def _synth(text, speed):
    return tts.synthesize(
        text=text,
        voice_style=style,
        total_steps=8,
        speed=speed,
        max_chunk_length=300,
        silence_duration=0.12,
        lang='ja',
        verbose=False,
    )

def _split_clauses(text):
    # Prefer natural Japanese sentence/clause boundaries while keeping punctuation.
    parts = [x.strip() for x in re.findall(r'.+?(?:[。！？!?]|$)', text) if x.strip()]
    if len(parts) > 1:
        return parts
    parts = [x.strip() for x in re.findall(r'.+?(?:[、，,；;：:]|$)', text) if x.strip()]
    if len(parts) > 1:
        return parts
    # Last-resort split near the middle at a safe character boundary.
    if len(text) >= 12:
        mid = len(text) // 2
        return [text[:mid].strip(), text[mid:].strip()]
    return [text]

def synthesize_resilient(uid, text):
    failures = []
    for speed in DIRECT_SPEEDS:
        try:
            wav, duration = _synth(text, speed)
            if speed != 1.0:
                print(f'{VOICE}: recovered {uid} with speed={speed:.2f}')
            return wav, duration, {'mode':'direct','speed':speed}
        except Exception as exc:
            failures.append(f'{type(exc).__name__}: {exc}')
            print(f'{VOICE}: retry {uid} speed={speed:.2f} after {type(exc).__name__}: {exc}')

    pieces = [p for p in _split_clauses(text) if p]
    if len(pieces) <= 1:
        raise RuntimeError(f'{VOICE} {uid}: all synthesis retries failed: {failures[-3:]}')

    rendered = []
    durations = []
    used_speeds = []
    for i, piece in enumerate(pieces, 1):
        piece_ok = False
        for speed in DIRECT_SPEEDS:
            try:
                wav, duration = _synth(piece, speed)
                rendered.append(np.asarray(wav, dtype=np.float32))
                try:
                    durations.append(float(np.asarray(duration).reshape(-1)[0]))
                except Exception:
                    durations.append(rendered[-1].shape[-1] / sample_rate)
                used_speeds.append(speed)
                piece_ok = True
                break
            except Exception as exc:
                print(f'{VOICE}: clause retry {uid} part={i}/{len(pieces)} speed={speed:.2f} after {type(exc).__name__}: {exc}')
        if not piece_ok:
            raise RuntimeError(f'{VOICE} {uid}: clause {i}/{len(pieces)} could not be synthesized')

    silence = np.zeros((1, max(1, int(sample_rate * 0.12))), dtype=np.float32)
    joined = []
    for i, wav in enumerate(rendered):
        if wav.ndim == 1:
            wav = wav.reshape(1, -1)
        joined.append(wav)
        if i + 1 < len(rendered):
            joined.append(silence)
    combined = np.concatenate(joined, axis=1)
    total_duration = np.asarray([combined.shape[-1] / sample_rate], dtype=np.float32)
    print(f'{VOICE}: recovered {uid} by clause fallback ({len(pieces)} pieces)')
    return combined, total_duration, {'mode':'clauses','pieces':len(pieces),'speeds':used_speeds}

fallbacks = {}

with tempfile.TemporaryDirectory(prefix=f'supertonic-{VOICE}-') as td:
    tmp = Path(td)
    mp3_files = []
    for n, (uid, rec) in enumerate(lines.items(), 1):
        text = str(rec.get('text') or '').strip()
        if not text:
            raise SystemExit(f'Empty text for {uid}')
        try:
            wav, duration, recovery = synthesize_resilient(uid, text)
        except Exception as exc:
            raise SystemExit(f'Unable to synthesize {uid} ({text}): {exc}') from exc
        if recovery.get('mode') != 'direct' or float(recovery.get('speed', 1.0)) != 1.0:
            fallbacks[uid] = {'text': text, **recovery}
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
        if n % 100 == 0 or n == len(lines):
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
if tar_path.stat().st_size < 500000:
    raise SystemExit('TAR unexpectedly small')

manifest = {
    'version': 4,
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
    'fallbackCount': len(fallbacks),
    'fallbacks': fallbacks,
    'members': members,
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
print(f'Built {tar_path} ({tar_path.stat().st_size:,} bytes), {len(members)} recordings, {len(fallbacks)} resilient fallbacks')
