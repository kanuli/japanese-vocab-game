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
  if(!t) return esc(text);
  try{return t.tokenize(String(text||'')).map(tokenRuby).join('');}
  catch(err){console.warn(err);return esc(text);}
}

async function render(el,text){
  if(!el) return;
  const serial=++renderSerial;
  el.textContent=String(text||'');
  const html=await rubyHTML(text);
  if(serial!==renderSerial) return;
  el.innerHTML=html;
}

window.PronunciationFurigana={init:init,render:render,rubyHTML:rubyHTML,ready:function(){return !!tokenizer;}};
ensureStyle();
init();
})();
