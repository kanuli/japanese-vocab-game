import fs from 'node:fs';
import vm from 'node:vm';

const report={version:'20260822-quality1',listening:{},mock:{},failures:[]};
const norm=s=>String(s||'').normalize('NFKC').replace(/[\s　，。！？、,.!?「」『』（）()]/g,'').trim();
const choiceOK=s=>!!String(s||'').trim()&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(String(s));
const bigrams=s=>{s=norm(s);const a=new Set;for(let i=0;i<s.length-1;i++)a.add(s.slice(i,i+2));return a};
const sim=(a,b)=>{const A=bigrams(a),B=bigrams(b);let inter=0;for(const x of A)if(B.has(x))inter++;return inter/Math.max(1,A.size+B.size-inter)};

// -------- Listening original catalog full audit --------
const catalog=JSON.parse(fs.readFileSync('listening-original-catalog.json','utf8'));
const raw=Array.isArray(catalog.items)?catalog.items:[];
const perLevelRaw={N1:0,N2:0,N3:0,N4:0,N5:0},perLevelKept={N1:0,N2:0,N3:0,N4:0,N5:0};
const dropReasons=new Map,position=[0,0,0,0];
let kept=0,dropped=0;
for(const x of raw){
  const level=String(x.level||'').toUpperCase();if(level in perLevelRaw)perLevelRaw[level]++;
  const cs=Array.isArray(x.choicesZh)?x.choicesZh.map(v=>String(v||'').trim()):[];
  const correct=String(x.correctZh||'').trim(),keys=cs.map(norm),target=norm(correct),errs=[];
  if(!x.id||!/^N[1-5]$/.test(level)||!String(x.jp||'').trim())errs.push('identity');
  if(cs.length!==4)errs.push('choice-count');
  if(cs.some(v=>!choiceOK(v)))errs.push('non-traditional-choice');
  if(new Set(keys).size!==4)errs.push('duplicate-choice');
  const ci=keys.indexOf(target);if(!target||keys.filter(k=>k===target).length!==1)errs.push('answer-not-unique');
  if(ci>=0&&cs.length===4){
    const cl=[...target].length,near=keys.filter((_,i)=>i!==ci).map(k=>Math.min([...k].length,cl)/Math.max(1,Math.max([...k].length,cl)));
    if(near.length&&Math.max(...near)<.52)errs.push('answer-length-giveaway');
    for(let i=0;i<cs.length;i++)if(i!==ci){const len=Math.min(keys[i].length,target.length)/Math.max(1,Math.max(keys[i].length,target.length));if(len<.58||sim(cs[i],correct)<.08){errs.push('weak-distractor-similarity');break}}
  }
  if(errs.length){dropped++;for(const e of new Set(errs))dropReasons.set(e,(dropReasons.get(e)||0)+1)}else{kept++;if(level in perLevelKept)perLevelKept[level]++;if(ci>=0)position[ci]++}
}
report.listening={raw:raw.length,kept,dropped,perLevelRaw,perLevelKept,dropReasons:Object.fromEntries(dropReasons),correctPositionDistribution:position};
if(raw.length<6000)report.failures.push(`listening catalog unexpectedly small: ${raw.length}`);
for(const [l,n] of Object.entries(perLevelKept))if(n<900)report.failures.push(`listening ${l} kept only ${n} quality catalog questions`);
if(kept<raw.length*.65)report.failures.push(`listening quality gate would drop too many catalog questions: kept ${kept}/${raw.length}`);
const maxPos=Math.max(...position),sumPos=position.reduce((a,b)=>a+b,0);if(sumPos>100&&maxPos/sumPos>.55)report.failures.push(`listening correct-answer position is too biased: ${position.join(',')}`);

// Static checks that runtime gate is installed.
const listeningHtml=fs.readFileSync('listening.html','utf8');
for(const marker of ['listeningCatalogErrors','answer-length-giveaway','zhChoiceSim(correctRow.zh,r.zh)','日本語聽解挑戰 v8.2'])if(!listeningHtml.includes(marker))report.failures.push(`listening runtime QA marker missing: ${marker}`);

// -------- Mock exam runtime audit --------
const dummy=()=>({style:{},classList:{toggle(){},add(){},remove(){}},textContent:'',innerHTML:'',value:'',disabled:false,onclick:null});
const selectorMap=new Map();
const getSel=s=>{if(s==='input[name=level]:checked')return {value:'N3'};if(s==='input[name=mode]:checked')return {value:'full'};if(!selectorMap.has(s))selectorMap.set(s,dummy());return selectorMap.get(s)};
globalThis.document={querySelector:getSel,querySelectorAll(){return[]},createElement(){let _html='';return{set innerHTML(v){_html=String(v);this.textContent=_html.replace(/<[^>]*>/g,' ')},get innerHTML(){return _html},textContent:''}}};
globalThis.window=globalThis;globalThis.window.addEventListener=()=>{};
globalThis.localStorage={getItem(){return null},setItem(){},removeItem(){}};
globalThis.alert=()=>{};globalThis.confirm=()=>true;globalThis.__MOCKTEST_QA__=true;
const js=fs.readFileSync('mocktest.js','utf8');
vm.runInThisContext(js,{filename:'mocktest.js'});
const api=globalThis.__mockTestQA;if(!api)throw new Error('mock QA API missing');
await api.loadAll();
const counts=api.qaCounts();
const perLevel={};let totalChecked=0;
for(const level of ['N5','N4','N3','N2','N1']){
  const need={vocab:level==='N1'?20:20,grammar:['N1','N2','N3'].includes(level)?14:(level==='N4'?12:10),reading:['N1'].includes(level)?16:level==='N2'?15:level==='N3'?14:level==='N4'?12:10,listening:['N1','N2'].includes(level)?22:level==='N3'?20:level==='N4'?18:16};
  const stats={vocab:0,grammar:0,reading:0,listening:0,failures:0,iterations:20};
  for(let it=0;it<stats.iterations;it++){
    for(const kind of ['vocab','grammar','reading','listening']){
      const fn={vocab:api.buildVocab,grammar:api.buildGrammar,reading:api.buildReading,listening:api.buildListening}[kind];
      const qs=fn(level,need[kind]);stats[kind]+=qs.length;totalChecked+=qs.length;
      if(qs.length<need[kind])report.failures.push(`mock ${level} ${kind} underfilled on iteration ${it}: ${qs.length}/${need[kind]}`);
      for(const q of qs){const errs=api.questionQualityErrors(q);if(errs.length){stats.failures++;report.failures.push(`mock ${level} ${kind} ${q.id}: ${errs.join(',')}`)}}
    }
  }
  perLevel[level]=stats;
}
report.mock={sourceCounts:counts,generatedChecked:totalChecked,perLevel};
for(const marker of ['questionQualityErrors(q)','usage-singleton-target-leak','function buildReadingContent(level,n)','function buildListeningContent(level,n)','qualityGate(diversifyQuestions'])if(!js.includes(marker))report.failures.push(`mock runtime QA marker missing: ${marker}`);
const buildListeningText=(js.match(/function buildListening\(level,n\)\{[^\n]+/)||[])[0]||'';
if(buildListeningText.includes('buildQuickResponse'))report.failures.push('mock weak QUICK_RESPONSE questions are still active in buildListening');

fs.mkdirSync('data',{recursive:true});
fs.writeFileSync('data/listening_mock_quality_v1_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(report.failures.length)process.exit(1);
