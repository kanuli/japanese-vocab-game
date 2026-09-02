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

function expectForms(word,expected,label){
  var result=conj.conjugate(word);
  if(!result){
    failed++;
    console.error('FAIL',label,'— conjugate returned null for',word);
    return;
  }
  Object.keys(expected).forEach(function(id){
    var row=result.forms.find(function(x){return x.id===id;})
      ||(result.extended||[]).find(function(x){return x.id===id;});
    eq(row?row.written:undefined,expected[id],label+' '+id);
  });
}

function expectReading(word,expected,label){
  var result=conj.conjugate(word);
  if(!result){
    failed++;
    console.error('FAIL',label,'— conjugate returned null for',word);
    return;
  }
  Object.keys(expected).forEach(function(id){
    var row=result.forms.find(function(x){return x.id===id;})
      ||(result.extended||[]).find(function(x){return x.id===id;});
    eq(row?row.reading:undefined,expected[id],label+' reading '+id);
  });
}

function potentialOf(word){
  var result=conj.conjugate(word);
  var row=result&&result.forms.find(function(x){return x.id==='potential';});
  return row?row.written:undefined;
}

var TABERU_BASIC={
  dict:'食べる',masu:'食べます',nai:'食べない',ta:'食べた',te:'食べて',
  potential:'食べられる',volitional:'食べよう',imperative:'食べろ',
  prohibitive:'食べるな',ba:'食べれば',passive:'食べられる',
  causative:'食べさせる',causativePassive:'食べさせられる'
};
var TABERU_EXT={
  pastNai:'食べなかった',masuNai:'食べません',masuTa:'食べました',masuTaNai:'食べませんでした',
  teiru:'食べている',teita:'食べていた',tai:'食べたい',takunai:'食べたくない',
  tara:'食べたら',tekudasai:'食べてください',naidekudasai:'食べないでください',
  nakereba:'食べなければならない'
};

expectForms({kanji:'食べる',reading:'たべる',pos:'他動2'},TABERU_BASIC,'食べる');
expectForms({kanji:'食べる',reading:'たべる',pos:'他動2'},TABERU_EXT,'食べる ext');
expectReading({kanji:'食べる',reading:'たべる',pos:'他動2'},{
  masu:'たべます',nai:'たべない',te:'たべて',pastNai:'たべなかった',
  masuTa:'たべました',teiru:'たべている'
},'食べる');

expectForms({kanji:'見る',reading:'みる',pos:'他動2'},{
  dict:'見る',masu:'見ます',nai:'見ない',ta:'見た',te:'見て',
  potential:'見られる',volitional:'見よう',imperative:'見ろ',
  prohibitive:'見るな',ba:'見れば',passive:'見られる',
  causative:'見させる',causativePassive:'見させられる',
  pastNai:'見なかった',masuNai:'見ません',masuTa:'見ました',teiru:'見ている',tai:'見たい'
},'見る');

expectForms({kanji:'起きる',reading:'おきる',pos:'自動2'},{
  dict:'起きる',masu:'起きます',nai:'起きない',ta:'起きた',te:'起きて',
  potential:'起きられる',volitional:'起きよう',imperative:'起きろ',
  pastNai:'起きなかった',teiru:'起きている'
},'起きる');

expectForms({kanji:'着る',reading:'きる',pos:'他動2'},{
  dict:'着る',masu:'着ます',nai:'着ない',ta:'着た',te:'着て',potential:'着られる'
},'着る ichidan');
eq(conj.conjugate({kanji:'着る',reading:'きる',pos:'他動2'}).type,'ichidan','着る class');

expectForms({kanji:'書く',reading:'かく',pos:'他動1'},{
  dict:'書く',masu:'書きます',nai:'書かない',ta:'書いた',te:'書いて',
  potential:'書ける',volitional:'書こう',imperative:'書け',
  prohibitive:'書くな',ba:'書けば',passive:'書かれる',
  causative:'書かせる',causativePassive:'書かせられる',
  pastNai:'書かなかった',masuNai:'書きません',masuTa:'書きました',teiru:'書いている'
},'書く');

