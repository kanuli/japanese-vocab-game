#!/usr/bin/env node
'use strict';
var fs=require('fs');
var path=require('path');
var conj=require(path.resolve(__dirname,'..','wordlist-conjugation.js'));
function loadWords(inputPath){
  var raw=fs.readFileSync(inputPath,'utf8');
  var data=JSON.parse(raw);
  return Array.isArray(data)?data:(data.words||[]);
}
var input=process.argv[2];
var outPath=process.argv[3]||'';
if(!input){
  console.error('usage: node scripts/enumerate_conjugation_readings.js words.json [out.json]');
  process.exit(2);
}
var words=loadWords(input);
var unique=Object.create(null);
var verbs=0, forms=0, skipped=0;
for(var i=0;i<words.length;i++){
  var w=words[i];
  if(!conj.canConjugate(w)){skipped++;continue;}
  verbs++;
  var result=conj.conjugate(w);
  var rows=(result.forms||[]).concat(result.extended||[]);
  for(var j=0;j<rows.length;j++){
    var row=rows[j];
    if(!row||!row.reading)continue;
    forms++;
    var r=conj.normalizeReading(row.reading);
    if(!r)continue;
    if(!unique[r])unique[r]={reading:r, written:row.written||r, count:0};
    unique[r].count++;
    if(row.written)unique[r].written=unique[r].written||row.written;
  }
}
var items=Object.keys(unique).sort().map(function(k){return unique[k];});
var payload={verbCount:verbs, skippedCount:skipped, formCount:forms, uniqueReadingCount:items.length, items:items};
var json=JSON.stringify(payload);
if(outPath)fs.writeFileSync(outPath,json);
else process.stdout.write(json);
console.error('verbs',verbs,'unique readings',items.length,'forms',forms,'skipped',skipped);
