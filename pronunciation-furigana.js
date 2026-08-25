(function(){
'use strict';
let tokenizer=null;
let initPromise=null;
let renderSerial=0;

function kataToHira(s){
  return String(s||'').replace(/[\u30a1-\u30f6]/g,function(ch){
    return String.fromCharCode(ch.charCodeAt(0)-0x60);
  });
}

function esc(s){
  return String(s??'').replace(/[&<>"']/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}

function tokenRuby(t){
  const surf=t.surface_form||'';
  const rd=t.reading&&t.reading!=='*'?kataToHira(t.reading):'';
  if(!rd||!/[一-龯々]/.test(surf)) return esc(surf);

  let k=surf.length;
  while(k>0&&/[ぁ-ゖァ-ヺー]/.test(surf[k-1])) k--;
  const stem=surf.slice(0,k);
  const suffix=surf.slice(k);
  const hiraSuffix=kataToHira(suffix);

  if(stem&&hiraSuffix&&rd.endsWith(hiraSuffix)){
    const rubyReading=rd.slice(0,-hiraSuffix.length);
    if(rubyReading) return '<ruby>'+esc(stem)+'<rt>'+esc(rubyReading)+'</rt></ruby>'+esc(suffix);
  }
  return '<ruby>'+esc(surf)+'<rt>'+esc(rd)+'</rt></ruby>';
}

const MONTH_READINGS={1:'いちがつ',2:'にがつ',3:'さんがつ',4:'しがつ',5:'ごがつ',6:'ろくがつ',7:'しちがつ',8:'はちがつ',9:'くがつ',10:'じゅうがつ',11:'じゅういちがつ',12:'じゅうにがつ'};
const SPECIAL_DAY_READINGS={1:'ついたち',2:'ふつか',3:'みっか',4:'よっか',5:'いつか',6:'むいか',7:'なのか',8:'ようか',9:'ここのか',10:'とおか',14:'じゅうよっか',20:'はつか',24:'にじゅうよっか'};
function dayNumberReading(n){
  const ones={0:'',1:'いち',2:'に',3:'さん',4:'よん',5:'ご',6:'ろく',7:'しち',8:'はち',9:'く'};
  if(n<10)return ones[n]||'';
  if(n<20)return 'じゅう'+(ones[n-10]||'');
  if(n<30)return 'にじゅう'+(ones[n-20]||'');
  if(n<=31)return 'さんじゅう'+(ones[n-30]||'');
  return '';
}
function dayReading(n){return SPECIAL_DAY_READINGS[n]||((dayNumberReading(n)||String(n))+'にち');}
function calendarRubyHTML(text,renderPlain){
  const s=String(text||'');
  const re=/(\d{1,2})月(\d{1,2})日/g;
  let out='',last=0,m;
  while((m=re.exec(s))){
    const month=Number(m[1]),day=Number(m[2]);
    if(month<1||month>12||day<1||day>31)continue;
    out+=renderPlain(s.slice(last,m.index));
    out+='<ruby>'+esc(m[1]+'月')+'<rt>'+esc(MONTH_READINGS[month])+'</rt></ruby>';
    out+='<ruby>'+esc(m[2]+'日')+'<rt>'+esc(dayReading(day))+'</rt></ruby>';
    last=m.index+m[0].length;
  }
  out+=renderPlain(s.slice(last));
  return out;
}

function ensureStyle(){
  if(document.getElementById('pronunciation-furigana-style')) return;
  const style=document.createElement('style');
  style.id='pronunciation-furigana-style';
  style.textContent='.sentence ruby{ruby-position:over;margin:0 .02em}.sentence rt{font-family:-apple-system,BlinkMacSystemFont,"Yu Gothic UI","Noto Sans JP",sans-serif;font-size:.48em;line-height:1;color:#596579;font-weight:700}.sentence{padding-top:.35em}';
  document.head.appendChild(style);
}

function init(){
  ensureStyle();
  if(tokenizer) return Promise.resolve(tokenizer);
  if(initPromise) return initPromise;
  initPromise=new Promise(function(resolve,reject){
    if(typeof window.kuromoji==='undefined'){
      reject(new Error('kuromoji.js not loaded'));
      return;
    }
    window.kuromoji.builder({dicPath:'./dict/'}).build(function(err,t){
      if(err){reject(err);return;}
      tokenizer=t;
      resolve(t);
    });
  }).catch(function(err){
    console.warn('Pronunciation furigana unavailable:',err);
    initPromise=null;
    return null;
  });
  return initPromise;
}

async function rubyHTML(text){
  const t=tokenizer||await init();
  const renderPlain=function(segment){
    if(!segment)return '';
    if(!t)return esc(segment);
    try{return t.tokenize(segment).map(tokenRuby).join('');}
    catch(err){console.warn(err);return esc(segment);}
  };
  return calendarRubyHTML(text,renderPlain);
}

async function render(el,text){
  if(!el) return;
  const serial=++renderSerial;
  el.textContent=String(text||'');
  const html=await rubyHTML(text);
  if(serial!==renderSerial) return;
  el.innerHTML=html;
}

window.PronunciationFurigana={init:init,render:render,rubyHTML:rubyHTML,ready:function(){return !!tokenizer;},dayReading:dayReading};
ensureStyle();
init();
})();
