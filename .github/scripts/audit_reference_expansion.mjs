import fs from 'node:fs';
import vm from 'node:vm';

function runFile(path, seed={}){
  const code=fs.readFileSync(path,'utf8');
  const sandbox={console,window:{...seed},document:{querySelector:()=>null}};
  vm.createContext(sandbox);
  vm.runInContext(code,sandbox,{filename:path,timeout:5000});
  return sandbox.window;
}

const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』【】（）()]/g,'');
const levels=['N1','N2','N3','N4','N5'];
const failures=[];

const gw=runFile('grammar-reference-expansion.js');
const grammar=gw.REFERENCE_GRAMMAR_EXPANSION||[];
const grammarPerLevel={};
for(const l of levels)grammarPerLevel[l]=grammar.filter(x=>x.level===l).length;
for(const [i,x] of grammar.entries()){
  if(!levels.includes(x.level))failures.push(`grammar ${i}: bad level`);
  if(!String(x.q||'').includes('＿＿'))failures.push(`grammar ${i}: missing blank`);
  if(!Array.isArray(x.choices)||x.choices.length!==4)failures.push(`grammar ${i}: choice count`);
  if(new Set((x.choices||[]).map(norm)).size!==4)failures.push(`grammar ${i}: duplicate choices`);
  if(!(x.choices||[]).includes(x.a))failures.push(`grammar ${i}: answer missing from choices`);
  if(!String(x.zh||'').trim()||!String(x.meaning||'').trim()||!String(x.exp||'').trim())failures.push(`grammar ${i}: missing zh/meaning/explanation`);
  const restored=String(x.q||'').replace('＿＿',String(x.a||''));
  if(restored.includes('＿＿'))failures.push(`grammar ${i}: unresolved blank`);
}

const lw=runFile('listening-reference-expansion.js');
const listening=lw.REFERENCE_LISTENING_EXPANSION||[];
const listeningPerLevel={};
for(const l of levels)listeningPerLevel[l]=listening.filter(x=>x.level===l).length;
for(const [i,x] of listening.entries()){
  if(!levels.includes(x.level))failures.push(`listening ${i}: bad level`);
  if(!String(x.jp||'').trim())failures.push(`listening ${i}: missing jp`);
  if(!Array.isArray(x.choicesZh)||x.choicesZh.length!==4)failures.push(`listening ${i}: choice count`);
  if(new Set((x.choicesZh||[]).map(norm)).size!==4)failures.push(`listening ${i}: duplicate choices`);
  if((x.choicesZh||[]).filter(v=>norm(v)===norm(x.correctZh)).length!==1)failures.push(`listening ${i}: answer not unique`);
  if(/[A-Za-z]/.test(String(x.correctZh||'')))failures.push(`listening ${i}: English in correctZh`);
}
if(new Set(Object.values(listeningPerLevel)).size!==1)failures.push('listening: per-level expansion is not balanced');

const cw=runFile('conversation-reference-expansion.js',{SITUATION_SCENES:[]});
const scenes=cw.SITUATION_SCENES||[];
const dialogueCount=scenes.reduce((n,s)=>n+(s.items||[]).length,0);
for(const s of scenes){
  if(!s.id||!s.zh||!s.jp)failures.push(`conversation: incomplete scene metadata ${s.id||'?'}`);
  if((s.items||[]).length!==25)failures.push(`conversation ${s.id}: expected 25 items`);
  for(const l of levels){
    if((s.items||[]).filter(x=>x.level===l).length!==5)failures.push(`conversation ${s.id}: ${l} expected 5 items`);
  }
  for(const [i,x] of (s.items||[]).entries()){
    if(!x.situation)failures.push(`conversation ${s.id}/${i}: missing situation`);
    if(!Array.isArray(x.lines)||x.lines.length!==2)failures.push(`conversation ${s.id}/${i}: expected 2 lines`);
    for(const ln of x.lines||[])if(!ln.jp||!ln.zh)failures.push(`conversation ${s.id}/${i}: missing jp/zh line`);
  }
}

const pageChecks={
  grammar: fs.readFileSync('grammar.html','utf8').includes('grammar-reference-expansion.js'),
  listening: fs.readFileSync('listening.html','utf8').includes('listening-reference-expansion.js'),
  conversation: fs.readFileSync('conversation.html','utf8').includes('conversation-reference-expansion.js'),
  mocktest: fs.readFileSync('mocktest.html','utf8').includes('grammar-reference-expansion.js') && fs.readFileSync('mocktest.js','utf8').includes('mock-ref-grammar')
};
for(const [k,v] of Object.entries(pageChecks))if(!v)failures.push(`integration: ${k} not wired`);

const report={
  version:'2026-08-26-v1',
  grammar:{count:grammar.length,perLevel:grammarPerLevel},
  listening:{count:listening.length,perLevel:listeningPerLevel},
  conversation:{newScenes:scenes.length,newDialogues:dialogueCount,perScene:25},
  pageChecks,
  failures,
  passed:failures.length===0
};
fs.mkdirSync('data',{recursive:true});
fs.writeFileSync('data/reference_expansion_quality_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(failures.length)process.exit(1);
