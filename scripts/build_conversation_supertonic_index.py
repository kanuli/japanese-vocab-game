import json
import os
from pathlib import Path

CATALOG = Path(os.environ.get('CATALOG', 'conversation-audio-catalog.json'))
MANIFEST_DIR = Path(os.environ.get('MANIFEST_DIR', 'conversation-supertonic-manifests'))
OUT = Path(os.environ.get('OUT', 'conversation-supertonic-index.json'))
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'kanuli/japanese-vocab-game')
HF_DATASET_REPO = os.environ.get('HF_DATASET_REPO', 'kanuli1983/japanese-listening-voicevox-backup')
RELEASE_TAG = os.environ.get('RELEASE_TAG', 'conversation-supertonic-v1')

catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
voices = catalog.get('voices') or {}
lines = catalog.get('lines') or {}
text_map = catalog.get('textMap') or {}
if len(voices) != 10:
    raise SystemExit(f'Expected 10 voices, got {len(voices)}')
if len(lines) < 2600:
    raise SystemExit(f'Expected at least 2600 unique utterances, got {len(lines)}')

out_voices = {}
for key, label in voices.items():
    p = MANIFEST_DIR / f'{key}.json'
    if not p.is_file():
        raise SystemExit(f'Missing manifest: {p}')
    m = json.loads(p.read_text(encoding='utf-8'))
    if m.get('voice') != key or int(m.get('count', 0)) != len(lines):
        raise SystemExit(f'Invalid manifest for {key}: {m.get("count")} / {len(lines)}')
    if set(m.get('members') or {}) != set(lines):
        raise SystemExit(f'Member coverage mismatch for {key}')
    asset = m.get('asset') or f'{key}.tar'
    out_voices[key] = {
        'label': label,
        'codec': m.get('codec', 'mp3'),
        'sampleRate': int(m.get('sampleRate', 44100)),
        'bitrateKbps': int(m.get('bitrateKbps', 96)),
        'qualitySteps': int(m.get('qualitySteps', 8)),
        'githubUrl': f'https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/{asset}',
        'hfUrl': f'https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/conversation/supertonic/v1/{asset}?download=true',
        'members': m['members'],
    }

out = {
    'version': 2,
    'status': 'ready',
    'engine': 'supertonic-3',
    'language': 'ja',
    'sceneCount': int(catalog.get('sceneCount', 0)),
    'sourceLineCount': int(catalog.get('sourceLineCount', 0)),
    'conversationCount': int(catalog.get('conversationCount', 0)),
    'utteranceCount': len(lines),
    'voiceCount': len(out_voices),
    'recordingCount': len(lines) * len(out_voices),
    'lines': text_map,
    'voices': out_voices,
}
if out['sceneCount'] != 61 or out['sourceLineCount'] != 3050 or out['conversationCount'] != 1525:
    raise SystemExit(f"Expected 61 scenes / 1525 conversations / 3050 source lines, got {out['sceneCount']} / {out['conversationCount']} / {out['sourceLineCount']}")
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
print(f"Final Supertonic 3 coverage: {out['voiceCount']} voices × {out['utteranceCount']} unique utterances = {out['recordingCount']} recordings")
