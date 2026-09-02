'use strict';
var conj=require('./wordlist-conjugation.js');
var failed=0,passed=0;

function eq(actual,expected,msg){
  if(actual===expected){passed++;return;}
  failed++;
  console.error('FAIL',msg);
  console.error('  expected:',expected);
  console.error('  actual  :',actual);
}

function mapForms(result){
  var o={};
  (result&&result.forms||[]).forEach(function(row){o[row.id]=row.written;});
  return o;
}

function expectForms(word,expected,label){
  var result=conj.conjugate(word);
  if(!result){
    failed++;
    console.error('FAIL',label,'— conjugate returned null for',word);
    return;
  }
  Object.keys(expected).forEach(function(id){
    var row=result.forms.find(function(x){return x.id===id;});
    eq(row?row.written:undefined,expected[id],label+' '+id);
  });
}

function expectReading(word,expected,label){
  var result=conj.conjugate(word);
  Object.keys(expected).forEach(function(id){
    var row=result&&result.forms.find(function(x){return x.id===id;});
    eq(row?row.reading:undefined,expected[id],label+' reading '+id);
  });
}

/* 一段 */
expectForms({kanji:'食べる',reading:'たべる',pos:'他動2'},{
  dict:'食べる',masu:'食べます',nai:'食べない',ta:'食べた',te:'食べて',
  potential:'食べられる',volitional:'食べよう',imperative:'食べろ',
  prohibitive:'食べるな',ba:'食べれば',passive:'食べられる',
  causative:'食べさせる',causativePassive:'食べさせられる'
},'食べる');
expectReading({kanji:'食べる',reading:'たべる',pos:'他動2'},{
  masu:'たべます',nai:'たべない',te:'たべて'
},'食べる');

expectForms({kanji:'見る',reading:'みる',pos:'他動2'},{
  dict:'見る',masu:'見ます',nai:'見ない',ta:'見た',te:'見て',
  potential:'見られる',volitional:'見よう',imperative:'見ろ',
  prohibitive:'見るな',ba:'見れば',passive:'見られる',
  causative:'見させる',causativePassive:'見させられる'
},'見る');

expectForms({kanji:'起きる',reading:'おきる',pos:'自動2'},{
  dict:'起きる',masu:'起きます',nai:'起きない',ta:'起きた',te:'起きて',
  potential:'起きられる',volitional:'起きよう',imperative:'起きろ'
},'起きる');

/* 五段 */
expectForms({kanji:'書く',reading:'かく',pos:'他動1'},{
  dict:'書く',masu:'書きます',nai:'書かない',ta:'書いた',te:'書いて',
  potential:'書ける',volitional:'書こう',imperative:'書け',
  prohibitive:'書くな',ba:'書けば',passive:'書かれる',
  causative:'書かせる',causativePassive:'書かせられる'
},'書く');

expectForms({kanji:'読む',reading:'よむ',pos:'他動1'},{
  dict:'読む',masu:'読みます',nai:'読まない',ta:'読んだ',te:'読んで',
  potential:'読める',volitional:'読もう',imperative:'読め',
  prohibitive:'読むな',ba:'読めば',passive:'読まれる',
  causative:'読ませる',causativePassive:'読ませられる'
},'読む');

expectForms({kanji:'話す',reading:'はなす',pos:'他動1'},{
  dict:'話す',masu:'話します',nai:'話さない',ta:'話した',te:'話して',
  potential:'話せる',volitional:'話そう',imperative:'話せ',
  prohibitive:'話すな',ba:'話せば',passive:'話される',
  causative:'話させる',causativePassive:'話させられる'
},'話す');

expectForms({kanji:'買う',reading:'かう',pos:'他動1'},{
  dict:'買う',masu:'買います',nai:'買わない',ta:'買った',te:'買って',
  potential:'買える',volitional:'買おう',imperative:'買え',
  prohibitive:'買うな',ba:'買えば',passive:'買われる',
  causative:'買わせる',causativePassive:'買わせられる'
},'買う');

expectForms({kanji:'待つ',reading:'まつ',pos:'他動1'},{
  dict:'待つ',masu:'待ちます',nai:'待たない',ta:'待った',te:'待って'
},'待つ');

expectForms({kanji:'死ぬ',reading:'しぬ',pos:'自動1'},{
  dict:'死ぬ',masu:'死にます',nai:'死なない',ta:'死んだ',te:'死んで',
  potential:'死ねる',volitional:'死のう',imperative:'死ね'
},'死ぬ');

expectForms({kanji:'遊ぶ',reading:'あそぶ',pos:'自動1'},{
  dict:'遊ぶ',masu:'遊びます',nai:'遊ばない',ta:'遊んだ',te:'遊んで'
},'遊ぶ');

expectForms({kanji:'取る',reading:'とる',pos:'他動1'},{
  dict:'取る',masu:'取ります',nai:'取らない',ta:'取った',te:'取って',
  potential:'取れる',volitional:'取ろう',imperative:'取れ'
},'取る');

