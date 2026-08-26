import fs from 'node:fs';

const LEVELS=['N1','N2','N3','N4','N5'];
const failures=[];
const avg=a=>a.length?+(a.reduce((s,n)=>s+n,0)/a.length).toFixed(1):0;
const median=a=>{if(!a.length)return 0;const b=[...a].sort((x,y)=>x-y),m=Math.floor(b.length/2);return b.length%2?b[m]:+((b[m-1]+b[m])/2).toFixed(1)};
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s　，。！？、,.!?「」『』（）()：:；;]/g,'');
const jpLen=s=>[...String(s??'').replace(/[\s　。、，,.！？!?「」『』【】（）()]/g,'')].length;
const EXTREME=/一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不/;
function zhSet(s){return new Set([...norm(s)].filter(c=>/[\u3400-\u9fff]/.test(c)))}
function overlap(a,b){const A=zhSet(a),B=zhSet(b);if(!A.size||!B.size)return 0;let n=0;A.forEach(c=>{if(B.has(c))n++});return n/Math.max(1,Math.min(A.size,B.size))}
function structuralErrors(x){const cs=Array.isArray(x?.choicesZh)?x.choicesZh.map(v=>String(v||'').trim()):[],correct=String(x?.correctZh||'').trim();const e=[];if(cs.length!==4)e.push('choice-count');if(cs.some(v=>!v))e.push('empty-choice');const keys=cs.map(norm);if(new Set(keys).size!==4)e.push('duplicate-choice');const target=norm(correct);if(!target||keys.filter(k=>k===target).length!==1)e.push('answer-not-unique');return e}
function catalogQuality(x){const errors=structuralErrors(x);if(errors.length)return{pass:false,errors,extremeWrong:0,nearMiss:0,lengthOutlier:0};const correct=String(x.correctZh||'').trim(),target=norm(correct),wrongs=x.choicesZh.map(v=>String(v||'').trim()).filter(v=>norm(v)!==target);const extremeWrong=wrongs.filter(w=>EXTREME.test(w)&&!EXTREME.test(correct)).length;const nearMiss=wrongs.filter(w=>overlap(correct,w)>=.12).length;const base=Math.max(1,[...norm(correct)].length);const lengthOutlier=wrongs.filter(w=>{const r=[...norm(w)].length/base;return r<.45||r>2.2}).length;return{pass:extremeWrong<2&&lengthOutlier<2&&nearMiss>=1,errors:[],extremeWrong,nearMiss,lengthOutlier}}

// Full 6,690-item project-original listening catalog.
const data=JSON.parse(fs.readFileSync('listening-original-catalog.json','utf8'));
const catalog=Array.isArray(data?.items)?data.items:[];
if(catalog.length!==6690)failures.push(`original catalog expected 6690 items, got ${catalog.length}`);
const perLevel={};
let structuralBad=0,eligible=0,extreme2=0,near0=0,len2=0;
const sigCount=new Map();
for(const l of LEVELS){const rows=catalog.filter(x=>String(x.level||'').toUpperCase()===l);const lens=[],stats={count:rows.length,qualityEligible:0,rejected:0,structuralBad:0,extremeTwoPlus:0,noNearMiss:0,lengthTwoPlusOutlier:0,avgSentenceChars:0,medianSentenceChars:0};for(const x of rows){lens.push(jpLen(x.jp));const q=catalogQuality(x);if(q.errors.length){stats.structuralBad++;structuralBad++;}if(q.extremeWrong>=2){stats.extremeTwoPlus++;extreme2++}if(q.nearMiss===0){stats.noNearMiss++;near0++}if(q.lengthOutlier>=2){stats.lengthTwoPlusOutlier++;len2++}if(q.pass){stats.qualityEligible++;eligible++}else stats.rejected++;const target=norm(x.correctZh);const wrongs=(x.choicesZh||[]).map(norm).filter(v=>v!==target).sort();const sig=wrongs.join('|');if(sig)sigCount.set(sig,(sigCount.get(sig)||0)+1)}stats.avgSentenceChars=avg(lens);stats.medianSentenceChars=median(lens);perLevel[l]=stats}
const repeatedWrongTriples=[...sigCount.values()].filter(n=>n>1);const maxWrongTripleReuse=repeatedWrongTriples.length?Math.max(...repeatedWrongTriples):1;
if(structuralBad)failures.push(`original catalog has ${structuralBad} structural choice errors`);
for(const l of LEVELS){if((perLevel[l]?.qualityEligible||0)<400)failures.push(`${l} retains fewer than 400 quality-eligible original items`)}
if(eligible<3000)failures.push(`quality-eligible original catalog too small (${eligible})`);

