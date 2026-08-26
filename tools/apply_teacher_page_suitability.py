from pathlib import Path
import re

# Make Mock Test use the same teacher-calibrated vocabulary runtime as the main vocab pages.
html = Path('mocktest.html')
s = html.read_text(encoding='utf-8')
anchor = '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>'
loader = '<script src="./advanced_words.js?v=20260826v5teacher"></script>\n<script src="./wordaudio-data.js?v=20260825v2"></script>\n'
if loader not in s:
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
old = '''async function fetchVocab(){let err;for(const u of VOCAB_URLS){try{const r=await fetchWithTimeout(u,{cache:"default"},6000);if(!r.ok)throw Error(`HTTP ${r.status}`);const rows=rowsToVocab(parseCSV(await r.text()));if(rows.length<1000)throw Error("詞彙資料不足");return rows}catch(e){err=e}}console.warn(err);return Object.entries(FALLBACK_VOCAB).flatMap(([level,rows],i)=>rows.map((x,j)=>({id:`fbv-${level}-${j}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})))}'''
new = '''function teacherRuntimeVocab(){const words=Array.isArray(window.WA?.words)?window.WA.words:[];if(words.length<32000)return[];const out=[],seen=new Set;for(const w of words){const level=String(w.level||'').toUpperCase();const word=String(w.kanji||w.displayWord||w.reading||'').trim(),rd=String(w.reading||'').trim(),meaning=String(w.meaning||'').trim();if(!/^N[1-5]$/.test(level)||!word||!rd||!meaning||!kana(rd))continue;const k=`${level}|${word}|${rd}`;if(seen.has(k))continue;seen.add(k);out.push({id:`tv-${w.id||`${level}-${word}-${rd}`}`,level,word,reading:rd,meaning,sentence:String(w.sentence||w.example||''),pos:String(w.pos||''),levelSource:String(w.levelSource||'teacher-runtime')})}return out}
async function waitTeacherRuntime(ms=5200){const started=Date.now();while(Date.now()-started<ms){const rows=teacherRuntimeVocab();if(rows.length>=32000)return rows;await new Promise(r=>setTimeout(r,80))}return teacherRuntimeVocab()}
async function fetchVocab(){let teacher=await waitTeacherRuntime();if(teacher.length>=32000){globalThis.MOCKTEST_VOCAB_META={source:'teacher-runtime',count:teacher.length};return teacher}let err;for(const u of VOCAB_URLS){try{const r=await fetchWithTimeout(u,{cache:"default"},6000);if(!r.ok)throw Error(`HTTP ${r.status}`);const rows=rowsToVocab(parseCSV(await r.text()));if(rows.length<1000)throw Error("詞彙資料不足");globalThis.MOCKTEST_VOCAB_META={source:'external-fallback',count:rows.length};return rows}catch(e){err=e}}console.warn(err);const rows=Object.entries(FALLBACK_VOCAB).flatMap(([level,rows],i)=>rows.map((x,j)=>({id:`fbv-${level}-${j}`,level,word:x[0],reading:x[1],meaning:x[2],sentence:"",pos:""})));globalThis.MOCKTEST_VOCAB_META={source:'built-in-fallback',count:rows.length};return rows}'''
if old in s:
    s = s.replace(old, new, 1)
elif 'function teacherRuntimeVocab()' not in s or "source:'teacher-runtime'" not in s:
    raise SystemExit('mocktest.js fetchVocab pattern not found')
js.write_text(s, encoding='utf-8')
print('teacher page suitability integration applied')
