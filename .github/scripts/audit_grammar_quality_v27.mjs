import fs from 'node:fs';
import vm from 'node:vm';

const HTML = 'grammar.html';
const REPORT = 'data/grammar_quality_v27_runtime_report.json';
const html = fs.readFileSync(HTML, 'utf8');
const m = html.match(/<script>\s*(\(\(\)=>\{"use strict";[\s\S]*?\}\)\(\);)\s*<\/script>/);
if (!m) throw new Error('Cannot locate grammar game inline script');
let js = m[1];
const init = 'render();Promise.allSettled([loadWeb(),initFurigana()]).then(()=>render());';
if (!js.includes(init)) throw new Error('Cannot locate grammar initialization marker');
js = js.replace(init, 'globalThis.__grammarQA={generateFromPoints,qualityGate,questionQualityErrors,BUILTIN};');

const dummy = new Proxy({
  style: {}, classList: {toggle(){}, add(){}, remove(){}},
  querySelector(){ return dummy; }, querySelectorAll(){ return []; },
  setAttribute(){}, removeAttribute(){}, appendChild(){}, focus(){}, click(){},
  disabled: false, value: '', checked: false, files: [], innerHTML: '', textContent: ''
}, {
  get(target, prop) { return prop in target ? target[prop] : null; },
  set(target, prop, value) { target[prop] = value; return true; }
});

globalThis.document = {
  querySelector(){ return dummy; },
  querySelectorAll(){ return []; },
  addEventListener(){},
  createElement(){ return dummy; }
};
globalThis.localStorage = {getItem(){ return null; }, setItem(){}, removeItem(){}};
globalThis.alert = ()=>{};
if (!('location' in globalThis)) globalThis.location = {href: 'https://example.invalid/grammar.html'};
globalThis.kuromoji = undefined;
if (!globalThis.URL) globalThis.URL = class URL {};
if (!globalThis.URL.createObjectURL) globalThis.URL.createObjectURL = ()=>'';
if (!globalThis.URL.revokeObjectURL) globalThis.URL.revokeObjectURL = ()=>{};

vm.runInThisContext(js, {filename: 'grammar-inline.js'});
const api = globalThis.__grammarQA;
if (!api) throw new Error('Grammar QA API was not exported');

const files = {
  N5: 'grammar_ja_N5_full_alphabetical_0001.json',
  N4: 'grammar_ja_N4_full_alphabetical_0001.json',
  N3: 'grammar_ja_N3_full_alphabetical_0001.json',
  N2: 'grammar_ja_N2_full_alphabetical_0001.json',
  N1: 'grammar_ja_N1_full_alphabetical_0001.json'
};
const base = 'https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/';
const countOcc = (s,p)=>p ? String(s).split(p).length-1 : 0;
const failures = [];
const perLevel = {};
let all = [];
let douiuSourcePoints = 0;
let douiuGenerated = [];

function assertQuestion(q) {
  const errs = api.questionQualityErrors(q);
  if (errs.length) failures.push({id:q.id, errors:errs});
  const choices = q.choices || [];
  if (choices.length !== 4 || new Set(choices).size !== 4) failures.push({id:q.id, errors:['choice-uniqueness-runtime']});
  if (choices.filter(x=>x===q.a).length !== 1) failures.push({id:q.id, errors:['answer-uniqueness-runtime']});
  if ((q.mode||'fill') === 'fill') {
    if (countOcc(q.q,'＿＿') !== 1) failures.push({id:q.id, errors:['blank-count-runtime']});
    if (q.sentence && q.q.replace('＿＿', q.a) !== q.sentence) failures.push({id:q.id, errors:['fill-reconstruction-runtime']});
  } else {
    if (!q.usageAnchor) failures.push({id:q.id, errors:['missing-usage-anchor-runtime']});
    if (!q.usageHint) failures.push({id:q.id, errors:['missing-usage-hint-runtime']});
    if (q.usageAnchor && choices.some(x=>countOcc(x,q.usageAnchor)!==1)) failures.push({id:q.id, errors:['usage-answer-leak-runtime']});
  }
}

for (const [level,file] of Object.entries(files)) {
  const r = await fetch(base + file);
  if (!r.ok) throw new Error(`${level} source fetch failed: HTTP ${r.status}`);
  const pts = await r.json();
  if (!Array.isArray(pts) || pts.length < 20) throw new Error(`${level} source data invalid`);
  douiuSourcePoints += pts.filter(pt=>String(pt.title||'').includes('どういう')).length;
  const generated = api.generateFromPoints(pts, level);
  const gated = api.qualityGate(generated, `audit-${level}`);
  if (gated.length !== generated.length) failures.push({id:`${level}-gate`, errors:['generator-produced-question-rejected-by-own-gate'], generated:generated.length, gated:gated.length});
  gated.forEach(assertQuestion);
  const fill = gated.filter(q=>q.mode==='fill').length;
  const usage = gated.filter(q=>q.mode==='usage').length;
  perLevel[level] = {sourceGrammarPoints:pts.length, generated:gated.length, fill, usage};
  douiuGenerated.push(...gated.filter(q=>String(q.grammar||'').includes('どういう')));
  all.push(...gated);
}

// Explicit regression for the user's reported failure.
for (const q of douiuGenerated.filter(q=>q.mode==='usage')) {
  if (!q.usageAnchor || q.choices.some(x=>countOcc(x,q.usageAnchor)!==1)) {
    failures.push({id:q.id, errors:['douiu-regression-failed'], grammar:q.grammar, anchor:q.usageAnchor, choices:q.choices});
  }
}

// No usage question may have only one option containing the anchor.
const usageLeakCount = all.filter(q=>q.mode==='usage' && q.usageAnchor && q.choices.filter(x=>countOcc(x,q.usageAnchor)===1).length!==4).length;
if (usageLeakCount) failures.push({id:'global-usage-leak', errors:['one-option-target-token-leak'], count:usageLeakCount});

const builtinFailures = [];
for (const q of api.BUILTIN) {
  const errs = api.questionQualityErrors(q);
  if (errs.length) builtinFailures.push({id:q.id, errors:errs});
}
if (builtinFailures.length) failures.push({id:'built-in-bank', errors:['built-in-runtime-failure'], rows:builtinFailures});

const report = {
  version: '2.7',
  source: 'Hanabira N1-N5 live JSON',
  perLevel,
  totals: {
    webGeneratedAndChecked: all.length,
    fill: all.filter(q=>q.mode==='fill').length,
    usage: all.filter(q=>q.mode==='usage').length,
    builtInChecked: api.BUILTIN.length,
    failures: failures.length,
    usageTargetLeakFailures: usageLeakCount
  },
  douiuRegression: {
    sourceGrammarPoints: douiuSourcePoints,
    generatedQuestions: douiuGenerated.length,
    generatedUsageQuestions: douiuGenerated.filter(q=>q.mode==='usage').length,
    allGeneratedUsageChoicesContainSameAnchor: douiuGenerated.filter(q=>q.mode==='usage').every(q=>q.usageAnchor && q.choices.every(x=>countOcc(x,q.usageAnchor)===1))
  },
  failures
};
fs.mkdirSync('data', {recursive:true});
fs.writeFileSync(REPORT, JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if (failures.length) process.exit(1);