expectForms({kanji:'読む',reading:'よむ',pos:'他動1'},{
  dict:'読む',masu:'読みます',nai:'読まない',ta:'読んだ',te:'読んで',
  potential:'読める',volitional:'読もう',imperative:'読め',
  prohibitive:'読むな',ba:'読めば',passive:'読まれる',
  causative:'読ませる',causativePassive:'読ませられる',
  pastNai:'読まなかった',teiru:'読んでいる',tara:'読んだら'
},'読む');

expectForms({kanji:'話す',reading:'はなす',pos:'他動1'},{
  dict:'話す',masu:'話します',nai:'話さない',ta:'話した',te:'話して',
  potential:'話せる',volitional:'話そう',imperative:'話せ',
  prohibitive:'話すな',ba:'話せば',passive:'話される',
  causative:'話させる',causativePassive:'話させられる',
  pastNai:'話さなかった',teiru:'話している'
},'話す');

expectForms({kanji:'買う',reading:'かう',pos:'他動1'},{
  dict:'買う',masu:'買います',nai:'買わない',ta:'買った',te:'買って',
  potential:'買える',volitional:'買おう',imperative:'買え',
  prohibitive:'買うな',ba:'買えば',passive:'買われる',
  causative:'買わせる',causativePassive:'買わせられる',
  pastNai:'買わなかった',teiru:'買っている',tara:'買ったら'
},'買う');

expectForms({kanji:'泳ぐ',reading:'およぐ',pos:'自動1'},{
  dict:'泳ぐ',masu:'泳ぎます',nai:'泳がない',ta:'泳いだ',te:'泳いで',
  potential:'泳げる',volitional:'泳ごう',imperative:'泳げ',
  teiru:'泳いでいる',pastNai:'泳がなかった'
},'泳ぐ');

expectForms({kanji:'待つ',reading:'まつ',pos:'他動1'},{
  dict:'待つ',masu:'待ちます',nai:'待たない',ta:'待った',te:'待って',
  pastNai:'待たなかった',teiru:'待っている'
},'待つ');

expectForms({kanji:'死ぬ',reading:'しぬ',pos:'自動1'},{
  dict:'死ぬ',masu:'死にます',nai:'死なない',ta:'死んだ',te:'死んで',
  potential:'死ねる',volitional:'死のう',imperative:'死ね',
  teiru:'死んでいる'
},'死ぬ');

expectForms({kanji:'遊ぶ',reading:'あそぶ',pos:'自動1'},{
  dict:'遊ぶ',masu:'遊びます',nai:'遊ばない',ta:'遊んだ',te:'遊んで',
  teiru:'遊んでいる',pastNai:'遊ばなかった'
},'遊ぶ');

expectForms({kanji:'取る',reading:'とる',pos:'他動1'},{
  dict:'取る',masu:'取ります',nai:'取らない',ta:'取った',te:'取って',
  potential:'取れる',volitional:'取ろう',imperative:'取れ',
  teiru:'取っている'
},'取る');

expectForms({kanji:'切る',reading:'きる',pos:'他動1'},{
  dict:'切る',masu:'切ります',nai:'切らない',te:'切って',potential:'切れる'
},'切る godan');
eq(conj.conjugate({kanji:'切る',reading:'きる',pos:'他動1'}).type,'godan','切る class');
eq(conj.conjugate({kanji:'走る',reading:'はしる',pos:'自動1'}).type,'godan','走る class');
eq(conj.conjugate({kanji:'帰る',reading:'かえる',pos:'自動1'}).type,'godan','帰る class');
eq(conj.conjugate({kanji:'入る',reading:'はいる',pos:'自動1'}).type,'godan','入る class');
expectForms({kanji:'走る',reading:'はしる',pos:'自動1'},{
  masu:'走ります',nai:'走らない',te:'走って',potential:'走れる'
},'走る');
expectForms({kanji:'帰る',reading:'かえる',pos:'自動1'},{
  masu:'帰ります',nai:'帰らない',te:'帰って',ta:'帰った'
},'帰る');

