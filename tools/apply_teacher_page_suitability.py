from pathlib import Path
import re

# Make Mock Test use the same teacher-calibrated vocabulary runtime as the main vocab pages.
html = Path('mocktest.html')
s = html.read_text(encoding='utf-8')
anchor = '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>'
loader = '<script src="./advanced_words.js?v=20260826v5teacher"></script>\n<script src="./wordaudio-data.js?v=20260827v3teacher"></script>\n'
if loader not in s:
    # Replace an earlier teacher loader version if present, otherwise insert it.
    s = re.sub(r'<script src="\./advanced_words\.js\?v=[^"]+"></script>\s*<script src="\./wordaudio-data\.js\?v=[^"]+"></script>\s*', '', s, count=1)
    if anchor not in s:
        raise SystemExit('mocktest.html grammar script anchor not found')
    s = s.replace(anchor, loader + anchor, 1)
old_footer = 'Web vocabulary: 5mdld/anki-jlpt-decks；文法／例句：Hanabira。'
new_footer = '詞彙優先使用本站與單字清單相同的教師校準 runtime；5mdld/anki-jlpt-decks 只在本地教師題庫無法載入時作備援。文法／例句：Hanabira。'
if old_footer in s:
    s = s.replace(old_footer, new_footer, 1)
elif new_footer not in s:
    raise SystemExit('mocktest.html source footer pattern not found')
html.write_text(s, encoding='utf-8')

js = Path('mocktest.js')
s = js.read_text(encoding='utf-8')

if 'const FALLBACK_LEVEL_FIXES=' not in s:
    marker='const FALLBACK_GRAMMAR={'
    if marker not in s: raise SystemExit('mocktest.js FALLBACK_GRAMMAR marker missing')
    helper='''const FALLBACK_LEVEL_FIXES={
"きゅうに|急に":"N3","けいけん|経験":"N4","かくにん|確認":"N4","けっか|結果":"N4","わざわざ|わざわざ":"N2",
"かいぜん|改善":"N3","けいこう|傾向":"N3","じっし|実施":"N3","あいにく|あいにく":"N3","とうとう|とうとう":"N4",
"はあく|把握":"N2","ちくせき|蓄積":"N2","すいそく|推測":"N2","みとおし|見通し":"N2","おおむね|おおむね":"N2"
};
const FALLBACK_EXTRA={N1:[
["顧みる","かえりみる","回顧、顧及"],["遂げる","とげる","完成、達成"],["侮る","あなどる","輕視、蔑視"],["覆す","くつがえす","推翻、顛覆"],["滞る","とどこおる","停滯、拖延"],["携わる","たずさわる","參與、從事"],["潔い","いさぎよい","乾脆、潔白"]
]};
function teacherAlignedFallbackVocab(){const out=[],seen=new Set;for(const [declared,rows] of Object.entries(FALLBACK_VOCAB)){for(const x of rows){const level=FALLBACK_LEVEL_FIXES[`${x[1]}|${x[0]}`]||declared,k=`${level}|${x[0]}|${x[1]}`;if(!seen.has(k)){seen.add(k);out.push({id:`fbv-${level}-${out.length}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})}}}for(const [level,rows] of Object.entries(FALLBACK_EXTRA)){for(const x of rows){const k=`${level}|${x[0]}|${x[1]}`;if(!seen.has(k)){seen.add(k);out.push({id:`fbx-${level}-${out.length}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})}}}return out}
'''
    s=s.replace(marker,helper+marker,1)

if 'const SPECIAL_LEVEL_FIXES=' not in s:
    marker='const QUICK_RESPONSE={'
    if marker not in s: raise SystemExit('mocktest.js QUICK_RESPONSE marker missing')
    helper='''const SPECIAL_LEVEL_FIXES={"おおむね":"N2","とうとう":"N4","あいにく":"N3","わざわざ":"N2","急に":"N3"};
(()=>{const moved={N1:[],N2:[],N3:[],N4:[],N5:[]};for(const [declared,rows] of Object.entries(SPECIAL)){for(const q of rows){const term=String(q.q||'').match(/『([^』]+)』/)?.[1]||'';const level=SPECIAL_LEVEL_FIXES[term]||declared;moved[level].push(q)}}for(const l of Object.keys(moved))SPECIAL[l]=moved[l]})();
'''
    s=s.replace(marker,helper+marker,1)

