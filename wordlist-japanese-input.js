(function(){'use strict';
var input=document.getElementById('search');
if(!input)return;

/* Mobile keyboards remain under iOS/Android control, but these hints make the
   field explicitly Japanese-oriented and remove English autocorrect noise. */
input.setAttribute('lang','ja');
input.setAttribute('inputmode','text');
input.setAttribute('enterkeyhint','search');
input.setAttribute('autocomplete','off');
input.setAttribute('autocapitalize','off');
input.setAttribute('autocorrect','off');
input.setAttribute('spellcheck','false');
input.setAttribute('aria-label','日本語單字搜尋：可輸入漢字、假名、Romaji 或繁體中文');
input.placeholder='搜尋原形／變化形、漢字、假名、Romaji 或繁體中文意思';

/* Add a consistent clear button instead of relying on browser-specific
   type=search controls, which are not equally visible on mobile browsers. */
var wrap=document.createElement('div');
wrap.className='word-search-wrap';
input.parentNode.insertBefore(wrap,input);
wrap.appendChild(input);
var clear=document.createElement('button');
clear.type='button';
clear.className='word-search-clear';
clear.setAttribute('aria-label','清除搜尋');
clear.setAttribute('title','清除搜尋');
clear.textContent='×';
wrap.appendChild(clear);
function updateClear(){clear.classList.toggle('visible',!!input.value);}

/* Lightweight Hepburn/keyboard-style Romaji -> Hiragana conversion.
   It only converts lowercase ASCII segments, so uppercase acronyms such as AI
   and non-Latin searches remain untouched. */
function romajiSegmentToHiragana(s){
  if(s==='konnichiwa')return 'こんにちは';
  if(s==='konbanwa')return 'こんばんは';
  var map={
    kya:'きゃ',kyu:'きゅ',kyo:'きょ',gya:'ぎゃ',gyu:'ぎゅ',gyo:'ぎょ',
    sha:'しゃ',shu:'しゅ',sho:'しょ',sya:'しゃ',syu:'しゅ',syo:'しょ',
    ja:'じゃ',ju:'じゅ',jo:'じょ',ji:'じ',jya:'じゃ',jyu:'じゅ',jyo:'じょ',
    cha:'ちゃ',chu:'ちゅ',cho:'ちょ',cya:'ちゃ',cyu:'ちゅ',cyo:'ちょ',
    tya:'ちゃ',tyu:'ちゅ',tyo:'ちょ',nya:'にゃ',nyu:'にゅ',nyo:'にょ',
    hya:'ひゃ',hyu:'ひゅ',hyo:'ひょ',bya:'びゃ',byu:'びゅ',byo:'びょ',
    pya:'ぴゃ',pyu:'ぴゅ',pyo:'ぴょ',mya:'みゃ',myu:'みゅ',myo:'みょ',
    rya:'りゃ',ryu:'りゅ',ryo:'りょ',shi:'し',chi:'ち',tsu:'つ',dzu:'づ',
    she:'しぇ',che:'ちぇ',je:'じぇ',fa:'ふぁ',fi:'ふぃ',fe:'ふぇ',fo:'ふぉ',
    fyu:'ふゅ',va:'ゔぁ',vi:'ゔぃ',vu:'ゔ',ve:'ゔぇ',vo:'ゔぉ',
    ti:'てぃ',tu:'とぅ',di:'でぃ',du:'どぅ',wi:'うぃ',we:'うぇ',wo:'を',
    ka:'か',ki:'き',ku:'く',ke:'け',ko:'こ',ga:'が',gi:'ぎ',gu:'ぐ',ge:'げ',go:'ご',
    sa:'さ',si:'し',su:'す',se:'せ',so:'そ',za:'ざ',zi:'じ',zu:'ず',ze:'ぜ',zo:'ぞ',
    ta:'た',te:'て',to:'と',da:'だ',de:'で',do:'ど',na:'な',ni:'に',nu:'ぬ',ne:'ね',no:'の',
    ha:'は',hi:'ひ',hu:'ふ',fu:'ふ',he:'へ',ho:'ほ',ba:'ば',bi:'び',bu:'ぶ',be:'べ',bo:'ぼ',
    pa:'ぱ',pi:'ぴ',pu:'ぷ',pe:'ぺ',po:'ぽ',ma:'ま',mi:'み',mu:'む',me:'め',mo:'も',
    ya:'や',yu:'ゆ',yo:'よ',ra:'ら',ri:'り',ru:'る',re:'れ',ro:'ろ',wa:'わ',
    a:'あ',i:'い',u:'う',e:'え',o:'お'
  };
  var out='',i=0;
  while(i<s.length){
    var c=s.charAt(i),next=s.charAt(i+1);
    if(c==='n'){
      if(next==="'"){out+='ん';i+=2;continue;}
      if(!next){out+='ん';i++;continue;}
      if(next==='n'){out+='ん';i++;continue;}
      if(!/[aeiouy]/.test(next)){out+='ん';i++;continue;}
    }
    if(next&&c===next&&/[bcdfghjkmprstvwxyz]/.test(c)&&c!=='n'){
      out+='っ';i++;continue;
    }
    var hit='',kana='';
    for(var len=3;len>=1;len--){
      var part=s.substr(i,len);
      if(map[part]){hit=part;kana=map[part];break;}
    }
    if(hit){out+=kana;i+=hit.length;}else{out+=c;i++;}
  }
  return out;
}
function convertRomajiInput(value){
  return String(value||'').replace(/[a-z']+/g,function(seg){return romajiSegmentToHiragana(seg);});
}

/* The legacy word-list attaches an immediate oninput render. Intercept trusted
   typing in capture phase, then release one synthetic input event after a short
   idle period. This prevents filter + deinflection + sort work on every key. */
var searchTimer=0,SEARCH_DELAY=180;
function fireSearch(){
  clearTimeout(searchTimer);
  searchTimer=0;
  var ev=new Event('input',{bubbles:true});
  ev.__wordlistDebounced=true;
  input.dispatchEvent(ev);
}
function scheduleSearch(delay){
  clearTimeout(searchTimer);
  searchTimer=setTimeout(fireSearch,delay==null?SEARCH_DELAY:delay);
}
input.addEventListener('input',function(e){
  if(e&&e.__wordlistDebounced){updateClear();return;}
  if(e)e.stopImmediatePropagation();
  if(!(e&&e.isComposing)){
    var converted=convertRomajiInput(input.value);
    if(converted!==input.value){
      input.value=converted;
      try{input.setSelectionRange(converted.length,converted.length);}catch(err){}
    }
  }
  updateClear();
  if(!(e&&e.isComposing))scheduleSearch();
},true);
input.addEventListener('compositionend',function(){
  updateClear();
  scheduleSearch(80);
},true);

clear.addEventListener('click',function(){
  clearTimeout(searchTimer);
  input.value='';
  updateClear();
  fireSearch();
  input.focus({preventScroll:true});
});
updateClear();
})();
