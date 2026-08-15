import fs from 'node:fs';
const src=JSON.parse(fs.readFileSync('voicevox-full-index.json','utf8'));
const q=src.questions||{};
const ids=Object.keys(q);
if(ids.length!==3310)throw new Error(`Expected 3,310 Listening questions, got ${ids.length}`);
const questions={},textMap={};
const norm=s=>String(s||'').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』（）()]/g,'').trim();
for(const id of ids){
 const text=String(q[id]?.text||'').trim();
 if(!text)throw new Error(`Missing Japanese text for ${id}`);
 questions[id]={text,level:String(id).split('-')[0]};
 const k=norm(text);if(k&&!textMap[k])textMap[k]=id;
}
const out={version:1,status:'catalog',engine:'shared-listening-audio',language:'ja',questionCount:ids.length,questions,textMap};
fs.writeFileSync('listening-audio-catalog.json',JSON.stringify(out,null,2)+'\n');
console.log(`Listening audio catalog: ${out.questionCount} questions, ${Object.keys(textMap).length} unique normalized texts`);
