#!/usr/bin/env python3
from pathlib import Path
p=Path('wordlist.html')
s=p.read_text(encoding='utf-8')
s=s.replace('<h2>🔊 Supertonic 日語語音</h2>','<h2>🔊 單字語音｜VOICEVOX / Supertonic</h2>')
s=s.replace('./wordlist-audio.js?v=2','./wordlist-audio.js?v=3')
s=s.replace('./wordlist-audio.js?v=1','./wordlist-audio.js?v=3')
s=s.replace('./wordlist.js?v=2','./wordlist.js?v=3')
s=s.replace('./wordlist.js?v=1','./wordlist.js?v=3')
needle='<script src="./wordlist-audio.js?v=3"></script>'
voice='<script src="./wordlist-voicevox.js?v=1"></script>'
if voice not in s:
    s=s.replace(needle,needle+voice)
assert './wordlist-audio.js?v=3' in s
assert './wordlist-voicevox.js?v=1' in s
assert './wordlist.js?v=3' in s
p.write_text(s,encoding='utf-8')
print('wordlist.html patched for VOICEVOX + Supertonic repair client')
