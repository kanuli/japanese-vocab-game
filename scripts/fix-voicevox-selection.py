from pathlib import Path

files = [Path('listening.html'), Path('scripts/patch-listening-onedrive-voicevox.py')]
old = 'radio.disabled=true;connect.disabled=true;setup.disabled=true;'
new = 'radio.disabled=false;connect.disabled=true;setup.disabled=true;'

for p in files:
    s = p.read_text(encoding='utf-8')
    if new in s:
        print(f'{p}: already fixed')
        continue
    if old not in s:
        raise SystemExit(f'{p}: VOICEVOX disabled-state anchor not found')
    s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')
    print(f'{p}: fixed VOICEVOX pre-configuration selection')
