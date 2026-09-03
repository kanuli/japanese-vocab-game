'use strict';
var fs=require('fs');
var path=require('path');
var conj=require('./wordlist-conjugation.js');
var failed=0,passed=0;
function ok(cond,msg){if(cond){passed++;return true;}failed++;console.error('FAIL',msg);return false;}
function load(name){
  var p=path.join(process.cwd(),name);
  if(!fs.existsSync(p))return null;
  return JSON.parse(fs.readFileSync(p,'utf8'));
}
function mustLoad(name){
  var d=load(name);
  ok(!!d, name+' exists');
  return d;
}
function group(c){return c?(c.voices||c.speakers||{}):{};}
function readingsOf(c){
  var out=Object.create(null),words=c&&c.words||{},k,r;
  for(k in words){
    if(!Object.prototype.hasOwnProperty.call(words,k))continue;
    r=conj.normalizeReading(String(k).split('|')[0]);
    if(r)out[r]=words[k];
  }
  return out;
}
function checkReadyCatalog(name,c,requiredVoices){
  if(!c)return;
  ok(typeof c==='object', name+' is object');
  ok(c.version===1||c.version===2, name+' version 1 or 2');
  ok(typeof c.status==='string', name+' has status');
  if(c.status==='building'||c.status==='catalog'||c.status==='pending'){
    ok(true, name+' pending/building is allowed before generation finishes');
    return;
  }
  if(c.status!=='ready'){
    ok(false, name+' unexpected status '+c.status);
    return;
  }
  ok(c.words&&typeof c.words==='object', name+' words map');
  var g=group(c);
  var keys=Object.keys(g);
  ok(keys.length>0, name+' has voices/speakers');
  ok(Number(c.wordCount)===Object.keys(c.words).length, name+' wordCount matches words map');
  var seen=Object.create(null),k,entry,id,shard;
  for(k in c.words){
    if(!Object.prototype.hasOwnProperty.call(c.words,k))continue;
    entry=c.words[k];
    if(!ok(Array.isArray(entry)&&entry.length>=2, name+' entry array for '+k))continue;
    id=String(entry[0]); shard=String(entry[1]);
    if(seen[id]&&seen[id]!==k){
      ok(false, name+' duplicate conflicting id '+id+' '+seen[id]+' vs '+k);
    }
    seen[id]=k;
  }
  requiredVoices.forEach(function(v){
    ok(!!g[v], name+' has required voice '+v);
    var meta=g[v]||{};
    var idx=meta.indexUrl||meta.indexGithubUrl||meta.indexHfUrl||'';
    ok(!!idx, name+' '+v+' has index URL');
    if(meta.indexUrl&&meta.indexUrl.indexOf('./')===0){
      var file=meta.indexUrl.split('?')[0].replace(/^\.\//,'');
      if(c.status==='ready'){
        ok(fs.existsSync(path.join(process.cwd(),file))||!!(meta.indexGithubUrl||meta.indexHfUrl), name+' '+v+' index file or remote URL '+file);
      }
    }
  });
}

var lemmaST=mustLoad('word-supertonic3-catalog.json');
var lemmaVV=mustLoad('word-voicevox-catalog.json');
var lemmaAI=mustLoad('word-aivis-catalog.json');
checkReadyCatalog('word-supertonic3-catalog.json', lemmaST, ['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5']);
checkReadyCatalog('word-voicevox-catalog.json', lemmaVV, ['s01']);
checkReadyCatalog('word-aivis-catalog.json', lemmaAI, ['a01','a02','a03','a04']);

var conjST=mustLoad('word-supertonic3-conj-catalog.json');
ok(!!conjST, 'conj F3 catalog target exists');
if(conjST){
  ok(conjST.status==='ready'||conjST.status==='building'||conjST.status==='catalog', 'conj catalog status');
  checkReadyCatalog('word-supertonic3-conj-catalog.json', conjST, conjST.status==='ready'?Object.keys(group(conjST)):[]);
  if(conjST.status==='ready'){
    ok(!!group(conjST).F3, 'existing conj catalog still has F3');
    var hit=conj.hostedLookup(conjST.words,{reading:'いった',kanji:'言った'});
    ok(!!hit, 'conj catalog reading lookup works for a hosted F3 reading');
  }
}

var conjV2=mustLoad('word-supertonic3-conj-v2-catalog.json');
ok(!!conjV2, 'conj v2 catalog target exists');
if(conjV2){
  checkReadyCatalog('word-supertonic3-conj-v2-catalog.json', conjV2, conjV2.status==='ready'?['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5']:[]);
}

var conjVV=load('word-voicevox-conj-catalog.json');
ok(!!conjVV, 'voicevox conj catalog target exists');
if(conjVV) checkReadyCatalog('word-voicevox-conj-catalog.json', conjVV, conjVV.status==='ready'?Object.keys(group(conjVV)):[]);

var conjAI=load('word-aivis-conj-catalog.json');
ok(!!conjAI, 'aivis conj catalog target exists');
if(conjAI) checkReadyCatalog('word-aivis-conj-catalog.json', conjAI, conjAI.status==='ready'?['a01','a02','a03','a04']:[]);

['word-supertonic3-delta-catalog.json','word-supertonic3-runtime-delta-catalog.json'].forEach(function(name){
  var d=mustLoad(name);
  if(d) checkReadyCatalog(name, d, d.status==='ready'?['F3']:[ ]);
});

var tabemasu=conj.hostedLookup((lemmaST&&lemmaST.words)||{}, {reading:'たべます',kanji:'食べます'});
ok(!!tabemasu && tabemasu.hit==='exact', 'lemma catalog still has たべます exact key');
var tabemashita=conj.hostedLookup((lemmaST&&lemmaST.words)||{}, {reading:'たべました',kanji:'食べました'});
ok(!tabemashita || tabemashita.hit, 'lookup API returns null or a hit, never throws');

var query=conj.audioQuery('食べました','たべました');
ok(query.text==='たべました', 'audioQuery still uses kana');

if(failed){
  console.error('\nCATALOG '+passed+' passed, '+failed+' failed');
  process.exit(1);
}
console.log('CATALOG PASS '+passed+' assertions');
