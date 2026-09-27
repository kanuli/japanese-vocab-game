(function(root){
'use strict';
var NAS_BASE='https://kanu-rustdesk.synology.me:8443';
var localAudio=null,blobUrl='';

function el(id){return document.getElementById(id);}
function stopLocal(){
  if(localAudio){try{localAudio.pause();localAudio.currentTime=0;}catch(e){}localAudio=null;}
  if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}
}
function inConjugationModal(){
  var x=el('conjOverlay');
  return !!(x&&x.classList&&x.classList.contains('is-open'));
}
function termOf(w){return String(w&&(w.kanji||w.displayWord||w.word||w.reading)||'').trim();}
function readingOf(w,text){return String(w&&w.reading||text||'').trim();}
function chooseResult(d,w,text){
  var rows=Array.isArray(d&&d.results)?d.results:[];
  var term=termOf(w),reading=readingOf(w,text),i;
  for(i=0;i<rows.length;i++)if(String(rows[i].word||'')===term&&String(rows[i].reading||'')===reading)return rows[i];
  for(i=0;i<rows.length;i++)if(String(rows[i].word||'')===term)return rows[i];
  for(i=0;i<rows.length;i++)if(String(rows[i].reading||'')===reading)return rows[i];
  return rows[0]||null;
}
async function fetchJson(url,timeout){
  var c=typeof AbortController!=='undefined'?new AbortController():null;
  var t=c?setTimeout(function(){c.abort();},timeout||5000):null;
  try{
    var r=await fetch(url,{cache:'no-store',signal:c?c.signal:undefined});
    if(!r.ok)throw new Error('NAS HTTP '+r.status);
    return await r.json();
  }finally{if(t)clearTimeout(t);}
}
async function fetchBytes(url,timeout){
  var c=typeof AbortController!=='undefined'?new AbortController():null;
  var t=c?setTimeout(function(){c.abort();},timeout||7000):null;
  try{
    var r=await fetch(url,{cache:'force-cache',signal:c?c.signal:undefined});
    if(!r.ok)throw new Error('NAS audio HTTP '+r.status);
    var b=await r.arrayBuffer();
    if(!b.byteLength)throw new Error('NAS audio empty');
    return {bytes:b,status:r.status};
  }finally{if(t)clearTimeout(t);}
}
async function playBytes(bytes,speed){
  stopLocal();
  var g=root.MobileSupertonicGuard||{};
  if(g.isMobile&&typeof g.playHostedBytes==='function'){
    await g.playHostedBytes(bytes,speed);
    return;
  }
  blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));
  await new Promise(function(resolve,reject){
    var a=localAudio=new Audio(blobUrl),done=false,timer=null;
    a.playbackRate=speed;
    function finish(ok,err){
      if(done)return;done=true;
      if(timer)clearTimeout(timer);
      a.onended=a.onerror=null;
      if(localAudio===a)localAudio=null;
      ok?resolve():reject(err||new Error('NAS conjugation playback failed'));
    }
    a.onended=function(){finish(true);};
    a.onerror=function(){finish(false);};
    timer=setTimeout(function(){finish(false,new Error('NAS conjugation playback timeout'));},10000);
    var p=a.play();
    if(p&&p.catch)p.catch(function(err){finish(false,err);});
  });
}
function install(){
  var W=root.WA=root.WA||{};
  if(typeof W.speak!=='function'||W.__conjugationNasInstalled)return;
  W.__conjugationNasInstalled=true;
  var baseSpeak=W.speak,basePause=W.pause;

  W.speak=async function(text,overrideWord){
    var engine=String(el('audioEngine')&&el('audioEngine').value||'');
    var voice=String(el('voice')&&el('voice').value||'');
    if(!overrideWord||!inConjugationModal()||engine!=='supertonic3'||voice!=='F3'){
      return baseSpeak.apply(W,arguments);
    }

    var term=termOf(overrideWord);
    if(!term)return baseSpeak.apply(W,arguments);

    try{
      var lookupUrl=NAS_BASE+'/api/v1/conjugation/'+encodeURIComponent(term)+'?engine=supertonic3&voice=F3';
      var d=await fetchJson(lookupUrl,5000);
      var row=chooseResult(d,overrideWord,text);
      if(!row||!row.audio_url)return baseSpeak.apply(W,arguments);

      var audioUrl=/^https?:\/\//i.test(row.audio_url)?row.audio_url:NAS_BASE+row.audio_url;
      var st=el('voiceStatus');
      if(st)st.textContent='正在從 NAS Japanese API 讀取動詞活用 F3：'+readingOf(overrideWord,text)+'…';
      var got=await fetchBytes(audioUrl,7000);
      var speed=Number(el('speed')&&el('speed').value||1);
      if(!Number.isFinite(speed)||speed<=0)speed=1;
      await playBytes(got.bytes,speed);

      W.lastSpeak={
        requestedReading:String(text||''),
        selectedVoice:'F3',
        provider:'supertonic3',
        resolvedAsset:String(row.audio_key||''),
        resolvedUrl:audioUrl,
        hostedHit:true,
        hostedMiss:false,
        fallbackUsed:false,
        playbackSuccess:true,
        playbackFailure:false,
        pending:false,
        catalog:'nas-conjugation-api',
        key:'F3',
        httpStatus:got.status,
        nas:true,
        conjugation:true
      };
      if(root.W)root.W.lastSpeak=W.lastSpeak;
      if(root.WordlistConjugation)root.WordlistConjugation.lastSpeak=W.lastSpeak;
      if(st)st.textContent='✅ NAS Japanese API 動詞活用已播放｜supertonic3｜F3';
      return {engine:'supertonic3',nas:true,conjugation:true,key:'F3',url:audioUrl};
    }catch(err){
      console.warn('NAS conjugation F3 failed; using existing GitHub/HF fallback',err);
      return baseSpeak.apply(W,arguments);
    }
  };

  W.pause=function(){
    stopLocal();
    return typeof basePause==='function'?basePause.apply(W,arguments):undefined;
  };
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
else install();
})(typeof window!=='undefined'?window:this);
