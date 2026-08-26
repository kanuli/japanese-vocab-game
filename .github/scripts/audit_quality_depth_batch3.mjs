import fs from 'node:fs';
import vm from 'node:vm';

function run(path,seed={}){const sandbox={console,window:{...seed},document:{querySelector:()=>null}};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path,'utf8'),sandbox,{filename:path,timeout:5000});return sandbox.window}
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』【】（）()：:；;]/g,'');
const jpLen=s=>[...String(s??'').replace(/[\s　。、，,.！？!?「」『』【】（）()]/g,'')].length;
const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0;
const failures=[];

// Grammar structural depth: representative higher-level items should be denser than beginner items.
const g0=run('grammar-reference-expansion.js');
const g1=run('grammar-gap-expansion.js',{REFERENCE_GRAMMAR_EXPANSION:[...(g0.REFERENCE_GRAMMAR_EXPANSION||[])]});
const grammar=g1.REFERENCE_GRAMMAR_EXPANSION||[];
const grammarDepth={};
for(const l of ['N1','N2','N3','N4','N5']){const rows=grammar.filter(x=>x.level===l);grammarDepth[l]={count:rows.length,avgSentenceChars:+avg(rows.map(x=>jpLen(String(x.q||'').replace('＿＿',String(x.a||''))))).toFixed(1),choiceErrors:rows.filter(x=>!Array.isArray(x.choices)||x.choices.length!==4||new Set(x.choices.map(norm)).size!==4||!x.choices.includes(x.a)).length}}
for(const [l,v] of Object.entries(grammarDepth))if(v.choiceErrors)failures.push(`grammar ${l}: choice structure errors ${v.choiceErrors}`);
if(grammarDepth.N1.avgSentenceChars<=grammarDepth.N5.avgSentenceChars+5)failures.push('grammar: N1 sentence depth not clearly above N5');
if(grammarDepth.N2.avgSentenceChars<=grammarDepth.N4.avgSentenceChars)failures.push('grammar: N2 sentence depth not above N4');

// Listening: load the full original expansion chain plus batch 3 distractor redesign.
let lw=run('listening-reference-expansion.js');
for(const f of ['listening-gap-expansion.js','listening-gap-topup.js','listening-gap-topup-batch2.js','listening-quality-batch3.js'])lw=run(f,{REFERENCE_LISTENING_EXPANSION:[...(lw.REFERENCE_LISTENING_EXPANSION||[])]});
const listening=lw.REFERENCE_LISTENING_EXPANSION||[];
const batch2=listening.filter(x=>/^gap-b2-/.test(String(x.id||'')));
const extremeMarkers=['一定','完全','永遠','絕對','必定','永久','一概'];
function grams(s){const c=[...String(s||'').replace(/[^\u3400-\u9fff]/g,'')],r=new Set();for(let i=0;i<c.length-1;i++)r.add(c[i]+c[i+1]);return r}
function jac(a,b){const A=grams(a),B=grams(b);let n=0;for(const x of A)if(B.has(x))n++;return n/Math.max(1,A.size+B.size-n)}
let extremeWrong=0,totalWrong=0,nearMissFailures=0,lengthFailures=0,qualityTagged=0;
const listeningDepth={};
for(const l of ['N1','N2','N3','N4']){const rows=batch2.filter(x=>x.level===l);listeningDepth[l]={count:rows.length,avgSentenceChars:+avg(rows.map(x=>jpLen(x.jp))).toFixed(1)}}
for(const x of batch2){
 if(x.qualityDepthBatch3)qualityTagged++;
 const wrong=(x.choicesZh||[]).filter(v=>norm(v)!==norm(x.correctZh));
 if(wrong.length!==3){failures.push(`listening ${x.id}: expected 3 distractors`);continue}
 const sims=wrong.map(w=>jac(x.correctZh,w)).sort((a,b)=>b-a);
 if((sims[1]||0)<0.12)nearMissFailures++;
 for(const w of wrong){totalWrong++;if(extremeMarkers.some(k=>String(w).includes(k)))extremeWrong++;const ratio=[...String(w)].length/Math.max(1,[...String(x.correctZh)].length);if(ratio<0.55||ratio>1.75)lengthFailures++}
}
const extremeRate=totalWrong?extremeWrong/totalWrong:1;
if(batch2.length!==28)failures.push(`listening: expected 28 batch2 targets, got ${batch2.length}`);
if(qualityTagged!==batch2.length)failures.push(`listening: only ${qualityTagged}/${batch2.length} batch2 items received quality-depth patch`);
if(extremeRate>0.05)failures.push(`listening: extreme distractor rate ${(extremeRate*100).toFixed(1)}%`);
if(nearMissFailures)failures.push(`listening: ${nearMissFailures} items lack two credible near-miss distractors`);
if(lengthFailures)failures.push(`listening: ${lengthFailures} distractors have implausible length`);
if(!(listeningDepth.N1.avgSentenceChars>listeningDepth.N2.avgSentenceChars&&listeningDepth.N2.avgSentenceChars>=listeningDepth.N3.avgSentenceChars-2&&listeningDepth.N3.avgSentenceChars>listeningDepth.N4.avgSentenceChars))failures.push('listening: cognitive-load progression N1→N4 is not preserved');

