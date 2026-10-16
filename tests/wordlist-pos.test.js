/* Run: node tests/wordlist-pos.test.js */
'use strict';
const assert=require('node:assert/strict');
global.WordlistConjugation=require('../wordlist-conjugation.js');
const POS=require('../wordlist-pos.js');
function expect(kanji,reading,pos,labels){
  assert.deepEqual(POS.labels({kanji,displayWord:kanji,reading,pos}),labels,kanji+' '+reading);
}
expect('全て','すべて','noun',['名詞','副詞']);
expect('多分','たぶん','adj',['副詞']);
expect('元々','もともと','adj',['副詞']);
expect('天神様','てんじんさま','noun',['名詞']);
expect('綺麗','きれい','adj',['な形容詞']);
expect('静か','しずか','adj',['な形容詞']);
expect('高い','たかい','adj',['い形容詞（推定）']);
expect('勉強','べんきょう','noun',['名詞','動詞（第3類）']);
expect('全部','ぜんぶ','名・副',['名詞','副詞']);
expect('食べる','たべる','動2',['動詞（第2類）']);
expect('走る','はしる','動1',['動詞（第1類）']);
expect('する','する','動3',['動詞（第3類）']);
expect('先生','せんせい','noun',['名詞']);
expect('かえって','かえって','adv',['副詞']);
expect('寧ろ','むしろ','adv',['副詞']);
expect('?', 'unknown', 'other', ['未分類']);
assert.ok(POS.labels({kanji:'謎る',reading:'なぞる',pos:'verb'}).length>0);
console.log('WORDLIST POS: PASS (17 checked examples)');