/* る-ending 五段 must not be treated as 一段 */
expectForms({kanji:'切る',reading:'きる',pos:'他動1'},{
  dict:'切る',masu:'切ります',nai:'切らない',te:'切って',potential:'切れる'
},'切る godan');
eq(conj.conjugate({kanji:'切る',reading:'きる',pos:'他動1'}).type,'godan','切る class');
eq(conj.conjugate({kanji:'着る',reading:'きる',pos:'他動2'}).type,'ichidan','着る class');

/* Irregular */
expectForms({kanji:'する',reading:'する',pos:'自他動3'},{
  dict:'する',masu:'します',nai:'しない',ta:'した',te:'して',
  potential:'できる',volitional:'しよう',imperative:'しろ',
  prohibitive:'するな',ba:'すれば',passive:'される',
  causative:'させる',causativePassive:'させられる'
},'する');

expectForms({kanji:'勉強する',reading:'べんきょうする',pos:'他動3'},{
  dict:'勉強する',masu:'勉強します',nai:'勉強しない',ta:'勉強した',te:'勉強して',
  potential:'勉強できる',volitional:'勉強しよう',imperative:'勉強しろ',
  prohibitive:'勉強するな',ba:'勉強すれば',passive:'勉強される',
  causative:'勉強させる',causativePassive:'勉強させられる'
},'勉強する');

expectForms({kanji:'運動',reading:'うんどう',pos:'名・自動3'},{
  dict:'運動する',masu:'運動します',nai:'運動しない',te:'運動して',potential:'運動できる'
},'運動 noun-suru');

expectForms({kanji:'説明する',reading:'せつめいする',pos:'他動3'},{
  dict:'説明する',masu:'説明します',nai:'説明しない',potential:'説明できる'
},'説明する');

expectForms({kanji:'来る',reading:'くる',pos:'自動3・補動'},{
  dict:'来る',masu:'来ます',nai:'来ない',ta:'来た',te:'来て',
  potential:'来られる',volitional:'来よう',imperative:'来い',
  prohibitive:'来るな',ba:'来れば',passive:'来られる',
  causative:'来させる',causativePassive:'来させられる'
},'来る');
expectReading({kanji:'来る',reading:'くる',pos:'自動3・補動'},{
  masu:'きます',nai:'こない',ta:'きた',te:'きて',volitional:'こよう',imperative:'こい'
},'来る');

expectForms({kanji:'行く',reading:'いく',pos:'自動1'},{
  dict:'行く',masu:'行きます',nai:'行かない',ta:'行った',te:'行って',
  potential:'行ける',volitional:'行こう',imperative:'行け',
  prohibitive:'行くな',ba:'行けば',passive:'行かれる',
  causative:'行かせる',causativePassive:'行かせられる'
},'行く');

expectForms({kanji:'ある',reading:'ある',pos:'自動1・補動'},{
  dict:'ある',masu:'あります',nai:'ない',ta:'あった',te:'あって',
  volitional:'あろう',imperative:'あれ',prohibitive:'あるな',ba:'あれば',
  potential:null,passive:null,causative:null,causativePassive:null
},'ある');

expectForms({kanji:'ない',reading:'ない',pos:'イ形・補形'},{
  dict:'ない',masu:'ありますせん',nai:'ない',ta:'なかった',te:'なくて',ba:'なければ',
  potential:null,imperative:null
},'ない');

/* Negative: nouns / adverbs / particles must not get 活用 */
['高校','庭','きれい','しかし','を','すぐ'].forEach(function(w,i){
  var samples=[
    {kanji:'高校',reading:'こうこう',pos:'名'},
    {kanji:'庭',reading:'にわ',pos:'noun'},
    {kanji:'きれい',reading:'きれい',pos:'ナ形'},
    {kanji:'しかし',reading:'しかし',pos:'接'},
    {kanji:'を',reading:'を',pos:'particle'},
    {kanji:'すぐ',reading:'すぐ',pos:'副'}
  ];
  eq(conj.canConjugate(samples[i]),false,'no conjugate '+samples[i].kanji);
});

eq(conj.canConjugate({kanji:'戦争',reading:'せんそう',pos:'verb'}),false,'戦争 tagged verb but not conjugatable');
eq(conj.canConjugate({kanji:'殺人',reading:'さつじん',pos:'verb'}),false,'殺人 tagged verb but not conjugatable');

/* Ambiguous kana-only きる without POS must fail safe */
eq(conj.canConjugate({kanji:'きる',reading:'きる',pos:''}),false,'ambiguous きる fails safe');

/* ふらふら 副・自動3 is primarily an adverb */
eq(conj.canConjugate({kanji:'ふらふら',reading:'ふらふら',pos:'副・ナ形・自動3'}),false,'adverb-suru fails safe');

if(failed){
  console.error('\n'+passed+' passed, '+failed+' failed');
  process.exit(1);
}
console.log('PASS '+passed+' assertions');
