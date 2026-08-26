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

const gwBase=runFile('grammar-reference-expansion.js');
const gw=runFile('grammar-gap-expansion.js',{REFERENCE_GRAMMAR_EXPANSION:[...(gwBase.REFERENCE_GRAMMAR_EXPANSION||[])]});
const grammar=gw.REFERENCE_GRAMMAR_EXPANSION||[];
const grammarPerLevel={};
for(const l of levels)grammarPerLevel[l]=grammar.filter(x=>x.level===l).length;
const grammarSentences=new Set();
for(const [i,x] of grammar.entries()){
  if(!levels.includes(x.level))failures.push(`grammar ${i}: bad level`);
  if(!String(x.q||'').includes('＿＿'))failures.push(`grammar ${i}: missing blank`);
  if(!Array.isArray(x.choices)||x.choices.length!==4)failures.push(`grammar ${i}: choice count`);
  if(new Set((x.choices||[]).map(norm)).size!==4)failures.push(`grammar ${i}: duplicate choices`);
  if(!(x.choices||[]).includes(x.a))failures.push(`grammar ${i}: answer missing from choices`);
  if(!String(x.zh||'').trim()||!String(x.meaning||'').trim()||!String(x.exp||'').trim())failures.push(`grammar ${i}: missing zh/meaning/explanation`);
  const restored=String(x.q||'').replace('＿＿',String(x.a||''));
  if(restored.includes('＿＿'))failures.push(`grammar ${i}: unresolved blank`);
  const sk=`${x.level}|${norm(restored)}`;if(grammarSentences.has(sk))failures.push(`grammar ${i}: duplicate restored sentence`);grammarSentences.add(sk);
}
if((grammarPerLevel.N4||0)<30)failures.push('grammar: N4 targeted passive top-up missing');

const lwBase=runFile('listening-reference-expansion.js');
const lw=runFile('listening-gap-expansion.js',{REFERENCE_LISTENING_EXPANSION:[...(lwBase.REFERENCE_LISTENING_EXPANSION||[])]});
const listening=lw.REFERENCE_LISTENING_EXPANSION||[];
const listeningPerLevel={}, listeningTypeCounts={};
for(const l of levels){
  const rows=listening.filter(x=>x.level===l);
  listeningPerLevel[l]=rows.length;
  listeningTypeCounts[l]={};
  for(const x of rows){const t=String(x.typeZh||x.type||'未分類');listeningTypeCounts[l][t]=(listeningTypeCounts[l][t]||0)+1}
}
const listeningSentences=new Set(), listeningIds=new Set();
const badJapanese=[/受け取りて/,/送りて/,/買い物をできる/,/より速く[^。]*ます[。]/];
for(const [i,x] of listening.entries()){
  if(!levels.includes(x.level))failures.push(`listening ${i}: bad level`);
  if(!String(x.jp||'').trim())failures.push(`listening ${i}: missing jp`);
  if(!Array.isArray(x.choicesZh)||x.choicesZh.length!==4)failures.push(`listening ${i}: choice count`);
  if(new Set((x.choicesZh||[]).map(norm)).size!==4)failures.push(`listening ${i}: duplicate choices`);
  if((x.choicesZh||[]).filter(v=>norm(v)===norm(x.correctZh)).length!==1)failures.push(`listening ${i}: answer not unique`);
  if(/[A-Za-z]/.test(String(x.correctZh||'')))failures.push(`listening ${i}: English in correctZh`);
  if(badJapanese.some(r=>r.test(String(x.jp||''))))failures.push(`listening ${i}: suspicious generated inflection: ${x.jp}`);
  const sk=`${x.level}|${norm(x.jp)}`;if(listeningSentences.has(sk))failures.push(`listening ${i}: duplicate Japanese sentence`);listeningSentences.add(sk);
  if(x.id){if(listeningIds.has(x.id))failures.push(`listening ${i}: duplicate id ${x.id}`);listeningIds.add(x.id)}
}
const targetedTypes={
 N5:['人物關係','地點理解','數量理解','資訊理解','交通理解','時間理解','行動理解'],
 N4:['順序理解','目的理解','指示理解','準備理解','方向理解','可能性理解','特徵理解','原因結果','條件理解'],
 N3:['變更理解','習慣理解','課題理解','變化理解','資訊來源','意圖理解','決定理解','順序理解','範圍理解','理由理解','細節理解'],
 N2:['程序理解','變化理解','課題理解','原因結果','原因推論','指示理解','否定推論','建議理解','趨勢理解','風險推論','範圍理解'],
 N1:['正式公告','論理理解','範圍理解','判斷理解','時間關係','展開理解','逆接理解','評價理解','結論推論']
};
if(listening.length<230)failures.push(`listening: unique expansion pool too small (${listening.length})`);
for(const l of levels){
  if((listeningPerLevel[l]||0)<38)failures.push(`listening: ${l} unique expansion pool too small`);
  for(const t of targetedTypes[l])if((listeningTypeCounts[l]?.[t]||0)<3)failures.push(`listening: ${l}/${t} still under-covered`);
}