expectForms({kanji:'する',reading:'する',pos:'自他動3'},{
  dict:'する',masu:'します',nai:'しない',ta:'した',te:'して',
  potential:'できる',volitional:'しよう',imperative:'しろ',
  prohibitive:'するな',ba:'すれば',passive:'される',
  causative:'させる',causativePassive:'させられる',
  pastNai:'しなかった',masuNai:'しません',masuTa:'しました',teiru:'している',tai:'したい'
},'する');

expectForms({kanji:'勉強する',reading:'べんきょうする',pos:'名・自他動3'},{
  dict:'勉強する',masu:'勉強します',nai:'勉強しない',ta:'勉強した',te:'勉強して',
  potential:'勉強できる',volitional:'勉強しよう',imperative:'勉強しろ',
  prohibitive:'勉強するな',ba:'勉強すれば',passive:'勉強される',
  causative:'勉強させる',causativePassive:'勉強させられる',
  pastNai:'勉強しなかった',teiru:'勉強している'
},'勉強する');

expectForms({kanji:'運動',reading:'うんどう',pos:'名・自動3'},{
  dict:'運動する',masu:'運動します',nai:'運動しない',te:'運動して',potential:'運動できる',
  pastNai:'運動しなかった'
},'運動 noun-suru');

expectForms({kanji:'説明する',reading:'せつめいする',pos:'名・他動3'},{
  dict:'説明する',masu:'説明します',nai:'説明しない',potential:'説明できる'
},'説明する');

eq(potentialOf({kanji:'達する',reading:'たっする',pos:'自他動3'})==='達できる',false,'達する not 達できる');
eq(potentialOf({kanji:'接する',reading:'せっする',pos:'自他動3'})==='接できる',false,'接する not 接できる');
eq(potentialOf({kanji:'発する',reading:'はっする',pos:'verb'})==='発できる',false,'発する not 発できる');
eq(potentialOf({kanji:'達する',reading:'たっする',pos:'自他動3'}),'達せられる','達する potential せられる');
eq(potentialOf({kanji:'接する',reading:'せっする',pos:'自他動3'}),'接せられる','接する potential せられる');
eq(potentialOf({kanji:'発する',reading:'はっする',pos:'verb'}),'発せられる','発する potential せられる');
expectForms({kanji:'達する',reading:'たっする',pos:'自他動3'},{
  dict:'達する',masu:'達します',nai:'達しない',ta:'達した',te:'達して',pastNai:'達しなかった'
},'達する lexical');

expectForms({kanji:'来る',reading:'くる',pos:'自動3・補動'},{
  dict:'来る',masu:'来ます',nai:'来ない',ta:'来た',te:'来て',
  potential:'来られる',volitional:'来よう',imperative:'来い',
  prohibitive:'来るな',ba:'来れば',passive:'来られる',
  causative:'来させる',causativePassive:'来させられる'
},'来る');
expectReading({kanji:'来る',reading:'くる',pos:'自動3・補動'},{
  masu:'きます',nai:'こない',ta:'きた',te:'きて',volitional:'こよう',imperative:'こい',
  masuNai:'きません',pastNai:'こなかった',teiru:'きている',tai:'きたい',
  tekudasai:'きてください',naidekudasai:'こないでください',nakereba:'こなければならない'
},'来る');
expectForms({kanji:'来る',reading:'くる',pos:'自動3・補動'},{
  masuNai:'来ません',pastNai:'来なかった',teiru:'来ている',tai:'来たい',
  tekudasai:'来てください',naidekudasai:'来ないでください',nakereba:'来なければならない'
},'来る ext written');

expectForms({kanji:'行く',reading:'いく',pos:'自動1'},{
  dict:'行く',masu:'行きます',nai:'行かない',ta:'行った',te:'行って',
  potential:'行ける',volitional:'行こう',imperative:'行け',
  prohibitive:'行くな',ba:'行けば',passive:'行かれる',
  causative:'行かせる',causativePassive:'行かせられる',
  teiru:'行っている',teita:'行っていた',tara:'行ったら',tekudasai:'行ってください'
},'行く');
eq(conj.conjugate({kanji:'行く',reading:'いく',pos:'自動1'}).extended.find(function(x){return x.id==='teiru';}).written,'行っている','行く ている not 行いている');

