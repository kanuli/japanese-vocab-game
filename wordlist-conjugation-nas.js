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
function chooseAsset(row,engine,voice){
  var audios=Array.isArray(row&&row.audios)?row.audios:[],i;
  for(i=0;i<audios.length;i++){
    if(audios[i]&&String(audios[i].engine||'')===engine&&String(audios[i].voice||'')===voice)return audios[i];
  }
  if(engine==='supertonic3'&&voice==='F3'&&row&&row.audio_url){
    return {audio_key:row.audio_key||'',engine:'supertonic3',voice:'F3',audio_url:row.audio_url};
  }
  return null;
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
async function chooseVoice(engine,selected){
  if(selected&&selected!=='random')return selected;
  var d=await fetchJson(NAS_BASE+'/api/v1/voices',5000);
  var rows=Array.isArray(d&&d.voices)?d.voices.filter(function(v){return v&&v.engine===engine;}):[];
  if(!rows.length)return '';
  return String(rows[Math.floor(Math.random()*rows.length)].voice||'');
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
      ok?resolve():reject(err||new Error('NAS playback failed'));
    }
    a.onended=function(){finish(true);};
    a.onerror=function(){finish(false,new Error('NAS playback failed'));};
    timer=setTimeout(function(){finish(false,new Error('NAS playback timeout'));},10000);
    var p=a.play();
    if(p&&p.catch)p.catch(function(err){finish(false,err);});
  });
}
function publishNasStatus(out){
  var W=root.WA||{},rec=W.lastSpeak||{};
  if(!rec.nas||!rec.playbackSuccess||rec.playbackFailure)return;
  var provider=String(rec.provider||out&&out.engine||'');
  var voice=String(rec.selectedVoice||rec.key||out&&out.key||'');
  var msg=rec.conjugation
    ? '✅ NAS Japanese API 動詞活用已播放｜'+provider+'｜'+voice
    : '✅ NAS Japanese API 已播放｜'+provider+'｜'+voice;
  var write=function(){
    var audioStatus=el('audioStatus'),voiceStatus=el('voiceStatus');
    if(audioStatus)audioStatus.textContent=msg;
    if(voiceStatus)voiceStatus.textContent=msg;
  };
  write();
  setTimeout(write,0);
}
function setLastSpeak(W,rec){
  W.lastSpeak=rec;
  if(root.W)root.W.lastSpeak=rec;
  if(root.WordlistConjugation)root.WordlistConjugation.lastSpeak=rec;
}
async function playVocabularyNas(W,text,w,engine,selected){
  var voice=await chooseVoice(engine,selected);
  if(!voice)throw new Error('NAS voice unavailable');
  var term=termOf(w);
  if(!term)throw new Error('NAS term unavailable');
  var lookupUrl=NAS_BASE+'/api/v1/vocabulary/'+encodeURIComponent(term)+'?engine='+encodeURIComponent(engine)+'&voice='+encodeURIComponent(voice);
  var d=await fetchJson(lookupUrl,5000);
  var row=chooseResult(d,w,text);
  var asset=chooseAsset(row,engine,voice);
  if(!asset||!asset.audio_url)throw new Error('NAS asset miss');
  var audioUrl=/^https?:\/\//i.test(asset.audio_url)?asset.audio_url:NAS_BASE+asset.audio_url;
  var st=el('voiceStatus');
  if(st)st.textContent='正在從 NAS Japanese API 讀取：'+readingOf(w,text)+'…';
  var got=await fetchBytes(audioUrl,7000);
  var speed=Number(el('speed')&&el('speed').value||1);
  if(!Number.isFinite(speed)||speed<=0)speed=1;
  await playBytes(got.bytes,speed);
  setLastSpeak(W,{
    requestedReading:String(text||''),
    selectedVoice:voice,
    provider:engine,
    resolvedAsset:String(asset.audio_key||''),
    resolvedUrl:audioUrl,
    hostedHit:true,
    hostedMiss:false,
    fallbackUsed:false,
    playbackSuccess:true,
    playbackFailure:false,
    pending:false,
    catalog:'nas-api',
    key:voice,
    httpStatus:got.status,
    nas:true,
    conjugation:false
  });
  var out={engine:engine,nas:true,key:voice,url:audioUrl};
  publishNasStatus(out);
  return out;
}
async function playConjugationNas(W,text,w){
  var term=termOf(w);
  if(!term)throw new Error('NAS conjugation term unavailable');
  var lookupUrl=NAS_BASE+'/api/v1/conjugation/'+encodeURIComponent(term)+'?engine=supertonic3&voice=F3';
  var d=await fetchJson(lookupUrl,5000);
  var row=chooseResult(d,w,text);
  if(!row||!row.audio_url)throw new Error('NAS conjugation asset miss');
  var audioUrl=/^https?:\/\//i.test(row.audio_url)?row.audio_url:NAS_BASE+row.audio_url;
  var st=el('voiceStatus');
  if(st)st.textContent='正在從 NAS Japanese API 讀取動詞活用 F3：'+readingOf(w,text)+'…';
  var got=await fetchBytes(audioUrl,7000);
  var speed=Number(el('speed')&&el('speed').value||1);
  if(!Number.isFinite(speed)||speed<=0)speed=1;
  await playBytes(got.bytes,speed);
  setLastSpeak(W,{
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
  });
  var out={engine:'supertonic3',nas:true,conjugation:true,key:'F3',url:audioUrl};
  publishNasStatus(out);
  return out;
}
function install(){
  var W=root.WA=root.WA||{};
  if(typeof W.speak!=='function'||W.__conjugationNasInstalled)return;
  W.__conjugationNasInstalled=true;
  var baseSpeak=W.speak,basePause=W.pause;

  W.speak=async function(text,overrideWord){
    if(!overrideWord)return baseSpeak.apply(W,arguments);
    var engine=String(el('audioEngine')&&el('audioEngine').value||'supertonic3');
    var selected=String(el('voice')&&el('voice').value||'');
    var isConj=inConjugationModal();

    if(isConj){
      if(engine!=='supertonic3'||selected!=='F3')return baseSpeak.apply(W,arguments);
      try{return await playConjugationNas(W,text,overrideWord);}
      catch(err){
        console.warn('NAS conjugation F3 failed; using existing GitHub/HF fallback',err);
        return baseSpeak.apply(W,arguments);
      }
    }

    if(engine==='device')return baseSpeak.apply(W,arguments);
    try{return await playVocabularyNas(W,text,overrideWord,engine,selected);}
    catch(err){
      console.warn('NAS primary word audio failed; using existing GitHub/HF fallback',err);
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
