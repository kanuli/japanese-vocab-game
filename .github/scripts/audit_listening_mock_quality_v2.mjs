import fs from 'node:fs';
import vm from 'node:vm';

const report={version:'20260822-quality2',listening:{},mock:{},failures:[]};
const norm=s=>String(s||'').normalize('NFKC').replace(/[\s　，。！？、,.!?「」『』（）()]/g,'').trim();
const chineseReady=s=>!!String(s||'').trim()&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(String(s));

// ---------- Listening: audit every original catalog row structurally ----------
const catalog=JSON.parse(fs.readFileSync('listening-original-catalog.json','utf8'));
const raw=Array.isArray(catalog.items)?catalog.items:[];
const levels=['N5','N4','N3','N2','N1'];
const perLevelRaw=Object.fromEntries(levels.map(l=>[l,0]));
const perLevelPass=Object.fromEntries(levels.map(l=>[l,0]));
const reasons=new Map();
const positions=[0,0,0,0];
let passed=0,translationRequired=0;
for(const x of raw){
  const level=String(x.level||'').toUpperCase();if(level in perLevelRaw)perLevelRaw[level]++;
  const cs=Array.isArray(x.choicesZh)?x.choicesZh.map(v=>String(v||'').trim()):[];
  const correct=String(x.correctZh||'').trim(),keys=cs.map(norm),target=norm(correct),errs=[];
  if(!x.id||!/^N[1-5]$/.test(level)||!String(x.jp||'').trim())errs.push('identity');
  if(cs.length!==4)errs.push('choice-count');
  if(cs.some(v=>!v))errs.push('empty-choice');
  if(new Set(keys).size!==4)errs.push('duplicate-choice');
  const matches=keys.filter(k=>k===target).length;if(!target||matches!==1)errs.push('answer-not-unique');
  if(cs.some(v=>!chineseReady(v)))translationRequired++;
  if(errs.length){for(const e of new Set(errs))reasons.set(e,(reasons.get(e)||0)+1);continue}
  passed++;perLevelPass[level]++;positions[keys.indexOf(target)]++;
}
report.listening={raw:raw.length,structurallyPassed:passed,structurallyRejected:raw.length-passed,perLevelRaw,perLevelPassed,translationRequiredAtSource:translationRequired,rejectReasons:Object.fromEntries(reasons),correctPositionDistribution:positions};
if(raw.length!==6690)report.failures.push(`listening expected 6690 original rows, found ${raw.length}`);
for(const l of levels)if(perLevelPass[l]<perLevelRaw[l]*.98)report.failures.push(`listening ${l} structural pass too low: ${perLevelPass[l]}/${perLevelRaw[l]}`);
if(passed<raw.length*.98)report.failures.push(`listening structural pass too low: ${passed}/${raw.length}`);
const posTotal=positions.reduce((a,b)=>a+b,0),maxPos=Math.max(...positions);if(posTotal&&maxPos/posTotal>.36)report.failures.push(`listening correct position bias: ${positions.join(',')}`);

// The browser performs Chinese repair/translation and semantic UI gating after load.
const listeningHtml=fs.readFileSync('listening.html','utf8');
for(const marker of ['日本語聽解挑戰 v8.2','function listeningCatalogErrorsV2','answer-not-unique','if(Math.max(...peers)<.18)return null','if(len<.45)return null','return shuffle(rows)']){
  if(!listeningHtml.includes(marker))report.failures.push(`listening runtime QA marker missing: ${marker}`);
}

// ---------- Mock exam runtime generation audit ----------
const dummy=()=>({style:{},classList:{toggle(){},add(){},remove(){}},textContent:'',innerHTML:'',value:'',disabled:false,onclick:null});
const selectorMap=new Map();
const getSel=s=>{if(s==='input[name=level]:checked')return {value:'N3'};if(s==='input[name=mode]:checked')return {value:'full'};if(!selectorMap.has(s))selectorMap.set(s,dummy());return selectorMap.get(s)};
globalThis.document={querySelector:getSel,querySelectorAll(){return[]},createElement(){let html='';return{set innerHTML(v){html=String(v);this.textContent=html.replace(/<[^>]*>/g,' ')},get innerHTML(){return html},textContent:''}}};
globalThis.window=globalThis;globalThis.window.addEventListener=()=>{};
globalThis.localStorage={getItem(){return null},setItem(){},removeItem(){}};
globalThis.alert=()=>{};globalThis.confirm=()=>true;globalThis.__MOCKTEST_QA__=true;
const js=fs.readFileSync('mocktest.js','utf8');
vm.runInThisContext(js,{filename:'mocktest.js'});
const api=globalThis.__mockTestQA;if(!api)throw new Error('mock QA API missing');
await api.loadAll();
const counts=api.qaCounts(),perLevel={},iterations=30;
let generatedChecked=0;
for(const level of levels){
  const need={
    vocab:20,
    grammar:level==='N5'?10:level==='N4'?12:14,
    reading:level==='N5'?10:level==='N4'?12:level==='N3'?14:level==='N2'?15:16,
    listening:level==='N5'?16:level==='N4'?18:level==='N3'?20:22
  };
  const st={iterations,vocab:0,grammar:0,reading:0,listening:0,qualityFailures:0,underfills:0};
  for(let it=0;it<iterations;it++){
    for(const kind of ['vocab','grammar','reading','listening']){
      const fn={vocab:api.buildVocab,grammar:api.buildGrammar,reading:api.buildReading,listening:api.buildListening}[kind];
      const qs=fn(level,need[kind]);st[kind]+=qs.length;generatedChecked+=qs.length;
      if(qs.length!==need[kind]){st.underfills++;report.failures.push(`mock ${level} ${kind} count ${qs.length}/${need[kind]} iteration ${it}`)}
      for(const q of qs){const errs=api.questionQualityErrors(q);if(errs.length){st.qualityFailures++;report.failures.push(`mock ${level} ${kind} ${q.id}: ${errs.join(',')}`)}}
    }
  }
  perLevel[level]=st;
}
report.mock={sourceCounts:counts,generatedChecked,perLevel};
for(const marker of ['function uniqBy(a,key)','usage-singleton-target-leak','function buildReadingContent(level,n)','function buildListeningContent(level,n)','grammarChoiceCompatible','qualityGate(diversifyQuestions']){
  if(!js.includes(marker))report.failures.push(`mock runtime QA marker missing: ${marker}`);
}
const activeListening=(js.match(/function buildListening\(level,n\)\{[^\n]+/)||[])[0]||'';
if(activeListening.includes('buildQuickResponse'))report.failures.push('mock weak QUICK_RESPONSE bank remains active');

fs.mkdirSync('data',{recursive:true});
fs.writeFileSync('data/listening_mock_quality_v2_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(report.failures.length)process.exit(1);
