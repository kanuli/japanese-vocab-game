/* Word-list part-of-speech display (evidence-first).
 * Preserve combined dictionary POS; do not assume coarse 'adj' is always な形容詞
 * or that every い／え+る verb is 一段. */
(function(root){
'use strict';
var OVERRIDES={
  'すべて|全て':['名詞','副詞'],
  'すべて|すべて':['名詞','副詞'],
  'たぶん|多分':['副詞'],
  'たぶん|たぶん':['副詞'],
  'もともと|元々':['副詞'],
  'もともと|もともと':['副詞'],
  'すぐ|直ぐ':['副詞'],
  'すぐ|すぐ':['副詞'],
  'いろいろ|色々':['名詞','な形容詞','副詞'],
  'いろいろ|いろいろ':['名詞','な形容詞','副詞'],
  'たくさん|沢山':['名詞','副詞'],
  'たくさん|たくさん':['名詞','副詞'],
  'まっすぐ|真っ直ぐ':['な形容詞','副詞'],
  'まっすぐ|まっすぐ':['な形容詞','副詞'],
  'いっぱい|一杯':['名詞','副詞'],
  'いっぱい|いっぱい':['名詞','副詞'],
  'たいした|大した':['連體詞'],
  'べんきょう|勉強':['名詞','動詞（第3類）'],
  'うんどう|運動':['名詞','動詞（第3類）'],
  'そうじ|掃除':['名詞','動詞（第3類）'],
  'けんきゅう|研究':['名詞','動詞（第3類）'],
  'てんじんさま|天神様':['名詞']
};
var NA_EXCEPTIONS=new Set(['きれい','綺麗','嫌い','きらい','幸い','さいわい','丁寧','ていねい','有名','ゆうめい','綺麗','きれい','意外','いがい','大嫌い','だいきらい','得意','とくい']);
function rawPos(w){return String(w&&(w.pos||w.PoS||w.vocabPoS)||'').trim();}
function written(w){return String(w&&(w.kanji||w.displayWord||w.reading)||'').trim();}
function reading(w){return String(w&&w.reading||'').trim();}
function conjugationGroup(w,p){
  var m=p.match(/動([123])/);
  if(m)return m[1];
  var api=root.WordlistConjugation;
  if(!api||typeof api.classify!=='function')return null;
  var cls=api.classify(w);
  if(!cls)return null;
  if(cls.type==='godan'||cls.type==='iku'||cls.type==='aru'||cls.type==='honorific')return '1';
  if(cls.type==='ichidan')return '2';
  if(cls.type==='suru'||cls.type==='kuru')return '3';
  return null;
}
function adjectiveLabel(w,p){
  if(/(?:adj-i|i-adj|イ形|い形容詞)/i.test(p))return 'い形容詞';
  if(/(?:adj-na|na-adj|ナ形|な形容詞|形容動詞|形動)/i.test(p))return 'な形容詞';
  if(/(?:adj|形容詞|^形$)/i.test(p)){
    var s=written(w),r=reading(w);
    if(s.endsWith('い')&&r.endsWith('い')&&!NA_EXCEPTIONS.has(s)&&!NA_EXCEPTIONS.has(r))return 'い形容詞（推定）';
    return '形容詞（類型待核實）';
  }
  return null;
}
function labels(w){
  if(!w)return ['未分類'];
  var r=reading(w),s=written(w),override=OVERRIDES[r+'|'+s];
  if(override)return override.slice();
  var p=rawPos(w),out=[];
  function add(v){if(v&&out.indexOf(v)<0)out.push(v);}
  var tokens=p.split(/[・／/,;、+＆&\s]+/).filter(Boolean);
  tokens.forEach(function(t){
    if(/^(?:名|名詞|noun|n)$/i.test(t))add('名詞');
    else if(/^(?:副|副詞|adv|adverb)$/i.test(t))add('副詞');
    else if(/^(?:動[123]|動詞|verb|v[123]?)$/i.test(t))add('動詞');
    else if(/^(?:形|形容詞|形動|形容動詞|adj|adjective|adj-i|adj-na|i-adj|na-adj|イ形|ナ形|い形容詞|な形容詞)$/i.test(t))add('形容詞');
    else if(/^(?:conj|接|接續詞|接続詞)$/i.test(t))add('接續詞');
    else if(/^(?:particle|助|助詞)$/i.test(t))add('助詞');
    else if(/^(?:連體詞|連体詞|連體)$/i.test(t))add('連體詞');
    else if(/^(?:感動詞|interjection)$/i.test(t))add('感動詞');
  });
  // Mixed tags (e.g. 名・副・動3) have to survive, never first-match only.
  if(/(?:^|[・／,;、+＆&\s])動[123](?:$|[・／,;、+＆&\s])/.test(p)&&out.indexOf('動詞')<0)add('動詞');
  return out.map(function(t){
    if(t==='形容詞')return adjectiveLabel(w,p)||'形容詞（類型待核實）';
    if(t==='動詞'){var group=conjugationGroup(w,p);return group?'動詞（第'+group+'類）':'動詞（組別待核實）';}
    return t;
  }).filter(function(t,i,a){return a.indexOf(t)===i;}).length?out.map(function(t){
    if(t==='形容詞')return adjectiveLabel(w,p)||'形容詞（類型待核實）';
    if(t==='動詞'){var g=conjugationGroup(w,p);return g?'動詞（第'+g+'類）':'動詞（組別待核實）';}
    return t;
  }).filter(function(t,i,a){return a.indexOf(t)===i;}):['未分類'];
}
var api={labels:labels,rawPos:rawPos};
root.WordlistPOS=api;
if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:typeof global!=='undefined'?global:this);
