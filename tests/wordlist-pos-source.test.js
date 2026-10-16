/* Verify the committed, pinned JMdict/Tomoshi POS catalog in the real renderer. */
'use strict';
const assert=require('node:assert/strict');
global.window=global;
require('../data/vocab_pos_verified.js');
const POS=require('../wordlist-pos.js');
const m=global.VOCAB_POS_VERIFIED;
assert.ok(m instanceof Map,'verified dictionary overlay must load as Map');
assert.ok(m.size>=32000,'insufficient complete-vocabulary POS coverage');
const checks=[
  ['ねっしん','熱心',['名詞','な形容詞']],
  ['すべて','全て',['名詞','副詞']],
  ['むしろ','寧ろ',['副詞']],
  ['かえって','却って',['副詞']],
  ['たべる','食べる',['動詞（第2類）']],
  ['きる','着る',['動詞（第2類）']],
  ['べんきょう','勉強',['名詞','動詞（第3類）']],
  ['きれい','綺麗',['な形容詞']],
  ['てんじんさま','天神様',['名詞']]
];
for(const [reading,kanji,expected] of checks){
  assert.deepEqual(POS.labels({reading,kanji,pos:'other'}),expected,kanji+' / '+reading);
}
assert.equal(POS.source({reading:'ねっしん',kanji:'熱心'}),'JMdict/Tomoshi');
assert.equal(POS.source({reading:'てんじんさま',kanji:'天神様'}),'manual');
const multi=Array.from(m.values()).filter(tags=>tags.length>1).length;
assert.ok(multi>8000, 'dictionary lost multi-POS on export');
console.log('VERIFIED LEXICAL POS: PASS ('+m.size+' entries, '+multi+' multi-POS)');
