import fs from 'node:fs';
import vm from 'node:vm';
function run(path,seed={}){const sandbox={console,window:{...seed},document:{querySelector:()=>null}};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path,'utf8'),sandbox,{filename:path,timeout:10000});return sandbox.window}
const files=['conversation-data-1.js','conversation-data-2.js','conversation-data-3.js','conversation-data-4.js','conversation-data-5.js','conversation-expansion.js','conversation-world-expansion.js','conversation-reference-expansion.js','conversation-gap-expansion.js','conversation-function-topup.js','conversation-quality-batch3.js','conversation-quality-batch7.js'];
let w={SITUATION_SCENES:[]};for(const f of files)w=run(f,{SITUATION_SCENES:[...(w.SITUATION_SCENES||[])]});
const scenes=w.SITUATION_SCENES||[];const rows=scenes.flatMap(s=>(s.items||[]).map((x,i)=>({...x,sceneId:s.id,itemIndex:i})));
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』【】（）()：:；;]/g,'');
const kana=/[ぁ-ゖァ-ヺ]/;const failures=[];const structure=[];
if(scenes.length!==77)failures.push(`sceneCount=${scenes.length}`);if(rows.length!==1925)failures.push(`dialogueCount=${rows.length}`);
for(const l of ['N1','N2','N3','N4','N5']){const n=rows.filter(x=>x.level===l).length;if(n!==385)failures.push(`${l} count=${n}`)}
for(const s of scenes){if((s.items||[]).length!==25)structure.push(`${s.id}: items ${(s.items||[]).length}`);for(const l of ['N1','N2','N3','N4','N5']){const n=(s.items||[]).filter(x=>x.level===l).length;if(n!==5)structure.push(`${s.id}: ${l}=${n}`)}}
for(const x of rows){if(!Array.isArray(x.lines)||x.lines.length!==2)structure.push(`${x.sceneId}/${x.itemIndex}: lines`);else for(const y of x.lines)if(!String(y.jp||'').trim()||!String(y.zh||'').trim())structure.push(`${x.sceneId}/${x.itemIndex}: blank`)}
if(structure.length)failures.push(`structureErrors=${structure.length}`);
let kanaZh=0;for(const x of rows)for(const y of x.lines||[])if(kana.test(String(y.zh||'')))kanaZh++;if(kanaZh)failures.push(`kanaZh=${kanaZh}`);
const seen=new Map();for(const x of rows){const k=norm((x.lines||[]).map(y=>y.jp).join('|'));seen.set(k,(seen.get(k)||0)+1)}const duplicatePairs=[...seen.entries()].filter(([,n])=>n>1);const duplicateCount=duplicatePairs.reduce((n,[,v])=>n+v-1,0);if(duplicateCount)failures.push(`exactDuplicatePairs=${duplicateCount}`);
const txt=(x)=>String(x.lines?.[0]?.jp||'');
const patternCounts={
 worldN5:rows.filter(x=>x.level==='N5'&&/はどこでできますか。$/.test(txt(x))).length,
 worldN4:rows.filter(x=>x.level==='N4'&&/には何が必要ですか。$/.test(txt(x))).length,
 worldN3:rows.filter(x=>x.level==='N3'&&/について確認したいのですが、「.+」という状況でも大丈夫ですか。$/.test(txt(x))).length,
 worldN2:rows.filter(x=>x.level==='N2'&&/を進めるにはどうすればいいですか。$/.test(txt(x))).length,
 worldN1:rows.filter(x=>x.level==='N1'&&/通常の方法以外で対応していただくことは可能でしょうか。$/.test(txt(x))).length,
 referenceN4:rows.filter(x=>x.level==='N4'&&/何を準備したらいいですか。$/.test(txt(x))).length,
 referenceN3:rows.filter(x=>x.level==='N3'&&/について確認したいのですが、どうすればいいですか。$/.test(txt(x))).length,
 referenceN2:rows.filter(x=>x.level==='N2'&&/を進める上で、別の方法はありますか。$/.test(txt(x))).length,
 referenceN1:rows.filter(x=>x.level==='N1'&&/例外的な扱いをご検討いただくことは可能でしょうか。$/.test(txt(x))).length
};
for(const [k,v] of Object.entries(patternCounts)){const cap=(k==='worldN5'||k==='worldN4')?40:12;if(v>cap)failures.push(`${k} concentration=${v}>${cap}`)}
const awkward=/確認を進めるには|相談を進めるには|予約を進めるには|変更を進めるには|トラブルを進めるには|利用を進めるには|説明を進めるには|書類を進めるには|購入を進めるには|支援を進めるには|違いを進めるには/;const awkwardCount=rows.filter(x=>awkward.test(txt(x))).length;if(awkwardCount)failures.push(`awkward generic 進める templates=${awkwardCount}`);
const avg=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;const depth={};for(const l of ['N1','N2','N3','N4','N5']){const a=rows.filter(x=>x.level===l);depth[l]=+avg(a.map(x=>norm((x.lines||[]).map(y=>y.jp).join('')).length)).toFixed(1)}if(!(depth.N1>depth.N2&&depth.N2>depth.N3&&depth.N3>depth.N4&&depth.N4>depth.N5))failures.push(`depth progression=${JSON.stringify(depth)}`);
function maxSuffix(level,index,len=18){const m=new Map();for(const x of rows.filter(r=>r.level===level)){const z=[...norm(x.lines?.[index]?.jp||'')].slice(-len).join('');if(z)m.set(z,(m.get(z)||0)+1)}return [...m.entries()].sort((a,b)=>b[1]-a[1])[0]||['',0]}
const suffixMax={};for(const l of ['N1','N2','N3','N4','N5'])suffixMax[l]={A:maxSuffix(l,0),B:maxSuffix(l,1)};if(suffixMax.N1.A[1]>45)failures.push(`N1 first-line suffix concentration=${suffixMax.N1.A[1]}`);
const report={version:'2026-08-27-full-conversation-batch7-v1',sceneCount:scenes.length,dialogueCount:rows.length,structureErrors:structure.length,kanaZhCount:kanaZh,exactDuplicatePairs:duplicateCount,patternCounts,awkwardGenericProgressionTemplates:awkwardCount,depth,suffixMax,batch7Meta:w.CONVERSATION_QUALITY_BATCH7||{},failures,passed:failures.length===0};fs.mkdirSync('data',{recursive:true});fs.writeFileSync('data/full_conversation_batch7_report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exit(1);