expectForms({kanji:'ある',reading:'ある',pos:'自動1・補動'},{
  dict:'ある',masu:'あります',nai:'ない',ta:'あった',te:'あって',
  volitional:'あろう',imperative:'あれ',prohibitive:'あるな',ba:'あれば',
  potential:null,passive:null,causative:null,causativePassive:null,
  pastNai:'なかった',masuNai:'ありません',masuTa:'ありました',tai:'ありたい'
},'ある');

eq(conj.canConjugate({kanji:'ない',reading:'ない',pos:'イ形・補形'}),false,'standalone ない is not a verb');
eq(conj.canConjugate({kanji:'ない',reading:'ない',pos:''}),false,'ない empty pos');
eq(conj.conjugate({kanji:'食べる',reading:'たべる',pos:'他動2'}).forms.find(function(x){return x.id==='nai';}).written,'食べない','verb ない形 kept');

['高校','庭','きれい','しかし','を','すぐ','ない'].forEach(function(w,i){
  var samples=[
    {kanji:'高校',reading:'こうこう',pos:'名'},
    {kanji:'庭',reading:'にわ',pos:'noun'},
    {kanji:'きれい',reading:'きれい',pos:'ナ形'},
    {kanji:'しかし',reading:'しかし',pos:'接'},
    {kanji:'を',reading:'を',pos:'particle'},
    {kanji:'すぐ',reading:'すぐ',pos:'副'},
    {kanji:'ない',reading:'ない',pos:'イ形・補形'}
  ];
  eq(conj.canConjugate(samples[i]),false,'no conjugate '+samples[i].kanji);
});

eq(conj.canConjugate({kanji:'戦争',reading:'せんそう',pos:'verb'}),false,'戦争 tagged verb but not conjugatable');
eq(conj.canConjugate({kanji:'殺人',reading:'さつじん',pos:'verb'}),false,'殺人 tagged verb but not conjugatable');
eq(conj.canConjugate({kanji:'きる',reading:'きる',pos:''}),false,'ambiguous きる fails safe');
eq(conj.canConjugate({kanji:'ふらふら',reading:'ふらふら',pos:'副・ナ形・自動3'}),false,'adverb-suru fails safe');

eq(conj.conjugate({kanji:'くださる',reading:'くださる',pos:'他動1'}).forms.find(function(x){return x.id==='masu';}).written,'くださいます','honorific くださる');

var query=conj.audioQuery('食べました','たべました');
eq(query.text,'たべました','speakForm uses kana reading');
eq(query.word.reading,'たべました','override reading is kana');
eq(query.word.kanji,'食べました','override keeps written');
eq(conj.lemmaKey({reading:'たべる',kanji:'食べる'}),'たべる|食べる','lemma W.key format unchanged');

var mockWords={
  'たべる|食べる':['lemma',0],
  'たべます|食べます':['masu',1]
};
var exact=conj.hostedLookup(mockWords,{reading:'たべます',kanji:'食べます'});
eq(exact&&exact.hit,'exact','hosted exact key hit');
eq(exact&&exact.entry[0],'masu','hosted exact entry');
var readingHit=conj.hostedLookup(mockWords,{reading:'たべます',kanji:'食べました'});
eq(readingHit&&readingHit.hit,'reading','hosted reading-only after exact miss');
eq(readingHit&&readingHit.entry[0],'masu','reading-only uses catalog clip');
var miss=conj.hostedLookup(mockWords,{reading:'たべました',kanji:'食べました'});
eq(miss,null,'hosted miss before device fallback');
var kata=conj.hostedLookup(mockWords,{reading:'タベマス',kanji:'X'});
eq(kata&&kata.hit,'reading','NFKC kata→hira reading lookup');

if(failed){
  console.error('\n'+passed+' passed, '+failed+' failed');
  process.exit(1);
}
console.log('PASS '+passed+' assertions');
