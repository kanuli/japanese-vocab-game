from pathlib import Path
import re

p = Path('grammar.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語文法挑戰 v2.3｜JLPT N1–N5', '日本語文法挑戰 v2.4｜JLPT N1–N5')
s = s.replace('<h1>📝 日本語文法挑戰 v2.3</h1>', '<h1>📝 日本語文法挑戰 v2.4</h1>')

replacement = r'''function answerShape(a){
 const s=String(a||"").trim().replace(/[〜～~]/g,"");
 if(!s)return "unknown";
 if(/^(て|で|た|だ|ない|なく|なけれ|ず|ば|なら|ても|でも)/.test(s))return "conjugation-bound";
 if(/^(の|に|を|が|は|へ|と|も|で|から|まで|より)(?:$|[^ぁ-んァ-ン一-龯])/.test(s))return "particle-bound";
 if(/^(の|に)(?:ため|ほう|方|わけ|訳|よう|様|つもり|ところ|こと|もの)/.test(s))return "particle-bound";
 return "free";
}
function edgeClass(text,side){
 const s=String(text||"");
 if(!s.trim())return "none";
 const t=side==="left"?s.trimEnd():s.trimStart();
 if(side==="left"){
  if(/[てで]$/.test(t))return "te-form";
  if(/[ただ]$/.test(t))return "past-form";
  if(/(?:ない|なく|なかった|ません|ず)$/.test(t))return "negative-form";
  if(/[るうくぐすつぬぶむ]$/.test(t))return "dictionary-like";
  if(/い$/.test(t))return "i-ending";
  if(/な$/.test(t))return "na-ending";
  if(/の$/.test(t))return "no-ending";
  if(/[一-龯々ぁ-んァ-ンー]$/.test(t))return "nominal-or-lexical";
  return "other";
 }
 if(/^[、,]/.test(t))return "comma";
 if(/^[。！？!?]/.test(t))return "sentence-end";
 if(/^(です|でした|だ|だった|である|では)/.test(t))return "copula";
 if(/^(を|が|は|に|で|へ|と|も|から|まで|より)/.test(t))return "particle";
 if(/^(ない|なく|なかった|ません|ず)/.test(t))return "negative";
 return "lexical";
}
function polarityOfRight(right){
 const r=String(right||"").trimStart().slice(0,18);
 return /(?:ない|なく|なかった|ません|ず|ぬ)/.test(r)?"negative":"other";
}
function slotProfile(q){
 const parts=String(q.q||"").split("＿＿");
 const left=parts[0]||"", right=parts.slice(1).join("＿＿");
 const l=left.trimEnd(), r=right.trimStart();
 let position="middle";
 if(!l.trim())position="start";
 else if(!r.trim())position="end";
 else if(/[。！？!?]$/.test(l))position="clause-start";
 return {
  position,
  leftClass:edgeClass(l,"left"),
  rightClass:edgeClass(r,"right"),
  polarity:polarityOfRight(r),
  answerShape:answerShape(q.a)
 };
}
function slotCompatible(a,b){
 if(!a||!b)return false;
 if(a.type!==b.type)return false;
 const x=a.slot||slotProfile(a), y=b.slot||slotProfile(b);
 if(x.position!==y.position)return false;
 if(x.answerShape!==y.answerShape)return false;
 if(x.rightClass!==y.rightClass)return false;
 if((x.position==="middle"||x.position==="end") && x.leftClass!==y.leftClass)return false;
 if((x.position==="start"||x.position==="clause-start") && x.polarity!==y.polarity)return false;
 return true;
}
function generateFromPoints(points,level){
 const raw=[];
 points.forEach((pt,pi)=>{
   const cat=semanticCategory((pt.short_explanation||"")+" "+(pt.long_explanation||""));
   const type=classifyType(pt.title,pt.short_explanation);
   (pt.examples||[]).slice(0,4).forEach((ex,ei)=>{
     const jp=String(ex.jp||"").trim(); if(!jp)return;
     const a=findPattern(jp,pt); if(!a)return;
     if(a.length===1 && countOcc(jp,a)!==1)return;
     const q={
       id:`web-${level}-${pi}-${ei}`, level, type, source:"web",
       q:jp.replace(a,"＿＿"), a, grammar:cleanTitle(pt.title),
       meaning:cat, exp:pt.short_explanation||"", zh:ex.en||"",
       formation:pt.formation||"", category:cat, answerLen:[...a].length
     };
     q.slot=slotProfile(q);
     raw.push(q);
   });
 });

 return raw.map(q=>{
   let candidates=raw.filter(x=>x.id!==q.id && x.a!==q.a && slotCompatible(q,x));

   const uniq=new Map();
   for(const x of candidates){if(!uniq.has(x.a))uniq.set(x.a,x)}
   candidates=[...uniq.values()];

   // For a free-standing modifier at the start of a clause, same-meaning alternatives
   // can make more than one answer valid. Prefer structurally compatible candidates
   // from different semantic categories, and discard the question if there are too few.
   const freeStart=(q.slot.position==="start"||q.slot.position==="clause-start") && q.slot.answerShape==="free";
   if(freeStart){
     const contrasted=candidates.filter(x=>x.category!==q.category);
     if(contrasted.length>=3)candidates=contrasted;
   }

   const score=x=>{
     let s=0;
     if(!freeStart && x.category===q.category)s+=40;
     if(freeStart && x.category!==q.category)s+=25;
     if(x.slot.polarity===q.slot.polarity)s+=12;
     if(x.answerLen===q.answerLen)s+=8;
     s-=Math.abs(x.answerLen-q.answerLen)*2;
     return s;
   };
   candidates.sort((a,b)=>score(b)-score(a));

   // Never fall back to grammatically incompatible random choices.
   if(candidates.length<3)return null;
   const pool=candidates.slice(0,12);
   const pick=[];
   while(pick.length<3 && pool.length){
     const window=Math.min(4,pool.length);
     const i=Math.floor(Math.random()*window);
     pick.push(pool.splice(i,1)[0].a);
   }
   if(pick.length<3)return null;
   q.choices=shuffle([q.a,...pick]);
   return q;
 }).filter(Boolean);
}
async function fetchJSON(level){'''

pat = r'function generateFromPoints\(points,level\)\{.*?\n\}\nasync function fetchJSON\(level\)\{'
new_s, n = re.subn(pat, lambda m: replacement, s, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f'generateFromPoints replacement failed: {n}')
s = new_s

s = s.replace('產生 ${webQuestions.length.toLocaleString()} 題填空練習。', '經文法相容性過濾後產生 ${webQuestions.length.toLocaleString()} 題高品質填空練習。')

p.write_text(s, encoding='utf-8')
