/* Regression: 50 hand-reviewed JMdict common-vocabulary candidates are retained
 * across core/advanced merge, with exact entry IDs, usable readings and POS.
 * This file is deterministic and does not need browser/network access. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const report=JSON.parse(fs.readFileSync('data/vocab_common_coverage_audit.json','utf8'));
const expectedIds=[32,39,42,43,45,50,51,53,54,59,61,72,83,87,98,99,111,114,116,120,121,124,128,129,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165,167]
  .map(i=>report.candidates[i-1].entryId);
const expected=new Set(expectedIds);
assert.equal(expected.size,50,'must have exactly 50 unique JMdict entry IDs');
const ctx={window:{ADVANCED_WORDS:[]}};
vm.runInNewContext(fs.readFileSync('data/vocab_common_fixups.js','utf8'),ctx);
const words=ctx.window.VOCAB_COMMON_FIXUPS;
const reviewed=words.filter(w=>String(w.id).startsWith('reviewed-common-20261017-'));
assert.equal(reviewed.length,50,'all 50 reviewed terms must be published');
assert.equal(new Set(reviewed.map(w=>w.entryId)).size,50);
assert.deepEqual(new Set(reviewed.map(w=>w.entryId)),expected,'only the approved 50 candidate entry IDs may be published');
assert.equal(new Set(reviewed.map(w=>w.reading+'|'+w.displayWord)).size,50,'new entries cannot duplicate exact word forms');
for(const w of reviewed){
  assert.match(w.reading,/^[ぁ-ゖァ-ヺー]+$/);
  assert.match(w.level,/^N[2-4]$/,'learning level should be an N2-N4 estimate');
  assert.equal(w.estimated,true,w.displayWord+' not marked estimated');
  assert.equal(w.levelSource,'supplement-estimate-not-official');
  assert.ok(w.meaning&&w.meaning.length>=2);
  assert.ok(w.category);
  assert.ok(Array.isArray(w.reviewedPOS)&&w.reviewedPOS.length>0);
  assert.equal(w.id,'reviewed-common-20261017-'+w.entryId);
}
assert.ok(!reviewed.some(w=>w.meaning.includes('丘位元')||w.displayWord==='刳い'||w.displayWord==='塩っぱい'||w.displayWord==='滅茶'));
const POS=require('../wordlist-pos.js');
for(const w of reviewed){
  assert.deepEqual(POS.labels(w),w.reviewedPOS,w.displayWord+' POS mismatch');
  assert.equal(POS.source(w),'manual',w.displayWord+' review origin lost');
}
function find(k){return reviewed.find(w=>w.displayWord===k);}
for(const v of ['やらかす','バグる','ミスる','ビビる'])assert.deepEqual(POS.labels(find(v)),['動詞（第1類）']);
for(const v of ['ダサい','しょっぱい','キモい','えぐい','うざい','むずい'])assert.deepEqual(POS.labels(find(v)),['い形容詞']);
assert.deepEqual(POS.labels(find('めっちゃ')),['副詞']);
assert.deepEqual(POS.labels(find('めちゃ')),['名詞','な形容詞','副詞']);
const baseline=[{reading:'てんじんさま',kanji:'天神様',displayWord:'天神様',meaning:'OLD',level:'N1'},...reviewed.slice(0,2)];
const merged=ctx.window.applyVocabCommonFixups(baseline);
assert.equal(merged.filter(w=>w.reading==='てんじんさま'&&w.kanji==='天神様').length,1);
assert.equal(merged.find(w=>w.reading==='てんじんさま').level,'N3');
assert.equal(new Set(merged.map(w=>w.reading+'|'+(w.kanji||w.displayWord||w.reading))).size,merged.length);
console.log('REVIEWED COMMON VOCAB PASS: 50 exact source IDs, reviewed POS, estimated JLPT, merge dedup');
