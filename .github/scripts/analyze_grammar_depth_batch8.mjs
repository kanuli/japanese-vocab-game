import fs from 'node:fs';
import vm from 'node:vm';
function run(path,seed={}){const sandbox={console,window:{...seed}};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path,'utf8'),sandbox,{filename:path,timeout:5000});return sandbox.window}
let w=run('grammar-reference-expansion.js');w=run('grammar-gap-expansion.js',{REFERENCE_GRAMMAR_EXPANSION:[...(w.REFERENCE_GRAMMAR_EXPANSION||[])]});
const rows=w.REFERENCE_GRAMMAR_EXPANSION||[];
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　]/g,'');
const jpLen=s=>[...norm(s).replace(/[。、，,.！？!?「」『』【】（）()]/g,'')].length;
const avg=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;
const ADV=[/ものの/g,/とはいえ/g,/にもかかわらず/g,/わけでは/g,/にしては/g,/ながらも/g,/一方/g,/上で/g,/次第/g,/かねない/g,/ざるを得/g,/にほかなら/g,/にすぎな/g,/ものなら/g,/とあって/g,/を踏まえ/g,/限り/g,/に伴/g,/に応じ/g,/に基づ/g,/をめぐ/g,/に際し/g,/に先立/g,/を余儀なく/g,/に至/g,/にかかわらず/g,/に即し/g];
const MODAL=[/べき/g,/はず/g,/わけ/g,/恐れ/g,/かね/g,/ざる/g,/に違いない/g,/とは限らない/g,/ないことはない/g,/ことにな/g,/ように/g,/つもり/g,/かもしれ/g];
const CONNECT=[/ので/g,/ため/g,/けれど/g,/が/g,/なら/g,/ても/g,/場合/g,/ところ/g,/ながら/g,/一方/g,/ものの/g,/にもかかわらず/g,/から/g,/上で/g,/のに/g,/として/g,/について/g,/に対して/g,/によって/g,/という/g,/ことから/g];
function hits(s,rs){let n=0;for(const r0 of rs){const r=new RegExp(r0.source,r0.flags);n+=(String(s).match(r)||[]).length}return n}
function metrics(x){const sentence=String(x.q||'').replace('＿＿',String(x.a||''));const full=[sentence,x.grammar,x.exp].join(' ');const advanced=hits(full,ADV),modal=hits(full,MODAL),connect=hits(sentence,CONNECT),commas=(sentence.match(/[、，,]/g)||[]).length,clauses=1+commas+connect;const score=advanced*3+modal*1.5+connect*1.25+Math.min(3,commas)*.5;return{sentence,chars:jpLen(sentence),advanced,modal,connect,commas,clauses,score:+score.toFixed(2)}}
const byLevel={};for(const l of ['N1','N2','N3','N4','N5']){const a=rows.filter(x=>x.level===l),ms=a.map(metrics);byLevel[l]={count:a.length,avgChars:+avg(ms.map(x=>x.chars)).toFixed(1),avgAdvanced:+avg(ms.map(x=>x.advanced)).toFixed(2),avgModal:+avg(ms.map(x=>x.modal)).toFixed(2),avgConnect:+avg(ms.map(x=>x.connect)).toFixed(2),avgClauses:+avg(ms.map(x=>x.clauses)).toFixed(2),avgComplexityScore:+avg(ms.map(x=>x.score)).toFixed(2),advancedShare:+(100*ms.filter(x=>x.advanced>0).length/Math.max(1,ms.length)).toFixed(1),structuralErrors:a.filter(x=>!Array.isArray(x.choices)||x.choices.length!==4||new Set(x.choices.map(norm)).size!==4||!x.choices.includes(x.a)).length};}
const n2=rows.filter(x=>x.level==='N2').map(x=>({id:x.id,grammar:x.grammar,q:x.q,...metrics(x)}));const n3=rows.filter(x=>x.level==='N3').map(x=>({id:x.id,grammar:x.grammar,q:x.q,...metrics(x)}));
const report={version:'2026-08-27-grammar-depth-batch8-preflight-v1',count:rows.length,byLevel,n2Lowest:[...n2].sort((a,b)=>a.score-b.score).slice(0,10),n3Highest:[...n3].sort((a,b)=>b.score-a.score).slice(0,10),note:'Complexity is diagnostic, combining advanced construction markers, modality, connective/subordination signals and clause segmentation; sentence length alone is not a JLPT-level proxy.'};fs.mkdirSync('data',{recursive:true});fs.writeFileSync('data/grammar_depth_batch8_preflight.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({count:rows.length,byLevel},null,2));
