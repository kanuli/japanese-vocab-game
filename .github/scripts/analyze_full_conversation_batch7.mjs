import fs from 'node:fs';
import vm from 'node:vm';

function run(path,seed={}){const sandbox={console,window:{...seed},document:{querySelector:()=>null}};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path,'utf8'),sandbox,{filename:path,timeout:10000});return sandbox.window}
const files=['conversation-data-1.js','conversation-data-2.js','conversation-data-3.js','conversation-data-4.js','conversation-data-5.js','conversation-expansion.js','conversation-world-expansion.js','conversation-reference-expansion.js','conversation-gap-expansion.js','conversation-function-topup.js','conversation-quality-batch3.js'];
let w={SITUATION_SCENES:[]};for(const f of files)w=run(f,{SITUATION_SCENES:[...(w.SITUATION_SCENES||[])]});
const scenes=w.SITUATION_SCENES||[];
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』【】（）()：:；;]/g,'');
const kana=/[ぁ-ゖァ-ヺ]/;
const rows=scenes.flatMap(s=>(s.items||[]).map((x,i)=>({...x,sceneId:s.id,sceneZh:s.zh,itemIndex:i,source:s.coverageGapExpansion?'gap':s.referenceExpansion?'reference':s.worldExpansion?'world':s.expansion?'expansion':'base'})));
const counts={sceneCount:scenes.length,dialogueCount:rows.length,byLevel:{},bySource:{}};
for(const l of ['N1','N2','N3','N4','N5'])counts.byLevel[l]=rows.filter(x=>x.level===l).length;
for(const x of rows)counts.bySource[x.source]=(counts.bySource[x.source]||0)+1;
const structure=[];for(const s of scenes){if((s.items||[]).length!==25)structure.push({scene:s.id,error:`items=${(s.items||[]).length}`});for(const l of ['N1','N2','N3','N4','N5']){const n=(s.items||[]).filter(x=>x.level===l).length;if(n!==5)structure.push({scene:s.id,error:`${l}=${n}`})}}
for(const x of rows){if(!Array.isArray(x.lines)||x.lines.length!==2)structure.push({scene:x.sceneId,index:x.itemIndex,error:'lines!=2'});else for(const [i,line] of x.lines.entries())if(!String(line.jp||'').trim()||!String(line.zh||'').trim())structure.push({scene:x.sceneId,index:x.itemIndex,line:i,error:'blank jp/zh'})}
let kanaZh=0;const kanaSamples=[];for(const x of rows)for(const line of x.lines||[])if(kana.test(String(line.zh||''))){kanaZh++;if(kanaSamples.length<20)kanaSamples.push({scene:x.sceneId,level:x.level,zh:line.zh})}
const pairCount=new Map();for(const x of rows){const k=norm((x.lines||[]).map(y=>y.jp).join('|'));pairCount.set(k,(pairCount.get(k)||0)+1)}
const duplicatePairs=[...pairCount.entries()].filter(([,n])=>n>1).sort((a,b)=>b[1]-a[1]).slice(0,30).map(([key,count])=>({count,key}));
const exactDupCount=[...pairCount.values()].reduce((n,v)=>n+Math.max(0,v-1),0);
function suffixStats(level,lineIndex,len=18){const m=new Map();for(const x of rows.filter(r=>r.level===level)){const t=norm(x.lines?.[lineIndex]?.jp||'');if(!t)continue;const k=[...t].slice(-len).join('');m.set(k,(m.get(k)||0)+1)}return [...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,15).map(([suffix,count])=>({suffix,count}))}
const suffixes={};for(const l of ['N1','N2','N3','N4','N5'])suffixes[l]={A:suffixStats(l,0),B:suffixStats(l,1)};
const legacy={
 N5:['をお願いします','はいわかりました'],
 N4:['何を準備したらいいですか'],
 N3:['について確認したいのですがどうすればいいですか','どうしたらいいですか'],
 N2:['を進める上で別の方法はありますか','通常の方法が難しい場合'],
 N1:['例外的な扱いをご検討いただくことは可能でしょうか','実情に即した対応をご検討いただけないでしょうか']
};
const legacyCounts={};for(const [l,ps] of Object.entries(legacy)){legacyCounts[l]={};for(const p of ps)legacyCounts[l][p]=rows.filter(x=>x.level===l&&norm((x.lines||[]).map(y=>y.jp).join(' ')).includes(norm(p))).length}
const avg=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;const jpLen=s=>[...norm(s)].length;const depth={};for(const l of ['N1','N2','N3','N4','N5']){const a=rows.filter(x=>x.level===l);depth[l]={count:a.length,avgDialogueChars:+avg(a.map(x=>jpLen((x.lines||[]).map(y=>y.jp).join('')))).toFixed(1)}}
const report={version:'2026-08-27-full-conversation-batch7-preflight-v1',files,counts,structureErrors:structure.length,structureSamples:structure.slice(0,30),kanaZhCount:kanaZh,kanaSamples,exactDuplicatePairs:exactDupCount,duplicatePairFamilies:duplicatePairs,legacyCounts,suffixes,depth};
fs.mkdirSync('data',{recursive:true});fs.writeFileSync('data/full_conversation_batch7_preflight.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({scenes:scenes.length,dialogues:rows.length,structure:structure.length,kanaZh,exactDupCount,legacyCounts,depth},null,2));
