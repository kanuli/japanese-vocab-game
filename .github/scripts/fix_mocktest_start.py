from pathlib import Path
import re

p = Path('mocktest.js')
s = p.read_text(encoding='utf-8')

# 1) Add a real fetch timeout so a stalled Web source cannot leave START disabled forever.
needle = 'const GRAMMAR_BASES=["https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/","https://cdn.jsdelivr.net/gh/tristcoil/hanabira.org-japanese-content@main/grammar_json/"];\n'
insert = needle + '''async function fetchWithTimeout(url,options={},ms=6000){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),ms);try{return await fetch(url,{...options,signal:controller.signal})}finally{clearTimeout(timer)}}\n'''
if 'function fetchWithTimeout' not in s:
    if needle not in s:
        raise SystemExit('GRAMMAR_BASES insertion point not found')
    s = s.replace(needle, insert, 1)

s = s.replace('await fetch(u,{cache:"default"})', 'await fetchWithTimeout(u,{cache:"default"},6000)')
s = s.replace('await fetch(b+GRAMMAR_FILES[level],{cache:"default"})', 'await fetchWithTimeout(b+GRAMMAR_FILES[level],{cache:"default"},6000)')

# 2) Cap similarity searches. Sorting thousands of entries for every question can freeze mobile Safari.
old_read = 'function similarReading(pool,c){return pool.filter(x=>x.id!==c.id&&x.reading!==c.reading).map(x=>({x,s:Math.abs(x.reading.length-c.reading.length)+(x.reading[0]===c.reading[0]?-.7:0)})).sort((a,b)=>a.s-b.s).map(o=>o.x)}'
new_read = 'function similarReading(pool,c){let base=pool.filter(x=>x.id!==c.id&&x.reading!==c.reading&&Math.abs(x.reading.length-c.reading.length)<=2);if(base.length<12)base=pool.filter(x=>x.id!==c.id&&x.reading!==c.reading);base=sample(base,Math.min(180,base.length));return base.map(x=>({x,s:Math.abs(x.reading.length-c.reading.length)+(x.reading[0]===c.reading[0]?-.7:0)})).sort((a,b)=>a.s-b.s).map(o=>o.x)}'
old_word = 'function similarWord(pool,c){return pool.filter(x=>x.id!==c.id&&x.word!==c.word).map(x=>({x,s:Math.abs(x.word.length-c.word.length)+(x.word[0]===c.word[0]?-.6:0)})).sort((a,b)=>a.s-b.s).map(o=>o.x)}'
new_word = 'function similarWord(pool,c){let base=pool.filter(x=>x.id!==c.id&&x.word!==c.word&&Math.abs(x.word.length-c.word.length)<=2);if(base.length<12)base=pool.filter(x=>x.id!==c.id&&x.word!==c.word);base=sample(base,Math.min(180,base.length));return base.map(x=>({x,s:Math.abs(x.word.length-c.word.length)+(x.word[0]===c.word[0]?-.6:0)})).sort((a,b)=>a.s-b.s).map(o=>o.x)}'
if old_read in s:
    s=s.replace(old_read,new_read,1)
if old_word in s:
    s=s.replace(old_word,new_word,1)
if new_read not in s or new_word not in s:
    raise SystemExit('similarity optimization patch not applied')

# 3) Make START visibly responsive and catch runtime generation errors.
start_pat = re.compile(r'function start\(\)\{if\(!loadDone\)return;state=buildTest\(\);if\(!state\.sections\.every\(s=>s\.questions\.length\)\)\{alert\("題庫暫時不足，請重新載入頁面後再試。"\);return\}\$\("#setup"\)\.style\.display="none";\$\("#resultPage"\)\.style\.display="none";\$\("#sectionGate"\)\.style\.display="none";\$\("#exam"\)\.style\.display="block";startSection\(\)\}')
new_start = '''let starting=false;\nfunction start(){if(!loadDone||starting)return;starting=true;const btn=$("#start");btn.disabled=true;btn.textContent="正在組卷…";$("#availability").textContent=`正在建立 ${currentLevel()} 模擬試卷，請稍候…`;setTimeout(()=>{try{state=buildTest();if(!state.sections.every(s=>s.questions.length))throw Error("題庫暫時不足");$("#setup").style.display="none";$("#resultPage").style.display="none";$("#sectionGate").style.display="none";$("#exam").style.display="block";startSection()}catch(e){console.error("Mock test start failed",e);state=null;alert("模擬試驗暫時無法建立。已保留頁面，請再按一次；若 Web 題庫失敗會自動使用備援。\n\n"+(e?.message||e));renderAvailability()}finally{starting=false;btn.textContent="開始模擬試驗 START";if($("#setup").style.display!=="none")btn.disabled=false}},40)}'''
s, n = start_pat.subn(lambda m:new_start, s, count=1)
if n != 1 and 'let starting=false;' not in s:
    raise SystemExit('start function patch target not found')

# 4) Explicitly reset button state when returning to setup.
s = s.replace('function restart(){clearTimer();stopAudio();state=null;', 'function restart(){clearTimer();stopAudio();state=null;starting=false;$("#start").textContent="開始模擬試驗 START";', 1)

# 5) Show a slow-loading message rather than appearing dead.
old_load = 'async function loadAll(){$("#sourceStatus").textContent="正在載入約 10,000 個詞彙及 N1–N5 文法例句…";'
new_load = 'async function loadAll(){$("#sourceStatus").textContent="正在載入約 10,000 個詞彙及 N1–N5 文法例句…";const slow=setTimeout(()=>{$("#availability").textContent="Web 題庫載入較慢，正在自動切換／嘗試備援來源…"},4500);'
if old_load in s:
    s=s.replace(old_load,new_load,1)
# clear watchdog once all sources resolve
s = s.replace('loadDone=true;const gtotal=', 'clearTimeout(slow);loadDone=true;const gtotal=', 1)

p.write_text(s,encoding='utf-8')
print('Patched mock test start reliability and mobile performance')
