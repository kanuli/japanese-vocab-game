#!/usr/bin/env python3
from pathlib import Path
pairs=[
 ('conversation.html','conversation-hosted-audio.js?v=20260814v1','conversation-hosted-audio.js?v=20260815v2'),
 ('translator.html','translator-hosted-voice.js?v=20260815v1','translator-hosted-voice.js?v=20260815v2'),
]
for name,old,new in pairs:
 p=Path(name);s=p.read_text(encoding='utf-8')
 if new not in s:
  if old not in s:raise SystemExit(f'{name}: cache anchor not found')
  s=s.replace(old,new,1)
 p.write_text(s,encoding='utf-8')
 print(name,new)