old = '''async function fetchVocab(){let err;for(const u of VOCAB_URLS){try{const r=await fetchWithTimeout(u,{cache:"default"},6000);if(!r.ok)throw Error(`HTTP ${r.status}`);const rows=rowsToVocab(parseCSV(await r.text()));if(rows.length<1000)throw Error("詞彙資料不足");return rows}catch(e){err=e}}console.warn(err);return Object.entries(FALLBACK_VOCAB).flatMap(([level,rows],i)=>rows.map((x,j)=>({id:`fbv-${level}-${j}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})))}'''
new = '''function teacherRuntimeVocab(){const words=Array.isArray(window.WA?.words)?window.WA.words:[];if(words.length<32000)return[];const out=[],seen=new Set;for(const w of words){const level=String(w.level||'').toUpperCase();const word=String(w.kanji||w.displayWord||w.reading||'').trim(),rd=String(w.reading||'').trim(),meaning=String(w.meaning||'').trim();if(!/^N[1-5]$/.test(level)||!word||!rd||!meaning||!kana(rd))continue;const k=`${level}|${word}|${rd}`;if(seen.has(k))continue;seen.add(k);out.push({id:`tv-${w.id||`${level}-${word}-${rd}`}`,level,word,reading:rd,meaning,sentence:String(w.sentence||w.example||''),pos:String(w.pos||''),levelSource:String(w.levelSource||'teacher-runtime')})}return out}
async function waitTeacherRuntime(ms=30000){const started=Date.now();if(typeof window.WA?.buildWords==='function'){try{await Promise.race([window.WA.buildWords(),new Promise(r=>setTimeout(r,Math.min(20000,ms)))])}catch(e){console.warn('Teacher vocabulary builder unavailable',e)}}while(Date.now()-started<ms){const rows=teacherRuntimeVocab();if(rows.length>=32000)return rows;await new Promise(r=>setTimeout(r,100))}return teacherRuntimeVocab()}
async function fetchVocab(){let teacher=await waitTeacherRuntime();if(teacher.length>=32000){globalThis.MOCKTEST_VOCAB_META={source:'teacher-runtime',count:teacher.length};return teacher}let err;for(const u of VOCAB_URLS){try{const r=await fetchWithTimeout(u,{cache:"default"},6000);if(!r.ok)throw Error(`HTTP ${r.status}`);const rows=rowsToVocab(parseCSV(await r.text()));if(rows.length<1000)throw Error("詞彙資料不足");globalThis.MOCKTEST_VOCAB_META={source:'external-fallback',count:rows.length};return rows}catch(e){err=e}}console.warn(err);const rows=teacherAlignedFallbackVocab();globalThis.MOCKTEST_VOCAB_META={source:'built-in-fallback',count:rows.length};return rows}'''
if old in s:
    s = s.replace(old, new, 1)
elif 'function teacherRuntimeVocab()' not in s or "source:'teacher-runtime'" not in s:
    raise SystemExit('mocktest.js fetchVocab pattern not found')
# Upgrade an already-integrated older wait function deterministically.
s=re.sub(r'async function waitTeacherRuntime\(ms=\d+\)\{.*?\}\nasync function fetchVocab\(\)', new.split('\nasync function fetchVocab()')[0]+'\nasync function fetchVocab()', s, count=1, flags=re.S)
s=s.replace('const rows=Object.entries(FALLBACK_VOCAB).flatMap(([level,rows],i)=>rows.map((x,j)=>({id:`fbv-${level}-${j}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})));globalThis.MOCKTEST_VOCAB_META={source:\'built-in-fallback\',count:rows.length};return rows}',
            'const rows=teacherAlignedFallbackVocab();globalThis.MOCKTEST_VOCAB_META={source:\'built-in-fallback\',count:rows.length};return rows}')
js.write_text(s, encoding='utf-8')
print('teacher page suitability integration applied')
