import fs from 'node:fs';

// Run the full v2 audit first (6,690 listening rows + repeated N1-N5 generation).
await import('./audit_listening_mock_quality_v2.mjs');

const base=JSON.parse(fs.readFileSync('data/listening_mock_quality_v2_report.json','utf8'));
const failures=[...(base.failures||[])];
const html=fs.readFileSync('mocktest.html','utf8');
const js=fs.readFileSync('mocktest.js','utf8');
const finalStatic={
  mockCacheBust:html.includes('mocktest.js?v=20260822-quality3'),
  informationSearchDuplicateRootFixed:js.includes('t===18?16:18'),
  weakQuickResponseInactive:!((js.match(/function buildListening\(level,n\)\{[^\n]+/)||[])[0]||'').includes('buildQuickResponse'),
  listeningV82:fs.readFileSync('listening.html','utf8').includes('日本語聽解挑戰 v8.2')
};
for(const [k,v] of Object.entries(finalStatic))if(!v)failures.push(`final static check failed: ${k}`);
const report={...base,version:'20260822-quality3',finalStatic,failures};
fs.writeFileSync('data/listening_mock_quality_v3_report.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(failures.length)process.exit(1);
