import fs from 'node:fs';
const p='data/grammar_depth_batch8_preflight.json';
const d=JSON.parse(fs.readFileSync(p,'utf8'));
const b=d.byLevel||{};const failures=[];
const expected={N1:24,N2:18,N3:18,N4:30,N5:18};
if(d.count!==108)failures.push(`grammar count=${d.count} != 108`);
for(const [lv,n] of Object.entries(expected)){
 if(b?.[lv]?.count!==n)failures.push(`${lv} count=${b?.[lv]?.count} != ${n}`);
 if((b?.[lv]?.structuralErrors||0)!==0)failures.push(`${lv} structuralErrors=${b?.[lv]?.structuralErrors}`);
}
// The purpose of Batch 8 is specifically to prevent sentence length from being
// mistaken for JLPT depth. N2 must carry materially greater relation/inference
// complexity than N3 even if an N3 sentence happens to contain more characters.
if(!(b.N2.avgComplexityScore>=b.N3.avgComplexityScore+2.0))failures.push(`N2/N3 complexity separation too small: ${b.N2.avgComplexityScore} vs ${b.N3.avgComplexityScore}`);
if(!(b.N2.avgClauses>b.N3.avgClauses))failures.push(`N2 clauses ${b.N2.avgClauses} <= N3 ${b.N3.avgClauses}`);
if(!(b.N2.advancedShare>=50))failures.push(`N2 advancedShare=${b.N2.advancedShare}<50`);
if(!(b.N3.advancedShare<=25))failures.push(`N3 advancedShare=${b.N3.advancedShare}>25`);
if(!(b.N3.avgComplexityScore>b.N4.avgComplexityScore&&b.N4.avgComplexityScore>b.N5.avgComplexityScore))failures.push(`N3/N4/N5 complexity progression invalid`);
if(!(b.N1.avgChars>b.N5.avgChars&&b.N1.advancedShare>b.N5.advancedShare))failures.push(`N1 does not show higher-formality depth signals than N5`);
const report={version:'2026-08-27-grammar-depth-batch8-v1',grammarCount:d.count,byLevel:b,diagnosticFinding:'N3 average sentence length may slightly exceed N2, but N2 is materially deeper on advanced constructions, connective/subordination load and composite complexity. No padding rewrite is justified.',targets:{structuralErrors:0,n2MinusN3ComplexityMin:2,n2AdvancedShareMin:50,n3AdvancedShareMax:25},failures,passed:failures.length===0};
fs.writeFileSync('data/grammar_depth_batch8_report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(failures.length)process.exit(1);
