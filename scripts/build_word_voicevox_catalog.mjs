#!/usr/bin/env node
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';

const CORE_URLS=[
  'https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv',
  'https://cdn.jsdelivr.net/gh/5mdld/anki-jlpt-decks@main/deck-source/notes.csv'
];
const F=['Notetype','Deck','NoteID','VocabKanji','VocabPitch','VocabPoS','VocabFurigana','VocabDefSC','VocabDefTC','VocabPlus','VocabAudio','SentType1','SentKanji1','SentFurigana1','SentDefSC1','SentDefTC1','SentAudio1','SentType2','SentKanji2','SentFurigana2','SentDefSC2','SentDefTC2','SentAudio2','SentType3','SentKanji3','SentFurigana3','SentDefSC3','SentDefTC3','SentAudio3','SentType4','SentKanji4','SentFurigana4','SentDefSC4','SentDefTC4','SentAudio4','Sort','Alt1','Alt2','Tags'];
const SHARDS=5;

function decodeEntities(s){return String(s??'').replace(/&nbsp;/gi,' ').replace(/&amp;/gi,'&').replace(/&lt;/gi,'<').replace(/&gt;/gi,'>').replace(/&quot;/gi,'"').replace(/&#39;/gi,"'");}
function strip(s){return decodeEntities(String(s??'').replace(/\[sound:[^\]]+\]/gi,' ').replace(/<br\s*\/?>/gi,'；').replace(/<[^>]*>/g,' ')).replace(/\s+/g,' ').trim();}
function hasKanji(s){return /[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]/.test(s||'');}
function isKana(s){return !!s&&/^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$/.test(String(s).replace(/\s+/g,''));}
function readingFrom(f,w){let s=String(f||w||'').replace(/[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]+\[([^\]]+)\]/g,'$1').replace(/\[([^\]]+)\]/g,'$1');s=strip(s).replace(/\s+/g,'');return isKana(s)?s:(isKana(w)?w:'');}
function parseCsv(t){const h=String(t).split(/\r?\n/,1)[0].trim().toLowerCase(),d=h==='#separator:comma'?',':h==='#separator:semicolon'?';':'\t',rows=[];let row=[],f='',q=false;for(let p=0;p<t.length;p++){const c=t[p];if(q){if(c==='"'){if(t[p+1]==='"'){f+='"';p++;}else q=false;}else f+=c;}else if(c==='"')q=true;else if(c===d){row.push(f);f='';}else if(c==='\n'){row.push(f);rows.push(row);row=[];f='';}else if(c!=='\r')f+=c;}if(f||row.length){row.push(f);rows.push(row);}return rows;}
function core(rows){const out=[];for(let r of rows){if(!r.length||String(r[0]).startsWith('#'))continue;if(r.length===F.length+1)r=r.slice(1);if(r.length!==F.length)continue;const f=Object.fromEntries(F.map((n,j)=>[n,r[j]||''])),w=strip(f.VocabKanji).replace(/\s+/g,''),lv=`${f.Deck} ${f.Tags}`.match(/(?:^|[^A-Za-z0-9])N([1-5])(?=$|[^0-9])/i),rd=readingFrom(f.VocabFurigana,w);if(w&&lv&&rd)out.push({level:`N${lv[1]}`,reading:rd,kanji:hasKanji(w)?w:'',displayWord:w,estimated:false});}return out;}
function normAdvanced(x){if(!x)return null;let r=String(x.reading||'').trim(),k=String(x.kanji||'').trim(),d=String(x.displayWord||'').trim();if(hasKanji(r)&&isKana(k)){const z=r;r=k;k=z;d=z;}else if(!isKana(r)&&isKana(k)){const z=d||r;r=k;k=hasKanji(z)?z:'';d=z||r;}else if(!r&&isKana(d))r=d;if(!isKana(r))return null;return{level:/^N[1-5]$/.test(x.level)?x.level:'N1',reading:r,kanji:hasKanji(k)?k:'',displayWord:d||k||r,estimated:true};}
function keyOf(w){return `${w.reading}|${w.kanji||w.displayWord||w.reading}`;}
function stableId(key){return crypto.createHash('sha1').update(key,'utf8').digest('hex').slice(0,16);}
async function fetchCore(){let last=null;for(const u of CORE_URLS){try{const r=await fetch(u,{headers:{'user-agent':'word-voicevox-catalog'}});if(!r.ok)throw new Error(`HTTP ${r.status}`);const rows=core(parseCsv(await r.text()));if(rows.length<10000)throw new Error(`core too small: ${rows.length}`);return rows;}catch(e){last=e;}}throw last||new Error('core fetch failed');}
function loadAdvanced(){globalThis.window=globalThis;globalThis.ADVANCED_WORDS=[];for(const p of ['advanced_words_curated.js','data/advanced_vocab.js']){const src=fs.readFileSync(p,'utf8');vm.runInThisContext(src,{filename:p});}return (globalThis.ADVANCED_WORDS||[]).map(normAdvanced).filter(Boolean);}

const coreRows=await fetchCore();
const advRows=loadAdvanced();
const seen=new Set(),merged=[];
for(const w of [...coreRows,...advRows]){const key=keyOf(w);if(seen.has(key))continue;seen.add(key);merged.push({...w,key});}
merged.sort((a,b)=>a.key<b.key?-1:a.key>b.key?1:0);
const words=merged.map((w,i)=>({id:stableId(w.key),key:w.key,reading:w.reading,written:w.kanji||w.displayWord||w.reading,level:w.level,estimated:!!w.estimated,shard:i%SHARDS}));
const ids=new Set(words.map(w=>w.id));
if(ids.size!==words.length)throw new Error('Stable ID collision detected');
if(words.length<22000)throw new Error(`Merged vocabulary unexpectedly small: ${words.length}`);
const counts={N1:0,N2:0,N3:0,N4:0,N5:0};for(const w of words)counts[w.level]++;
const shardCounts=Array.from({length:SHARDS},(_,s)=>words.filter(w=>w.shard===s).length);
const out={version:1,generated:new Date().toISOString(),source:'wordaudio runtime-equivalent core + curated + prebuilt advanced vocabulary',wordCount:words.length,shardCount:SHARDS,coreCount:coreRows.length,advancedCount:advRows.length,countsByLevel:counts,shardCounts,words};
fs.writeFileSync(process.env.CATALOG_OUT||'word-voicevox-catalog.json',JSON.stringify(out));
console.log(`VOICEVOX vocabulary catalog: ${words.length} words; core=${coreRows.length}; advanced=${advRows.length}`);
console.log('levels',counts,'shards',shardCounts);
