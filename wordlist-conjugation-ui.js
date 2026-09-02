(function(root){
'use strict';
if(typeof document==='undefined')return;
var api=root.WordlistConjugation;
if(!api)return;
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
/* -------- UI: stay on the vocabulary list; desktop modal / mobile sheet -------- */
if(typeof document==='undefined')return;

var overlay=null,dialog=null,titleEl=null,listEl=null,lastFocus=null,scrollSave=null,open=false;

function isMobile(){
  return window.matchMedia&&window.matchMedia('(max-width:820px)').matches;
}

function focusables(){
  if(!dialog)return [];
  return Array.prototype.slice.call(dialog.querySelectorAll('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')).filter(function(el){
    return !el.disabled&&el.offsetParent!==null;
  });
}

function lockScroll(){
  var wrap=document.querySelector('.table-wrap');
  scrollSave={
    x:window.scrollX||0,
    y:window.scrollY||0,
    table:wrap?wrap.scrollTop:0
  };
  document.body.style.top='-'+scrollSave.y+'px';
  document.body.style.position='fixed';
  document.body.style.left='0';
  document.body.style.right='0';
  document.body.style.width='100%';
}

function unlockScroll(){
  var y=scrollSave?scrollSave.y:0,x=scrollSave?scrollSave.x:0,table=scrollSave?scrollSave.table:0;
  document.body.style.position='';
  document.body.style.top='';
  document.body.style.left='';
  document.body.style.right='';
  document.body.style.width='';
  window.scrollTo(x,y);
  var wrap=document.querySelector('.table-wrap');
  if(wrap)wrap.scrollTop=table;
}

function closeModal(){
  if(!open||!overlay)return;
  open=false;
  overlay.classList.remove('is-open');
  overlay.setAttribute('hidden','');
  overlay.setAttribute('aria-hidden','true');
  unlockScroll();
  var focus=lastFocus;
  lastFocus=null;
  if(focus&&typeof focus.focus==='function'){
    try{focus.focus({preventScroll:true});}catch(e){try{focus.focus();}catch(e2){}}
  }
}

async function speakForm(ev,written,reading){
  if(ev){ev.preventDefault();ev.stopPropagation();}
  var W=root.WA||window.WA;
  var query=api.audioQuery?api.audioQuery(written,reading):{text:reading||written,word:{reading:reading||written,kanji:written||'',displayWord:written||reading}};
  var text=query.text;
  if(!text)return;
  var status=document.getElementById('audioStatus');
  if(status)status.textContent='🔊 正在播放：'+(written||text)+(reading&&reading!==written?'（'+reading+'）':'');
  try{
    if(!W||!W.speak){
      if(status)status.textContent='⚠️ 語音模組尚未載入。';
      return;
    }
    /* Speak kana. Hosted lookup tries exact reading|written then reading-only. */
    var used=await W.speak(text,query.word);
    if(status)status.textContent=used?'✅ 已播放：'+(written||text):'⚠️ 語音暫時無法播放。';
  }catch(e){
    if(status)status.textContent='⚠️ 播放失敗：'+(e&&e.message?e.message:String(e));
  }
}

function ensureModal(){
  if(overlay)return;
  overlay=document.createElement('div');
  overlay.id='conjOverlay';
  overlay.className='conj-overlay';
  overlay.setAttribute('hidden','');
  overlay.setAttribute('aria-hidden','true');
  overlay.innerHTML='<div class="conj-dialog" role="dialog" aria-modal="true" aria-labelledby="conjTitle" tabindex="-1">'
    +'<div class="conj-sheet-handle" aria-hidden="true"></div>'
    +'<div class="conj-head"><h2 id="conjTitle">動詞活用</h2>'
    +'<button type="button" class="conj-close" aria-label="關閉活用表">×</button></div>'
    +'<p class="conj-sub" id="conjSub"></p>'
    +'<div class="conj-body" id="conjList"></div></div>';
  document.body.appendChild(overlay);
  dialog=overlay.querySelector('.conj-dialog');
  titleEl=overlay.querySelector('#conjTitle');
  listEl=overlay.querySelector('#conjList');
  overlay.addEventListener('click',function(e){
    if(e.target===overlay)closeModal();
  });
  overlay.querySelector('.conj-close').addEventListener('click',function(e){
    e.preventDefault();
    e.stopPropagation();
    closeModal();
  });
  dialog.addEventListener('click',function(e){
    /* Keep audio / row clicks inside the dialog from reaching the backdrop. */
    e.stopPropagation();
  });
  document.addEventListener('keydown',function(e){
    if(!open)return;
    if(e.key==='Escape'){
      e.preventDefault();
      closeModal();
      return;
    }
    if(e.key!=='Tab')return;
    var nodes=focusables();
    if(!nodes.length)return;
    var first=nodes[0],last=nodes[nodes.length-1];
    if(e.shiftKey){
      if(document.activeElement===first||!dialog.contains(document.activeElement)){
        e.preventDefault();last.focus();
      }
    }else if(document.activeElement===last){
      e.preventDefault();first.focus();
    }
  });
}

function renderRow(row){
  if(!row.written){
    return '<div class="conj-row conj-row-na"><div class="conj-label">'+esc(row.label)
      +'</div><div class="conj-value muted">—</div></div>';
  }
  return '<div class="conj-row"><div class="conj-label">'+esc(row.label)+'</div>'
    +'<div class="conj-value"><span class="conj-written">'+esc(row.written)+'</span>'
    +(row.reading&&row.reading!==row.written?'<span class="conj-reading">'+esc(row.reading)+'</span>':'')
    +'<button type="button" class="btn conj-audio-btn" data-written="'+esc(row.written)+'" data-reading="'+esc(row.reading||row.written)+'" aria-label="播放 '+esc(row.written)+'">🔊</button>'
    +'</div></div>';
}

function renderSection(title,rows){
  var html='<section class="conj-section"><h3 class="conj-section-title">'+esc(title)+'</h3>'
    +'<div class="conj-list">';
  (rows||[]).forEach(function(row){html+=renderRow(row);});
  return html+'</div></section>';
}

function renderForms(result,sourceWord){
  var sub=overlay.querySelector('#conjSub');
  var shown=sourceWord.kanji||sourceWord.displayWord||sourceWord.reading||result.written;
  sub.textContent=shown+(result.reading&&result.reading!==shown?'　'+result.reading:'')
    +(sourceWord.meaning?'　'+sourceWord.meaning:'');
  listEl.innerHTML=renderSection('基本活用',result.forms)+renderSection('常用延伸',result.extended||[]);
  listEl.querySelectorAll('.conj-audio-btn').forEach(function(btn){
    btn.addEventListener('click',function(e){
      e.preventDefault();
      e.stopPropagation();
      speakForm(e,btn.getAttribute('data-written'),btn.getAttribute('data-reading'));
    });
  });
}

function openModal(word,opener){
  var result=api.conjugate(word);
  if(!result)return;
  ensureModal();
  lastFocus=opener||document.activeElement;
  lockScroll();
  renderForms(result,word);
  overlay.classList.toggle('is-sheet',isMobile());
  overlay.classList.add('is-open');
  overlay.removeAttribute('hidden');
  overlay.setAttribute('aria-hidden','false');
  open=true;
  var closeBtn=overlay.querySelector('.conj-close');
  try{(dialog||closeBtn).focus({preventScroll:true});}catch(e){try{(closeBtn||dialog).focus();}catch(e2){}}
}

function wordFromButton(btn){
  var W=root.WA||window.WA;
  var i=Number(btn&&btn.getAttribute('data-i'));
  var list=(W&&W.listView)||[];
  return list[i]||null;
}

function onBodyClick(e){
  var btn=e.target.closest&&e.target.closest('.conj-btn');
  if(!btn)return;
  e.preventDefault();
  e.stopPropagation();
  var word=wordFromButton(btn);
  if(word)openModal(word,btn);
}

document.addEventListener('click',onBodyClick,true);

api.open=openModal;
api.close=closeModal;
})(typeof window!=='undefined'?window:typeof global!=='undefined'?global:this);
