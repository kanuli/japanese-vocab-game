from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

old='if(new Set(keys).size!==4)return null;return shuffle(rows)'
new='if(new Set(keys).size!==4)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null}return shuffle(rows)'

if old not in s:
    if 'const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh))' in s:
        print('catalog similarity gate already present')
    else:
        raise SystemExit('catalog choice return point not found')
else:
    s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')
    print('catalog listening choice gate applied')