// Hanabira base examples are evaluated in memory only; report stores aggregate metrics, not copied text.
const GROUPS=[
['今日','昨日','明日','今朝'],['今週','先週','来週','再来週'],['今月','先月','来月','再来月'],['今年','去年','来年','再来年'],['さっき','先ほど','あとで','昨日'],
['朝','昼','夕方','夜'],['午前','午後'],['右','左','前','後'],['上','下'],['ここ','そこ','あそこ','どこ'],['これ','それ','あれ','どれ'],['この','その','あの','どの'],
['まだ','もう'],['いつも','よく','時々','たまに'],['必ず','たぶん','きっと','おそらく'],['好き','嫌い'],['高い','安い'],['大きい','小さい'],['多い','少ない'],['早い','遅い'],
['行きます','来ます','帰ります','戻ります'],['行く','来る','帰る','戻る'],['買います','売ります'],['買う','売る'],['始まります','終わります'],['始まる','終わる'],['増えます','減ります'],['増える','減る']
];
function shadowed(s,x){for(const g of GROUPS)for(const longer of g)if(longer!==x&&longer.length>x.length&&longer.includes(x)&&s.includes(longer))return true;return false}
function families(s){const out=[];for(const g of GROUPS){for(const x of g){if(!s.includes(x)||shadowed(s,x))continue;const a=[];for(const y of g){if(y===x)continue;const z=s.replace(x,y);if(z!==s&&!a.includes(z))a.push(z)}if(a.length)out.push(a)}}const m=s.match(/\d+/);if(m){const n=+m[0],a=[];for(const d of [-2,-1,1,2]){const v=Math.max(1,n+d),z=s.replace(m[0],String(v));if(z!==s&&!a.includes(z))a.push(z)}if(a.length)out.push(a)}return out}
function ranked(s){const f=families(s).sort((a,b)=>b.length-a.length);const same=f.find(a=>a.length>=3);if(same)return{items:[...same],sameDimension:true};return{items:[...new Set(f.flat())],sameDimension:false}}
async function fetchLevel(level){const url=`https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/grammar_ja_${level}_full_alphabetical_0001.json`;const r=await fetch(url);if(!r.ok)throw new Error(`${level} HTTP ${r.status}`);const d=await r.json();if(!Array.isArray(d))throw new Error(`${level} bad JSON shape`);const rows=[];for(const g of d)for(const e of (g.examples||[])){const jp=String(e.jp||'').trim();if(jp.length>=5&&jp.length<=95)rows.push(jp)}return rows}
const hanabira={perLevel:{},total:0,mutationEligible:0,sameDimensionEligible:0,duplicateSentences:0};const seenJp=new Set();
for(const l of LEVELS){let rows=[];try{rows=await fetchLevel(l)}catch(e){failures.push(`Hanabira ${l} fetch failed: ${e.message}`)}const lens=[],st={count:rows.length,mutationEligible:0,sameDimensionEligible:0,avgSentenceChars:0,medianSentenceChars:0};for(const jp of rows){lens.push(jpLen(jp));const k=norm(jp);if(seenJp.has(k))hanabira.duplicateSentences++;else seenJp.add(k);const r=ranked(jp);if(r.items.length>=3){st.mutationEligible++;hanabira.mutationEligible++;if(r.sameDimension){st.sameDimensionEligible++;hanabira.sameDimensionEligible++}}}st.avgSentenceChars=avg(lens);st.medianSentenceChars=median(lens);hanabira.perLevel[l]=st;hanabira.total+=rows.length}
if(hanabira.total<3000)failures.push(`Hanabira aggregate examples unexpectedly low (${hanabira.total})`);
if(hanabira.mutationEligible<100)failures.push(`Hanabira mutation-eligible pool unexpectedly low (${hanabira.mutationEligible})`);

const html=fs.readFileSync('listening.html','utf8');
const runtimeChecks={catalogQualityGate:html.includes('catalogChoiceQualityV4'),rankedMutation:html.includes('rankedMutationsV4'),qualityPool:html.includes('catalogChoiceQualityV4(x).pass'),qualityLabel:html.includes('通過全庫 quality gate')&&html.includes('優先同一語意維度')};
for(const [k,v] of Object.entries(runtimeChecks))if(!v)failures.push(`listening runtime integration missing: ${k}`);

const report={
 version:'2026-08-27-full-listening-quality-batch4-v1',
 methodology:{scope:'Full project-original 6,690 listening catalog plus Hanabira base examples used by listening.html.',catalogGate:'Severe-only runtime filter: rejects structural errors, >=2 extreme giveaway distractors, >=2 major length outliers, or zero lexical near-miss distractors.',hanabira:'Examples are fetched and evaluated in memory; only aggregate metrics are persisted.',copyright:'No external example text is written to this report.'},
 originalCatalog:{count:catalog.length,qualityEligible:eligible,rejected:catalog.length-eligible,eligibleRate:+(100*eligible/Math.max(1,catalog.length)).toFixed(1),structuralBad,extremeTwoPlus:extreme2,noNearMiss:near0,lengthTwoPlusOutlier:len2,maxWrongTripleReuse,perLevel},
 hanabira:{...hanabira,mutationEligibleRate:+(100*hanabira.mutationEligible/Math.max(1,hanabira.total)).toFixed(1),sameDimensionShareOfEligible:+(100*hanabira.sameDimensionEligible/Math.max(1,hanabira.mutationEligible)).toFixed(1)},
 runtimeChecks,
 failures,
 passed:failures.length===0
};
fs.mkdirSync('data',{recursive:true});fs.writeFileSync('data/full_listening_quality_batch4_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));if(failures.length)process.exit(1);
