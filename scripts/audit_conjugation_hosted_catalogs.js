#!/usr/bin/env node
'use strict';
var fs=require('fs');
var path=require('path');
var conj=require(path.resolve(__dirname,'..','wordlist-conjugation.js'));

function load(name){
  var p=path.resolve(process.cwd(),name);
  if(!fs.existsSync(p))return null;
  return JSON.parse(fs.readFileSync(p,'utf8'));
}
function nfkc(s){return conj.normalizeReading(s);}
function readings(c){
  var out={},words=c&&c.words||{},k,r;
  for(k in words){
    if(!Object.prototype.hasOwnProperty.call(words,k))continue;
    r=nfkc(String(k).split('|')[0]);
    if(r&&!out[r])out[r]=true;
  }
  return out;
}
function group(c){return c?(c.voices||c.speakers||{}):{};}

var requiredST=['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];
var lemmaST=load('word-supertonic3-catalog.json')||{};
var delta=load('word-supertonic3-delta-catalog.json')||{};
var runtime=load('word-supertonic3-runtime-delta-catalog.json')||{};
var conj1=load('word-supertonic3-conj-catalog.json')||{};
var conj2=load('word-supertonic3-conj-v2-catalog.json')||{};
var lemmaVV=load('word-voicevox-catalog.json')||{};
var deltaVV=load('word-voicevox-delta-catalog.json')||{};
var conjVV=load('word-voicevox-conj-catalog.json')||{};
var lemmaAI=load('word-aivis-catalog.json')||{};
var deltaAI=load('word-aivis-delta-catalog.json')||{};
var conjAI=load('word-aivis-conj-catalog.json')||{};
var plan=load('word-supertonic3-conj-plan.json')||{};
var auditIn=load('word-conj-hosted-audit.json')||load('word-supertonic3-conj-plan.json')||{};

function union(){
  var out={},i,src,k;
  for(i=0;i<arguments.length;i++){
    src=readings(arguments[i]);
    for(k in src)out[k]=true;
  }
  return out;
}

var stLemma=union(lemmaST,delta,runtime);
var stAll=union(lemmaST,delta,runtime,conj1,conj2.status==='ready'?conj2:{});
var vvAll=union(lemmaVV,deltaVV,conjVV.status==='ready'?conjVV:{});
var aiAll=union(lemmaAI,deltaAI,conjAI.status==='ready'?conjAI:{});

var uniqueCount=Number(auditIn.uniqueReadings||plan.uniqueReadingCount||0);
var remaining=Number(auditIn.remainingMissing!=null?auditIn.remainingMissing:(plan.newReadingCount||0));

function voiceCoverage(engine, catalogReady, required, lemmaReadings, conjCatalogs){
  var rows=[];
  required.forEach(function(v){
    var hasLemma=true;
    if(engine==='supertonic3'){
      hasLemma=!!(group(lemmaST)[v]||group(delta)[v]||group(runtime)[v]);
    }else if(engine==='voicevox'){
      hasLemma=!!group(lemmaVV)[v];
    }else if(engine==='aivis'){
      hasLemma=!!group(lemmaAI)[v];
    }
    var conjHas=conjCatalogs.some(function(c){return c&&c.status==='ready'&&!!group(c)[v];});
    var available=hasLemma?Object.keys(lemmaReadings).length:0;
    if(conjHas){
      conjCatalogs.forEach(function(c){
        if(c&&c.status==='ready'&&group(c)[v]) available=Object.keys(union({words:c.words}, {words:Object.keys(lemmaReadings).reduce(function(o,k){o[k+'|x']=[k,0];return o;},{})})).length;
      });
    }
    rows.push({
      voice:v,
      required:uniqueCount||null,
      lemmaVoicePresent:hasLemma,
      conjVoiceReady:conjHas,
      catalogStatus:conjHas?'ready':(conjCatalogs.some(function(c){return c&&c.status&&c.status!=='ready';})?'in_progress':'missing')
    });
  });
  return rows;
}

var errors=[];
requiredST.forEach(function(v){
  if(!group(lemmaST)[v]) errors.push('lemma SuperTonic missing voice '+v);
});
['a01','a02','a03','a04'].forEach(function(v){
  if(!group(lemmaAI)[v]) errors.push('lemma Aivis missing voice '+v);
});
if(!group(lemmaVV).s01) errors.push('lemma VOICEVOX missing s01');
if(!conj1) errors.push('missing word-supertonic3-conj-catalog.json');
if(!conj2) errors.push('missing word-supertonic3-conj-v2-catalog.json');
if(!conjVV) errors.push('missing word-voicevox-conj-catalog.json');
if(!conjAI) errors.push('missing word-aivis-conj-catalog.json');

if(conj1&&conj1.status==='ready'){
  Object.keys(conj1.words||{}).forEach(function(k){
    var e=conj1.words[k];
    if(!Array.isArray(e)||e.length<2) errors.push('malformed conj entry '+k);
  });
}

var report={
  version:2,
  vocabScanned:auditIn.vocabScanned||null,
  verbsEligible:auditIn.verbsEligible||plan.verbCount||null,
  formInstances:auditIn.formInstances||null,
  uniqueReadings:uniqueCount,
  alreadyHostedReadingCount:plan.alreadyHostedReadingCount||auditIn.alreadyHostedReadingCount||null,
  remainingMissing:remaining,
  missing_unique_readings:remaining,
  capped:!!plan.capped,
  success:auditIn.success||null,
  failure:auditIn.failure||0,
  skipped:auditIn.skipped||null,
  duplicatesRemoved:auditIn.duplicatesRemoved||null,
  engines:{
    supertonic3:{
      lemmaVoices:Object.keys(group(lemmaST)),
      conjV1Status:conj1&&conj1.status||'missing',
      conjV1Voices:Object.keys(group(conj1)),
      conjV2Status:conj2&&conj2.status||'missing',
      conjV2Voices:Object.keys(group(conj2)),
      coverage:voiceCoverage('supertonic3', true, requiredST, stLemma, [conj1,conj2])
    },
    voicevox:{
      lemmaSpeakers:Object.keys(group(lemmaVV)),
      conjStatus:conjVV&&conjVV.status||'missing',
      conjSpeakers:Object.keys(group(conjVV)),
      coverage:voiceCoverage('voicevox', true, Object.keys(group(lemmaVV)), readings(lemmaVV), [conjVV])
    },
    aivis:{
      lemmaVoices:Object.keys(group(lemmaAI)),
      conjStatus:conjAI&&conjAI.status||'missing',
      conjVoices:Object.keys(group(conjAI)),
      coverage:voiceCoverage('aivis', true, ['a01','a02','a03','a04'], readings(lemmaAI), [conjAI])
    }
  },
  errors:errors,
  note:'Device TTS is not hosted PASS. remainingMissing counts unique conjugated readings not yet in this engine source.'
};

var outPath=path.resolve(process.cwd(),'word-conj-hosted-audit.json');
var existing=load('word-conj-hosted-audit.json');
if(existing&&existing.uniqueReadings){
  report.vocabScanned=existing.vocabScanned||report.vocabScanned;
  report.verbsEligible=existing.verbsEligible||report.verbsEligible;
  report.formInstances=existing.formInstances||report.formInstances;
  report.uniqueReadings=existing.uniqueReadings;
  report.remainingMissing=existing.remainingMissing;
  report.missing_unique_readings=existing.missing_unique_readings;
  report.duplicatesRemoved=existing.duplicatesRemoved;
  report.skipped=existing.skipped;
  report.success=existing.success;
  report.alreadyHostedReadingCount=existing.alreadyHostedReadingCount;
}
fs.writeFileSync(outPath, JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({remainingMissing:report.remainingMissing,uniqueReadings:report.uniqueReadings,errors:errors,conjV2:conj2&&conj2.status,voicevox:conjVV&&conjVV.status,aivis:conjAI&&conjAI.status},null,2));
if(errors.length){
  console.error('AUDIT FAIL', errors.join('; '));
  process.exit(1);
}
console.log('AUDIT PASS catalog integrity');
