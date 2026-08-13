from pathlib import Path
import re
p=Path('listening.html');s=p.read_text(encoding='utf-8')
old='if(new Set(keys).size!==4)return null;return shuffle(rows)'
gate='if(new Set(keys).size!==4)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null}return shuffle(rows)'
if old in s:s=s.replace(old,gate,1)
elif 'const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh))' not in s:raise SystemExit('choice gate anchor not found')
pool='''function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}\nfunction voicevoxQuestionAvailable(q){return !!q?.id&&(!!voicevoxFullIndex?.questions?.[q.id]||!!voicevoxIndex?.items?.[q.id])}\nfunction pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));if(($('input[name=audioEngine]:checked')?.value||'voicevox')==='voicevox')p=p.filter(voicevoxQuestionAvailable);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
s,n=re.subn(r'function hasCatalogOptions\(x\)\{.*?\}\nfunction pool\(\)\{.*?\}',pool,s,count=1,flags=re.S)
if n!=1:raise SystemExit('pool patch failed')
s=s.replace('🎭 VOICEVOX<br>自動備援','🎭 VOICEVOX<br>錄音題庫')
p.write_text(s,encoding='utf-8');print('VOICEVOX mode now uses recorded questions only')