const cwBase=runFile('conversation-reference-expansion.js',{SITUATION_SCENES:[]});
const cw=runFile('conversation-gap-expansion.js',{SITUATION_SCENES:[...(cwBase.SITUATION_SCENES||[])]});
const scenes=cw.SITUATION_SCENES||[];
const dialogueCount=scenes.reduce((n,s)=>n+(s.items||[]).length,0);
const sceneIds=new Set();
for(const s of scenes){
  if(!s.id||!s.zh||!s.jp)failures.push(`conversation: incomplete scene metadata ${s.id||'?'}`);
  if(sceneIds.has(s.id))failures.push(`conversation: duplicate scene id ${s.id}`);sceneIds.add(s.id);
  if((s.items||[]).length!==25)failures.push(`conversation ${s.id}: expected 25 items`);
  for(const l of levels)if((s.items||[]).filter(x=>x.level===l).length!==5)failures.push(`conversation ${s.id}: ${l} expected 5 items`);
  for(const [i,x] of (s.items||[]).entries()){
    if(!x.situation)failures.push(`conversation ${s.id}/${i}: missing situation`);
    if(!Array.isArray(x.lines)||x.lines.length!==2)failures.push(`conversation ${s.id}/${i}: expected 2 lines`);
    for(const ln of x.lines||[])if(!ln.jp||!ln.zh)failures.push(`conversation ${s.id}/${i}: missing jp/zh line`);
  }
}
for(const id of ['dietary-restrictions','cooking-substitution','weather-warning','outdoor-nature','japanese-learning','culture-manners'])if(!sceneIds.has(id))failures.push(`conversation: targeted scene missing ${id}`);

const grammarHtml=fs.readFileSync('grammar.html','utf8'), listeningHtml=fs.readFileSync('listening.html','utf8'), conversationHtml=fs.readFileSync('conversation.html','utf8'), mockHtml=fs.readFileSync('mocktest.html','utf8'), mockJs=fs.readFileSync('mocktest.js','utf8');
const pageChecks={
  grammar: grammarHtml.includes('grammar-reference-expansion.js')&&grammarHtml.includes('grammar-gap-expansion.js'),
  listening: listeningHtml.includes('listening-reference-expansion.js')&&listeningHtml.includes('listening-gap-expansion.js'),
  conversation: conversationHtml.includes('conversation-reference-expansion.js')&&conversationHtml.includes('conversation-gap-expansion.js'),
  mocktest: mockHtml.includes('grammar-reference-expansion.js')&&mockHtml.includes('grammar-gap-expansion.js')&&mockJs.includes('mock-ref-grammar')
};
for(const [k,v] of Object.entries(pageChecks))if(!v)failures.push(`integration: ${k} not wired`);

const report={
  version:'2026-08-27-gap-v2',
  grammar:{count:grammar.length,perLevel:grammarPerLevel,targetedGap:'N4 passive'},
  listening:{count:listening.length,perLevel:listeningPerLevel,typeCounts:listeningTypeCounts,targetedGap:'underrepresented listening subtypes',note:'Candidate templates are sentence-deduplicated; QA requires unique subtype coverage rather than artificial count balance.'},
  conversation:{newScenes:scenes.length,newDialogues:dialogueCount,perScene:25,targetedGap:'JF food + nature/environment + language/culture'},
  pageChecks,
  failures,
  passed:failures.length===0
};
fs.mkdirSync('data',{recursive:true});
fs.writeFileSync('data/reference_expansion_quality_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(failures.length)process.exit(1);
