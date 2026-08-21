import fs from 'node:fs';

// Run the full v2 audit first (6,690 listening rows + repeated N1-N5 generation).
await import('./audit_listening_mock_quality_v2.mjs');

const base=JSON.parse(fs.readFileSync('data/listening_mock_quality_v2_report.json','utf8'));
const failures=[...(base.failures||[])];
const html=fs.readFileSync('mocktest.html','utf8');
const js=fs.readFileSync('mocktest.js','utf8');
const finalStatic={
  mockCacheBust:html.includes('mocktest.js?v=20260822-quality4'),
  informationSearchDuplicateRootFixed:js.includes('t===18?16:18'),
  weakQuickResponseInactive:!((js.match(/function buildListening\(level,n\)\{[^\n]+/)||[])[0]||'').includes('buildQuickResponse'),
  listeningV82:fs.readFileSync('listening.html','utf8').includes('日本語聽解挑戰 v8.2'),
  placeSpecificSceneActions:js.includes('const SCENE_ACTIONS=')&&js.includes('acts[place]||[]'),
  malformedMasuConcatenationRemoved:!js.includes('${act}予定です')&&!js.includes('${act2}必要があります')
};
for(const [k,v] of Object.entries(finalStatic))if(!v)failures.push(`final static check failed: ${k}`);

// Structural QA cannot by itself detect every awkward Japanese template. Generate
// additional reading/listening questions and reject known malformed sentence forms
// that were possible in the earlier cross-product scene generator.
const api=globalThis.__mockTestQA;
let naturalnessChecked=0;
const badJapanese=[/します必要があります/,/ます予定です/,/行って、?行きます/,/行き、そこで行きます/];
if(!api){
  failures.push('naturalness QA API unavailable');
}else{
  for(const level of ['N5','N4','N3','N2','N1']){
    for(let i=0;i<20;i++){
      const qs=[...api.buildReading(level,24),...api.buildListening(level,30)];
      for(const q of qs){
        naturalnessChecked++;
        const text=[q.question,q.passage,q.audioText,...(q.choices||[])].filter(Boolean).join('\n');
        for(const rx of badJapanese)if(rx.test(text))failures.push(`mock ${level} unnatural generated form ${rx}: ${q.id}`);
      }
    }
  }
}

const report={...base,version:'20260822-quality4',naturalnessChecked,finalStatic,failures};
fs.writeFileSync('data/listening_mock_quality_v3_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(failures.length)process.exit(1);
