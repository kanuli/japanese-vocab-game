/* Adjective inflection and noun copular-expression tables for the vocabulary list.
   Extends WordlistConjugation without changing the established verb engine. */
(function(root){
'use strict';
var api=root.WordlistConjugation;
if(!api)return;
var originalConjugate=api.conjugate;
var originalCanConjugate=api.canConjugate;
var originalOpen=api.open;

function text(v){return String(v==null?'':v).trim();}
function writtenOf(w){return text(w&&(w.kanji||w.displayWord||w.reading));}
function readingOf(w){return text(w&&w.reading);}
function posOf(w){return text(w&&(w.pos||w.PoS||w.vocabPoS));}
function form(w,r){return {written:w,reading:r||w};}
function row(id,label,w,r){var f=form(w,r);return {id:id,label:label,written:f.written,reading:f.reading};}
function suffixPair(baseW,baseR,wSuffix,rSuffix){return form(baseW+wSuffix,baseR+(rSuffix==null?wSuffix:rSuffix));}

function adjectiveKind(word){
  var pos=posOf(word);
  if(/(?:^|[・／,\s])(?:イ形|い形容詞|形容詞)(?:$|[・／,\s])/.test(pos)||/^(?:adj-i|i-adj)$/i.test(pos))return 'i-adj';
  if(/(?:^|[・／,\s])(?:ナ形|な形容詞|形動|形容動詞)(?:$|[・／,\s])/.test(pos)||/^(?:adj-na|na-adj)$/i.test(pos))return 'na-adj';
  return null;
}
function isNoun(word){
  var pos=posOf(word);
  return /(?:^|[・／,\s])名(?:$|[・／,\s])/.test(pos)||/^(?:noun|名詞)$/i.test(pos);
}

function iAdjective(word){
  var w=writtenOf(word),r=readingOf(word);
  if(!w||!r||!r.endsWith('い'))return null;
  var irregular=(r==='いい'||r.endsWith('いい'));
  var stemR=irregular?r.slice(0,-2)+'よ':r.slice(0,-1);
  var stemW;
  if(irregular){
    if(w==='いい')stemW='よ';
    else if(w.endsWith('いい'))stemW=w.slice(0,-2)+'よ';
    else if(w.endsWith('良い'))stemW=w.slice(0,-1);
    else stemW=w.slice(0,-1);
  }else stemW=w.slice(0,-1);
  function F(s){return suffixPair(stemW,stemR,s,s);}
  var forms=[
    row('dict','基本形',w,r),
    row('negative','否定形',F('くない').written,F('くない').reading),
    row('past','過去形',F('かった').written,F('かった').reading),
    row('pastNegative','過去否定形',F('くなかった').written,F('くなかった').reading),
    row('te','て形／連用形',F('くて').written,F('くて').reading),
    row('adverbial','副詞形',F('く').written,F('く').reading),
    row('conditional','條件形（ば）',F('ければ').written,F('ければ').reading)
  ];
  var extended=[
    row('polite','丁寧形',w+'です',r+'です'),
    row('politeNegative','丁寧否定形',F('くないです').written,F('くないです').reading),
    row('politePast','丁寧過去形',F('かったです').written,F('かったです').reading),
    row('politePastNegative','丁寧過去否定形',F('くなかったです').written,F('くなかったです').reading)
  ];
  return {type:'i-adj',category:'adjective',title:'い形容詞活用',written:w,reading:r,forms:forms,extended:extended};
}

function naAdjective(word){
  var w=writtenOf(word),r=readingOf(word);if(!w||!r)return null;
  var forms=[
    row('plain','普通形',w+'だ',r+'だ'),
    row('negative','否定形',w+'ではない',r+'ではない'),
    row('past','過去形',w+'だった',r+'だった'),
    row('pastNegative','過去否定形',w+'ではなかった',r+'ではなかった'),
    row('attributive','連體形（名詞前）',w+'な',r+'な'),
    row('adverbial','副詞形',w+'に',r+'に'),
    row('conditional','條件形',w+'なら',r+'なら')
  ];
  var extended=[
    row('polite','丁寧形',w+'です',r+'です'),
    row('politeNegative','丁寧否定形',w+'ではありません',r+'ではありません'),
    row('politePast','丁寧過去形',w+'でした',r+'でした'),
    row('politePastNegative','丁寧過去否定形',w+'ではありませんでした',r+'ではありませんでした')
  ];
  return {type:'na-adj',category:'adjective',title:'な形容詞活用',written:w,reading:r,forms:forms,extended:extended};
}

function nounExpressions(word){
  var w=writtenOf(word),r=readingOf(word);if(!w||!r)return null;
  var forms=[
    row('plain','普通形',w+'だ',r+'だ'),
    row('negative','否定形',w+'ではない',r+'ではない'),
    row('past','過去形',w+'だった',r+'だった'),
    row('pastNegative','過去否定形',w+'ではなかった',r+'ではなかった'),
    row('conditional','條件表現',w+'なら',r+'なら')
  ];
  var extended=[
    row('polite','丁寧形',w+'です',r+'です'),
    row('politeNegative','丁寧否定形',w+'ではありません',r+'ではありません'),
    row('politePast','丁寧過去形',w+'でした',r+'でした'),
    row('politePastNegative','丁寧過去否定形',w+'ではありませんでした',r+'ではありませんでした')
  ];
  return {type:'noun',category:'noun',title:'名詞＋判定表現',written:w,reading:r,forms:forms,extended:extended};
}

api.conjugate=function(word){
  var verb=originalConjugate(word);
  if(verb){verb.category=verb.category||'verb';verb.title=verb.title||'動詞活用';return verb;}
  var kind=adjectiveKind(word);
  if(kind==='i-adj')return iAdjective(word);
  if(kind==='na-adj')return naAdjective(word);
  if(isNoun(word))return nounExpressions(word);
  return null;
};
api.canConjugate=function(word){return !!api.conjugate(word);};
api.inflectionKind=function(word){var r=api.conjugate(word);return r?r.type:null;};

if(originalOpen){
  api.open=function(word,opener){
    var result=api.conjugate(word);
    if(!result)return;
    originalOpen(word,opener);
    var title=document.getElementById('conjTitle');
    if(title)title.textContent=result.title||'活用・表現';
    var basic=document.querySelector('#conjList .conj-section-title');
    if(basic)basic.textContent=result.category==='noun'?'基本判定表現':(result.category==='adjective'?'基本活用':'基本活用');
    var sections=document.querySelectorAll('#conjList .conj-section-title');
    if(sections.length>1&&result.category==='noun')sections[1].textContent='丁寧表現';
    else if(sections.length>1&&result.category==='adjective')sections[1].textContent='丁寧表現';
  };
}
})(typeof window!=='undefined'?window:typeof global!=='undefined'?global:this);
