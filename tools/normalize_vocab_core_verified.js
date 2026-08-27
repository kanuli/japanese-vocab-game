#!/usr/bin/env node
'use strict';
const fs=require('fs'),vm=require('vm');
const PATH='data/vocab_core_verified.js';
const INLINE=/\[[ぁ-ゖァ-ヺー]+\]/g;
const source=fs.readFileSync(PATH,'utf8');

function extract(){
  const marker='window.VOCAB_CORE_VERIFIED=map;window.VOCAB_CORE_VERIFIED_META=M;';
  if(!source.includes(marker)) throw new Error('verified core export marker not found');
  const instrumented=source.replace(marker,'window.__CORE_T=T;window.__CORE_M=M;'+marker);
  const sandbox={console:{log(){},warn(){},error(){}}}; sandbox.window=sandbox; sandbox.self=sandbox;
  vm.createContext(sandbox); vm.runInContext(instrumented,sandbox,{timeout:30000});
  const T=JSON.parse(JSON.stringify(sandbox.__CORE_T));
  const M=JSON.parse(JSON.stringify(sandbox.__CORE_M));
  if(!Array.isArray(T)||T.length<10000) throw new Error('unexpected core table size '+(T&&T.length));
  return {T,M};
}
function clean(s){return String(s??'').replace(INLINE,'');}
function gradeRank(g){return ({A:5,B:4,C:3,D:2})[String(g||'').trim().toUpperCase()]||0;}
function basisRank(s){
  s=String(s||'').toLowerCase();
  if(s.includes('manual')||s.includes('verified')) return 6;
  if(s.includes('secondary-exact')) return 5;
  if(s.includes('core-exact')) return 4;
  if(s.includes('exact')) return 3;
  if(s.includes('corroborat')||s.includes('validat')) return 2;
  return s?1:0;
}
function rank(x,dirty){return [gradeRank(x[7]),basisRank(x[8]),basisRank(x[5]),dirty?0:1,x.filter(v=>v!==null&&v!==undefined&&String(v)!=='').length];}
function cmp(a,b){for(let i=0;i<Math.max(a.length,b.length);i++){const d=(a[i]||0)-(b[i]||0);if(d)return d;}return 0;}
function fill(winner,loser){const out=winner.slice();for(let i=0;i<loser.length;i++){if((out[i]===null||out[i]===undefined||out[i]==='')&&loser[i]!==null&&loser[i]!==undefined&&loser[i]!=='')out[i]=loser[i];}return out;}

const {T,M}=extract();
const groups=new Map(); let malformed=0;
for(const row0 of T){
  const row=row0.slice(); const old=String(row[1]??row[0]??''); const dirty=INLINE.test(old); INLINE.lastIndex=0;
  const display=clean(old); if(display!==old) malformed++;
  row[1]=display; const key=String(row[0]??'').trim()+'|'+display.trim();
  if(!String(row[0]??'').trim()||!display.trim()) throw new Error('blank core lexical key');
  const r=rank(row0,dirty);
  if(!groups.has(key)){groups.set(key,{row,rank:r});continue;}
  const prev=groups.get(key);
  if(cmp(r,prev.rank)>0) groups.set(key,{row:fill(row,prev.row),rank:r});
  else prev.row=fill(prev.row,row);
}
const rows=[...groups.values()].map(x=>x.row);
const removed=T.length-rows.length;
const keys=new Set(rows.map(x=>String(x[0])+'|'+String(x[1])));
if(keys.size!==rows.length) throw new Error('duplicate clean core keys remain');
if(rows.length<10000||rows.length>T.length) throw new Error('unexpected normalized core size '+rows.length);
for(const x of rows){if(/\[[ぁ-ゖァ-ヺー]+\]/.test(String(x[0])+String(x[1])))throw new Error('inline annotation remains');}
M.rows=rows.length;
M.inlineReadingCleanup={sourceRows:T.length,canonicalRows:rows.length,malformedRows:malformed,duplicatesMerged:removed,policy:'teacher grade/basis before formatting cleanliness'};
const out='// AUTO-GENERATED teacher-audited JLPT core overlay. Do not edit by hand.\n'+
  '(()=>{"use strict";\nconst M='+JSON.stringify(M)+';\nconst T='+JSON.stringify(rows)+',map=new Map();\n'+
  'for(const x of T)map.set(`${x[0]}|${x[1]}`,{level:x[2],meaning:x[3],meaningSource:x[4],levelSource:x[5],entryId:x[6]||null,teacherGrade:x[7]||"",teacherBasis:x[8]||""});\n'+
  'window.VOCAB_CORE_VERIFIED=map;window.VOCAB_CORE_VERIFIED_META=M;\n})();\n';
fs.writeFileSync(PATH,out,'utf8');
console.log(JSON.stringify({sourceRows:T.length,canonicalRows:rows.length,malformedRows:malformed,duplicatesMerged:removed,bytes:Buffer.byteLength(out)},null,2));
