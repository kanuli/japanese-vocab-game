/* Verb conjugation for the vocabulary list page.
   Generate forms from dictionary form + verb class + explicit exceptions.
   Do not store all 12 conjugated forms on every vocab item. */
(function(root){
'use strict';

var FORM_DEFS=[
  ['dict','辭書形（原形）'],
  ['masu','ます形'],
  ['nai','ない形'],
  ['ta','た形'],
  ['te','て形'],
  ['potential','可能形'],
  ['volitional','意向形（意志形）'],
  ['imperative','命令形'],
  ['prohibitive','禁止形'],
  ['ba','條件形（ば形）'],
  ['passive','受身形（被動形）'],
  ['causative','使役形'],
  ['causativePassive','使役被動形']
];

var GODAN={
  'う':{a:'わ',i:'い',e:'え',o:'お',te:'って',ta:'った'},
  'く':{a:'か',i:'き',e:'け',o:'こ',te:'いて',ta:'いた'},
  'ぐ':{a:'が',i:'ぎ',e:'げ',o:'ご',te:'いで',ta:'いだ'},
  'す':{a:'さ',i:'し',e:'せ',o:'そ',te:'して',ta:'した'},
  'つ':{a:'た',i:'ち',e:'て',o:'と',te:'って',ta:'った'},
  'ぬ':{a:'な',i:'に',e:'ね',o:'の',te:'んで',ta:'んだ'},
  'ぶ':{a:'ば',i:'び',e:'べ',o:'ぼ',te:'んで',ta:'んだ'},
  'む':{a:'ま',i:'み',e:'め',o:'も',te:'んで',ta:'んだ'},
  'る':{a:'ら',i:'り',e:'れ',o:'ろ',te:'って',ta:'った'}
};

/* Well-known 五段 verbs that end with い/え + る. POS 動1 still wins when present. */
var GODAN_RU={
  '切る':1,'走る':1,'入る':1,'要る':1,'帰る':1,'返る':1,'減る':1,'焦る':1,
  '限る':1,'蹴る':1,'滑る':1,'握る':1,'練る':1,'参る':1,'散る':1,'湿る':1,
  '茂る':1,'照る':1,'知る':1,'足る':1,'しゃべる':1,'喋る':1,'混じる':1,
  '交じる':1,'嘲る':1,'遮る':1,'罵る':1,'捻る':1,'翻る':1,'蘇る':1,
  '滅入る':1,'漲る':1,'滾る':1,'弄る':1,'貪る':1,'覆る':1,'契る':1,
  '詰る':1,'選る':1,'煎る':1,'炒る':1,'要る':1,'交る':1,'喋る':1,
  'ねじる':1,'ひねる':1,'かじる':1,'かじる':1,'齧る':1,'詰る':1
};

var HONORIFIC={
  'くださる':{masu:'くださいます',imperative:'ください'},
  'なさる':{masu:'なさいます',imperative:'なさい'},
  'いらっしゃる':{masu:'いらっしゃいます',imperative:'いらっしゃい'},
  'おっしゃる':{masu:'おっしゃいます',imperative:'おっしゃい'},
  'ござる':{masu:'ございます',imperative:'ござい'}
};

var IE_ROW='いきぎしじちぢにひびぴみりえけげせぜてでねへべぺめれ';
var KANA_RE=/^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$/;
var NON_VERB_POS=/^(noun|adj|adv|conj|particle|other|名$|イ形|ナ形|副$|接$|代$|感$|連体|接頭|接尾|造$|連語|成句|形動|助詞|助動)/i;

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function toHira(s){return String(s||'').replace(/[ァ-ヶ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-96);});}
function isKana(s){return !!s&&KANA_RE.test(String(s).replace(/\s+/g,''));}
function writtenOf(w){return String((w&&(w.kanji||w.displayWord||w.reading))||'').trim();}
function readingOf(w){return toHira(String((w&&w.reading)||'').trim());}
function posOf(w){return String((w&&(w.pos||w.PoS||w.vocabPoS))||'').trim();}

function form(written,reading){
  if(!written&&!reading)return null;
  return {written:written||reading,reading:reading||written};
}

function replaceEnd(s,end,rep){
  s=String(s||'');
  if(end&&s.length>=end.length&&s.slice(-end.length)===end)return s.slice(0,-end.length)+rep;
  return null;
}

function pair(written,reading,from,to){
  var r=replaceEnd(reading,from,to);
  if(r==null)return null;
  var w=replaceEnd(written,from,to);
  if(w==null)w=written?written+to:r;
  return form(w,r);
}

function pack(dict,map){
  var out={},i,id;
  for(i=0;i<FORM_DEFS.length;i++){
    id=FORM_DEFS[i][0];
    out[id]=map[id]==null?null:map[id];
  }
  out.dict=out.dict||dict;
  return out;
}

function ichidanForms(written,reading){
  var dict=form(written,reading);
  var stemW=written.slice(0,-1),stemR=reading.slice(0,-1);
  function add(suffix){return form(stemW+suffix,stemR+suffix);}
  return pack(dict,{
    dict:dict,
    masu:add('ます'),
    nai:add('ない'),
    ta:add('た'),
    te:add('て'),
    potential:add('られる'),
    volitional:add('よう'),
    imperative:add('ろ'),
    prohibitive:form(written+'な',reading+'な'),
    ba:add('れば'),
    passive:add('られる'),
    causative:add('させる'),
    causativePassive:add('させられる')
  });
}

function godanForms(written,reading,ending,teOverride){
  var row=GODAN[ending];
  if(!row)return null;
  var dict=form(written,reading);
  var te=teOverride&&teOverride.te||row.te;
  var ta=teOverride&&teOverride.ta||row.ta;
  function stem(kind,extra){return pair(written,reading,ending,row[kind]+(extra||''));}
  return pack(dict,{
    dict:dict,
    masu:stem('i','ます'),
    nai:stem('a','ない'),
    ta:pair(written,reading,ending,ta),
    te:pair(written,reading,ending,te),
    potential:stem('e','る'),
    volitional:stem('o','う'),
    imperative:stem('e',''),
    prohibitive:form(written+'な',reading+'な'),
    ba:stem('e','ば'),
    passive:stem('a','れる'),
    causative:stem('a','せる'),
    causativePassive:stem('a','せられる')
  });
}

function suruForms(prefixW,prefixR){
  function add(s){return form(prefixW+s,prefixR+s);}
  var dict=add('する');
  return pack(dict,{
    dict:dict,
    masu:add('します'),
    nai:add('しない'),
    ta:add('した'),
    te:add('して'),
    potential:add('できる'),
    volitional:add('しよう'),
    imperative:add('しろ'),
    prohibitive:add('するな'),
    ba:add('すれば'),
    passive:add('される'),
    causative:add('させる'),
    causativePassive:add('させられる')
  });
}

function kuruFormsSimple(written,reading){
  /* written is 来る or ～来る / ～くる; reading ends with くる. */
  var wPrefix='',rPrefix='';
  if(reading.endsWith('くる'))rPrefix=reading.slice(0,-2);
  if(written.endsWith('来る'))wPrefix=written.slice(0,-2);
  else if(written.endsWith('くる'))wPrefix=written.slice(0,-2);
  else wPrefix=rPrefix;
  function F(wSuf,rSuf){
    var w=wPrefix+(written.endsWith('来る')||written==='来る'?wSuf:rSuf);
    if(!wPrefix&&(written==='来る'||written==='くる'))w=(written==='来る'?wSuf:rSuf);
    if(written.endsWith('来る'))w=wPrefix+wSuf;
    else if(written.endsWith('くる'))w=wPrefix+rSuf;
    else w=wPrefix+wSuf;
    return form(w,rPrefix+rSuf);
  }
  var dict=form(written,reading);
  return pack(dict,{
    dict:dict,
    masu:F('来ます','きます'),
    nai:F('来ない','こない'),
    ta:F('来た','きた'),
    te:F('来て','きて'),
    potential:F('来られる','こられる'),
    volitional:F('来よう','こよう'),
    imperative:F('来い','こい'),
    prohibitive:F('来るな','くるな'),
    ba:F('来れば','くれば'),
    passive:F('来られる','こられる'),
    causative:F('来させる','こさせる'),
    causativePassive:F('来させられる','こさせられる')
  });
}

function aruForms(written,reading){
  var dict=form(written||'ある',reading||'ある');
  var w=dict.written,r=dict.reading;
  function swap(from,toW,toR){
    return form(replaceEnd(w,from,toW)||toW,replaceEnd(r,from,toR)||toR);
  }
  return pack(dict,{
    dict:dict,
    masu:swap('ある','あります','あります'),
    nai:form('ない','ない'),
    ta:swap('ある','あった','あった'),
    te:swap('ある','あって','あって'),
    potential:null,
    volitional:swap('ある','あろう','あろう'),
    imperative:swap('ある','あれ','あれ'),
    prohibitive:form(w+'な',r+'な'),
    ba:swap('ある','あれば','あれば'),
    passive:null,
    causative:null,
    causativePassive:null
  });
}

function naiForms(){
  var dict=form('ない','ない');
  return pack(dict,{
    dict:dict,
    masu:form('ありません','ありません'),
    nai:form('ない','ない'),
    ta:form('なかった','なかった'),
    te:form('なくて','なくて'),
    potential:null,
    volitional:null,
    imperative:null,
    prohibitive:null,
    ba:form('なければ','なければ'),
    passive:null,
    causative:null,
    causativePassive:null
  });
}

function verbGroup(pos){
  pos=String(pos||'');
  var m=pos.match(/動([123])/);
  if(!m)return null;
  return m[1];
}

function looksLikeAdverbSuru(pos){
  pos=String(pos||'');
  return /動3/.test(pos)&&/(^副|副・)/.test(pos)&&!/名/.test(pos);
}

function isNonVerb(pos){
  pos=String(pos||'').trim();
  if(!pos)return false;
  if(/動[123]/.test(pos))return false;
  if(/^(verb|動詞)/i.test(pos))return false;
  return NON_VERB_POS.test(pos)||/^(noun|adj|adv|conj|particle|other)$/i.test(pos);
}

function endsWithGodan(reading){
  var last=reading.slice(-1);
  return Object.prototype.hasOwnProperty.call(GODAN,last)?last:null;
}

function writtenHasOkurigana(written,ending){
  if(!written||!ending)return false;
  return written===ending||written.endsWith(ending);
}

function classify(word){
  var written=writtenOf(word),reading=readingOf(word),pos=posOf(word);
  if(!reading||!isKana(reading))return null;

  var wKey=written,rKey=reading,group=verbGroup(pos);

  if((wKey==='ない'||rKey==='ない')&&(wKey==='ない'||/イ形|adj|補形/.test(pos))){
    return {type:'nai',written:'ない',reading:'ない'};
  }
  if(isNonVerb(pos))return null;
  if(looksLikeAdverbSuru(pos))return null;
  if(wKey==='ある'||(rKey==='ある'&&(!pos||/動1|verb|補動/.test(pos)))){
    if(wKey==='ある'||wKey==='')return {type:'aru',written:written||'ある',reading:'ある'};
  }

  if(HONORIFIC[rKey]||HONORIFIC[wKey]){
    return {type:'honorific',written:written||reading,reading:reading,honorific:HONORIFIC[wKey]||HONORIFIC[rKey]};
  }

  if(wKey==='来る'||rKey==='くる'||wKey.endsWith('来る')||rKey.endsWith('くる')){
    if(wKey==='来る'||rKey==='くる'||wKey.endsWith('来る')||(rKey.endsWith('くる')&&(group==='3'||wKey.endsWith('来る')||wKey.endsWith('くる')))){
      if(!(rKey.endsWith('くる')&&group==='1'))return {type:'kuru',written:written||'来る',reading:reading};
    }
  }

  if(wKey==='する'||rKey==='する'||wKey.endsWith('する')||rKey.endsWith('する')){
    return {type:'suru',written:written.endsWith('する')?written:written+'する',reading:reading.endsWith('する')?reading:reading+'する'};
  }

  if(group==='3'){
    /* 名・動3 and similar: conjugate as ～する rather than inventing a godan/ichidan form. */
    if(/名/.test(pos)||pos.indexOf('動3')>=0){
      if(!wKey.endsWith('する')&&!rKey.endsWith('する')&&!wKey.endsWith('来る')&&rKey!=='くる'){
        return {type:'suru',written:written+'する',reading:reading+'する'};
      }
    }
    return null;
  }

  if(wKey==='行く'||wKey==='いく'||(rKey==='いく'&&(wKey==='行く'||wKey==='いく'||group==='1'))){
    return {type:'iku',written:written||'行く',reading:rKey==='いく'||rKey==='ゆく'?rKey:'いく'};
  }
  if(rKey==='ゆく'&&(wKey==='行く'||wKey==='ゆく')){
    return {type:'iku',written:written||'行く',reading:'ゆく'};
  }

  if(group==='2'){
    if(!reading.endsWith('る'))return null;
    return {type:'ichidan',written:written,reading:reading};
  }
  if(group==='1'){
    var end1=endsWithGodan(reading);
    if(!end1)return null;
    return {type:'godan',written:written,reading:reading,ending:end1};
  }

  /* No textbook group: conservative shape rules. Never assume every る verb is 一段. */
  if(/^(verb|動詞)/i.test(pos)||!pos){
    if(reading.endsWith('する'))return {type:'suru',written:written.endsWith('する')?written:written+'する',reading:reading};
    if(written==='来る'||reading==='くる')return {type:'kuru',written:written,reading:reading};
    if(written==='行く'||reading==='いく'||reading==='ゆく')return {type:'iku',written:written,reading:reading};
    var end=endsWithGodan(reading);
    if(!end)return null;
    if(!writtenHasOkurigana(written,end)&&written!==reading)return null;
    if(end!=='る')return {type:'godan',written:written,reading:reading,ending:end};
    var stem=reading.slice(0,-1);
    var ie=stem&&IE_ROW.indexOf(stem.slice(-1))>=0;
    if(GODAN_RU[written]||GODAN_RU[reading])return {type:'godan',written:written,reading:reading,ending:'る'};
    if(!ie)return {type:'godan',written:written,reading:reading,ending:'る'};
    /* い/え + る without POS group or exception list is ambiguous (着る vs 切る). Fail safe. */
    if(/^(verb|動詞)/i.test(pos)&&!GODAN_RU[written]&&written!==reading){
      /* Distinct kanji that is not a known 五段 exception: treat as 一段. */
      return {type:'ichidan',written:written,reading:reading};
    }
    return null;
  }
  return null;
}

function applyHonorific(base,honorific){
  if(!base||!honorific)return base;
  if(honorific.masu){
    base.masu=form(
      replaceEnd(base.dict.written,'る','います')||honorific.masu,
      honorific.masu
    );
    if(base.dict.written.endsWith('る'))base.masu=form(base.dict.written.slice(0,-1)+'います',honorific.masu);
  }
  if(honorific.imperative){
    base.imperative=form(
      base.dict.written.endsWith('る')?base.dict.written.slice(0,-1)+'い':honorific.imperative,
      honorific.imperative
    );
  }
  return base;
}

function conjugate(word){
  var cls=classify(word);
  if(!cls)return null;
  var forms=null;
  if(cls.type==='ichidan')forms=ichidanForms(cls.written,cls.reading);
  else if(cls.type==='godan')forms=godanForms(cls.written,cls.reading,cls.ending);
  else if(cls.type==='iku')forms=godanForms(cls.written,cls.reading,'く',{te:'って',ta:'った'});
  else if(cls.type==='suru'){
    var pw=cls.written.endsWith('する')?cls.written.slice(0,-2):cls.written;
    var pr=cls.reading.endsWith('する')?cls.reading.slice(0,-2):cls.reading;
    forms=suruForms(pw,pr);
  }
  else if(cls.type==='kuru')forms=kuruFormsSimple(cls.written,cls.reading);
  else if(cls.type==='aru')forms=aruForms(cls.written,cls.reading);
  else if(cls.type==='nai')forms=naiForms();
  else if(cls.type==='honorific'){
    forms=godanForms(cls.written,cls.reading,'る');
    forms=applyHonorific(forms,cls.honorific);
  }
  if(!forms)return null;
  var rows=[],i,id,label,item;
  for(i=0;i<FORM_DEFS.length;i++){
    id=FORM_DEFS[i][0];label=FORM_DEFS[i][1];item=forms[id];
    rows.push({id:id,label:label,written:item?item.written:null,reading:item?item.reading:null});
  }
  if(!rows[0].written)return null;
  return {type:cls.type,written:cls.written,reading:cls.reading,forms:rows};
}

function canConjugate(word){
  var result=conjugate(word);
  return !!(result&&result.forms&&result.forms[0]&&result.forms[0].written);
}

var api={
  FORM_DEFS:FORM_DEFS,
  classify:classify,
  conjugate:conjugate,
  canConjugate:canConjugate
};

if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.WordlistConjugation=api;
})(typeof window!=='undefined'?window:typeof global!=='undefined'?global:this);
