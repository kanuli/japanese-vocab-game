#!/usr/bin/env python3
from pathlib import Path

TAG='<script defer src="./site-health.js?v=20260817v1"></script>'
changed=[]
for p in sorted(Path('.').glob('*.html')):
    s=p.read_text(encoding='utf-8')
    if 'site-health.js' in s:
        continue
    if '</head>' not in s:
        raise SystemExit(f'{p}: missing </head>')
    s=s.replace('</head>',TAG+'\n</head>',1)
    p.write_text(s,encoding='utf-8')
    changed.append(str(p))
print('Injected site health into',len(changed),'pages:',', '.join(changed))
