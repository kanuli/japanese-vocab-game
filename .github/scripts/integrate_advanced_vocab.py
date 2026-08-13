#!/usr/bin/env python3
from pathlib import Path
import re

p=Path('index.html')
s=p.read_text(encoding='utf-8')
MARK='ADVANCED_VOCAB_INTEGRATION_V1'
if MARK in s:
    print('advanced vocabulary integration already present')
    raise SystemExit(0)

# Visible source status.
anchor='<div id="webStatus" class="muted">正在載入…</div>'
if anchor not in s:
    raise SystemExit('webStatus anchor not found')
s=s.replace(anchor,anchor+'<div id="advancedStatus" class="muted" style="margin-top:5px">🧩 進階補充詞：準備中…</div>',1)

# Opt-in/out switch (default on because this is a learning expansion requested by the user).
avail='<div id="availability" class="notice">正在載入單字…</div>'
toggle='<div id="advancedToggleBox" class="notice" style="background:#f4f7ff;border-color:#c9d6fa"><label style="display:flex;gap:9px;align-items:flex-start;cursor:pointer"><input id="includeAdvanced" type="checkbox" checked style="margin-top:3px"><span><b>包含進階補充詞</b>（推定 N1–N5）<br><span class="muted">JLPT 核心詞保持不變；額外常用現代詞會標示「推定」。</span></span></label></div>'
if avail not in s:
    raise SystemExit('availability anchor not found')
s=s.replace(avail,toggle+avail,1)

# State variable.
if 'let web=[],manual=' not in s:
    raise SystemExit('web state anchor not found')
s=s.replace('let web=[],manual=','let web=[],advanced=[],manual=',1)

old='function allWords(){return[...web,...manual].map(w=>({...w,pos:w.pos||guessPos(w.kanji||w.reading)}))}'
if old not in s:
    raise SystemExit('allWords anchor not found')
new=r'''/* ADVANCED_VOCAB_INTEGRATION_V1 */
async function loadAdvanced(){
 const st=$("#advancedStatus"); if(st)st.textContent="🧩 正在載入進階補充詞…";
 try{
  const r=await fetch(`./advanced-vocab.json?v=${Date.now()}`,{cache:"no-cache"});
  if(!r.ok)throw Error(`HTTP ${r.status}`);
  const d=await r.json(); advanced=Array.isArray(d)?d:(d.words||[]);
  const counts={N1:0,N2:0,N3:0,N4:0,N5:0}; advanced.forEach(w=>{if(counts[w.level]!==undefined)counts[w.level]++});
  if(st)st.textContent=`🧩 進階補充：${advanced.length.toLocaleString()} 詞（推定 N1 ${counts.N1} / N2 ${counts.N2} / N3 ${counts.N3} / N4 ${counts.N4} / N5 ${counts.N5}）`;
 }catch(e){advanced=[];if(st)st.textContent="🧩 進階補充詞尚未建立；目前只使用 JLPT 核心詞。";console.warn("advanced vocabulary unavailable",e)}
 update();
}
function levelLabel(w){if(w?.estimated)return `推定 ${w.level} · 進階補充`;if(w?.source==="manual"||w?.sourceType==="manual")return `${w.level} · 手動`;return `${w.level} · JLPT核心`}
function allWords(){
 const base=[...web,...manual];
 if($("#includeAdvanced")?.checked){
  const seen=new Set(base.map(w=>`${w.reading}|${w.kanji||w.displayWord||w.reading}`));
  for(const w of advanced){const k=`${w.reading}|${w.kanji||w.displayWord||w.reading}`;if(!seen.has(k)){seen.add(k);base.push(w)}}
 }
 return base.map(w=>({...w,pos:w.pos||guessPos(w.kanji||w.reading)}))
}'''
s=s.replace(old,new,1)

# Show estimated/core status in the answer sheet.
s=s.replace('$("#aLevel").textContent=c.level;','$("#aLevel").textContent=levelLabel(c);',1)

# Toggle updates counts/availability immediately.
mode='$$\'input[name=mode]\''
# Current minified app uses this exact event anchor.
event_anchor='$$(' + "'input[name=mode]'" + ').forEach(x=>x.onchange=availability);'
if event_anchor in s:
    s=s.replace(event_anchor,event_anchor+'$("#includeAdvanced").onchange=update;',1)
else:
    # Fallback: put it before start binding.
    b='$("#start").onclick=start;'
    if b not in s: raise SystemExit('event binding anchor not found')
    s=s.replace(b,'$("#includeAdvanced").onchange=update;'+b,1)

# Start both independent sources.
if 'update();loadWeb();})();' in s:
    s=s.replace('update();loadWeb();})();','update();loadWeb();loadAdvanced();})();',1)
elif 'update();loadWeb(false);})();' in s:
    s=s.replace('update();loadWeb(false);})();','update();loadWeb(false);loadAdvanced();})();',1)
else:
    raise SystemExit('startup anchor not found')

# Attribution/labeling note.
needle='JLPT 官方不再公布固定詞彙清單，因此等級屬學習用分類。'
extra='JLPT 官方不再公布固定詞彙清單，因此等級屬學習用分類。進階補充詞取自 JMdict common 資料與中文維基詞典（kaikki.org），並按公開語料頻率分成「推定 N1–N5」；推定級別不是 JLPT 官方分類。'
if needle in s:s=s.replace(needle,extra,1)

p.write_text(s,encoding='utf-8')
print('index.html integrated with advanced-vocab.json')
