#!/usr/bin/env python3
from pathlib import Path

# Word List browser fallback.
p=Path('wordlist-audio.js');s=p.read_text(encoding='utf-8')
s=s.replace('Supertonic AI','Supertonic 3').replace('Supertonic 無法載入','Supertonic 3 無法載入').replace('totalSteps:5','totalSteps:8')
p.write_text(s,encoding='utf-8')

# Word Audio wrapper must force clients to refetch the updated fallback.
p=Path('wordaudio-voice.js');s=p.read_text(encoding='utf-8')
s=s.replace('wordaudio-ai.js?v=20260814v2','wordaudio-ai.js?v=20260815v3')
p.write_text(s,encoding='utf-8')

# Page cache keys.
p=Path('wordaudio.html');s=p.read_text(encoding='utf-8')
s=s.replace('wordaudio-voice.js?v=4','wordaudio-voice.js?v=5').replace('wordaudio-multivoice.js?v=20260815v1','wordaudio-multivoice.js?v=20260815v2')
p.write_text(s,encoding='utf-8')

p=Path('wordlist.html');s=p.read_text(encoding='utf-8')
s=s.replace('wordlist-audio.js?v=4','wordlist-audio.js?v=5')
p.write_text(s,encoding='utf-8')
print('Vocabulary Supertonic 3 fallbacks standardized at 8 steps.')