// Conversation: measure template concentration after the batch-3 style rewrite.
let cw=run('conversation-reference-expansion.js',{SITUATION_SCENES:[]});
for(const f of ['conversation-gap-expansion.js','conversation-function-topup.js','conversation-quality-batch3.js'])cw=run(f,{SITUATION_SCENES:[...(cw.SITUATION_SCENES||[])]});
const scenes=(cw.SITUATION_SCENES||[]).filter(s=>s.coverageGapExpansion);
const all=scenes.flatMap(s=>(s.items||[]).map(x=>({...x,sceneId:s.id})));
const qualityRewritten=all.filter(x=>x.qualityDepthBatch3).length;
for(const s of scenes){if((s.items||[]).length!==25)failures.push(`conversation ${s.id}: item count changed`);for(const l of ['N1','N2','N3','N4','N5'])if((s.items||[]).filter(x=>x.level===l).length!==5)failures.push(`conversation ${s.id}: ${l} count changed`)}
const legacyPhrases={N4:'について確認したいです。どうしたらいいですか。',N3:'を進めるには何を確認すればいいでしょうか。',N2:'通常の方法が難しい場合',N1:'実情に即した対応をご検討いただけないでしょうか。'};
const templateCounts={};
for(const [l,p] of Object.entries(legacyPhrases)){templateCounts[l]=all.filter(x=>x.level===l&&String(x.lines?.[0]?.jp||'').includes(p)).length;if(templateCounts[l]>9)failures.push(`conversation ${l}: legacy template concentration ${templateCounts[l]}`)}
const conversationDepth={};
for(const l of ['N1','N2','N3','N4','N5']){const rows=all.filter(x=>x.level===l);conversationDepth[l]={count:rows.length,avgDialogueChars:+avg(rows.map(x=>jpLen((x.lines||[]).map(y=>y.jp).join('')))).toFixed(1)}}
if(!(conversationDepth.N1.avgDialogueChars>conversationDepth.N2.avgDialogueChars&&conversationDepth.N2.avgDialogueChars>conversationDepth.N3.avgDialogueChars&&conversationDepth.N3.avgDialogueChars>conversationDepth.N4.avgDialogueChars&&conversationDepth.N4.avgDialogueChars>conversationDepth.N5.avgDialogueChars))failures.push('conversation: JLPT dialogue-load progression is not monotonic');
if(qualityRewritten<80)failures.push(`conversation: only ${qualityRewritten} generated dialogues were diversified`);
const pairSeen=new Set();let dupPairs=0;for(const x of all){const k=norm((x.lines||[]).map(y=>y.jp).join('|'));if(pairSeen.has(k))dupPairs++;pairSeen.add(k)}if(dupPairs)failures.push(`conversation: ${dupPairs} exact duplicate dialogue pairs remain in targeted scenes`);
const functionText=all.map(x=>(x.lines||[]).map(y=>y.jp).join(' ')).join(' ');
for(const [name,signals] of Object.entries({N4_reschedule:['変更','別の時間'],N4_recommendation:['ほうがいい','したほう'],N3_procedure:['手続','申請','提出'],N2_exception:['今回に限り','通常の方法以外','事情がある場合']}))if(!signals.some(k=>functionText.includes(k)))failures.push(`conversation: batch2 function regression ${name}`);

const report={version:'2026-08-27-quality-depth-batch3-v1',method:'Original-content quality audit; no external copyrighted examples are copied.',grammarDepth,listening:{batch2Targets:batch2.length,qualityTagged,extremeDistractorRate:+extremeRate.toFixed(4),nearMissFailures,lengthFailures,depth:listeningDepth},conversation:{targetScenes:scenes.length,targetDialogues:all.length,qualityRewritten,legacyTemplateCounts:templateCounts,depth:conversationDepth,duplicatePairs:dupPairs},failures,passed:failures.length===0};
fs.mkdirSync('data',{recursive:true});fs.writeFileSync('data/quality_depth_batch3_report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exit(1);
