#!/usr/bin/env python3
from pathlib import Path

p=Path('wordaudio.html')
s=p.read_text(encoding='utf-8')
needle='<script src="./wordaudio-init.js?v=2"></script>'
insert=needle+'<script src="./wordaudio-multivoice.js?v=20260815v1"></script>'
if insert not in s:
    if needle not in s:
        raise SystemExit('wordaudio-init script anchor not found')
    s=s.replace(needle,insert,1)
# Keep the static HTML meaningful before JS enhancement loads.
s=s.replace('<h2>✨ Supertonic AI 日語語音</h2>','<h2>🔊 單字語音｜VOICEVOX / Supertonic 3 / AivisSpeech</h2>',1)
s=s.replace('正在檢查 Supertonic AI 日語語音…','正在檢查 VOICEVOX / Supertonic 3 / AivisSpeech 日語語音…',1)
p.write_text(s,encoding='utf-8')
print('Word Audio multi-engine layer installed.')
