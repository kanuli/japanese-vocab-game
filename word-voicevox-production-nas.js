/* VOICEVOX production audio (43 voices, isolated NAS index). Legacy engines remain unchanged. */
(function(root){
'use strict';
var W=root.WA;
if(!W||typeof W.speak!=='function'||W.__voicevoxProductionNasInstalled)return;
var BASE='https://kanu-rustdesk.synology.me:8443';
var PATH='/api/v1/voicevox-production';
var oldSpeak=W.speak,oldPause=W.pause;
var audio=null,blobUrl='',requestNumber=0;
var VOICE_RE=/^s(?:0[1-9]|[1-3][0-9]|4[0-3])$/;
function el(id){return document.getElementById(id);}
function text(s){return String(s==null?'':s).trim();}
function normalize(s){s=text(s);try{s=s.normalize('NFKC');}catch(e){}return s;}
function stop(){
  if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}
  if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}
}
function track(rec){
  W.lastSpeak=rec;
  root.W=root.W||W;
  root.W.lastSpeak=rec;
  if(root.WordlistConjugation)root.WordlistConjugation.lastSpeak=rec;
}
function status(s){var x=el('voiceStatus');if(x)x.textContent=s;}
async function request(url,binary,timeout){
  var controller=typeof AbortController!=='undefined'?new AbortController():null;
  var timer=controller?setTimeout(function(){controller.abort();},timeout||10000):null;
  try{
    var result=await fetch(url,{cache:binary?'force-cache':'no-store',signal:controller?controller.signal:undefined});
    if(!result.ok)throw new Error('NAS HTTP '+result.status);
    return binary?result.arrayBuffer():result.json();
  }finally{if(timer)clearTimeout(timer);}
}
async function voiceOf(selected){
  if(selected&&selected!=='random'){
    if(!VOICE_RE.test(selected))throw new Error('Unknown VOICEVOX voice: '+selected);
    return selected;
  }
  var list=await request(BASE+PATH+'/voices',false,7000);
  var voices=(Array.isArray(list&&list.voices)?list.voices:[]).map(function(v){return text(v&&v.voice);}).filter(function(v){return VOICE_RE.test(v);});
  if(!voices.length)throw new Error('VOICEVOX production voices unavailable');
  return voices[Math.floor(Math.random()*voices.length)];
}
function pick(rows,reading,written){
  if(!rows.length)return null;
  var r=normalize(reading),w=normalize(written);
  var matches=rows.filter(function(x){return !x.reading||normalize(x.reading)===r;});
  if(!matches.length)return null;
  if(w){
    var exact=matches.find(function(x){return normalize(x.written||x.word||'')===w;});
    if(exact)return exact;
    var noWritten=matches.find(function(x){return !text(x.written||x.word||'');});
    if(noWritten)return noWritten;
  }
  return matches[0];
}
function assetUrl(row,voice){
  var url=text(row&&row.audio_url);
  var prefix=BASE+PATH+'/audio/'+encodeURIComponent(voice)+'/';
  if(url){
    if(url.slice(0,PATH.length+7)===PATH+'/audio/')url=BASE+url;
    if(url.indexOf(prefix)===0)return url;
  }
  var key=text(row&&(row.id||row.recording_id||row.audio_key||row.key));
  if(!key)throw new Error('Missing recording ID from production lookup');
  return prefix+encodeURIComponent(key);
}
async function playback(bytes,speed){
  stop();
  var g=root.MobileSupertonicGuard||{};
  if(g.isMobile&&typeof g.playHostedBytes==='function'){
    await g.playHostedBytes(bytes,speed);
    return;
  }
  blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));
  await new Promise(function(resolve,reject){
    var a=audio=new Audio(blobUrl),done=false,timer=null;
    a.playbackRate=speed;
    function finish(ok,err){
      if(done)return;done=true;
      if(timer)clearTimeout(timer);
      a.onended=a.onerror=null;
      if(audio===a)audio=null;
      if(blobUrl){URL.revokeObjectURL(blobUrl);blobUrl='';}
      if(ok)resolve();else reject(err||new Error('VOICEVOX playback failed'));
    }
    a.onended=function(){finish(true);};
    a.onerror=function(){finish(false,new Error('VOICEVOX media error'));};
    timer=setTimeout(function(){finish(false,new Error('VOICEVOX playback timeout'));},30000);
    try{var play=a.play();if(play&&play.catch)play.catch(function(err){finish(false,err);});}
    catch(e){finish(false,e);}
  });
}
W.speak=async function(reading,overrideWord){
  var engine=text(el('audioEngine')&&el('audioEngine').value);
  if(engine!=='voicevox')return oldSpeak.apply(W,arguments);
  var thisRequest=++requestNumber;
  var w=overrideWord||((W.list&&W.list[W.i]&&normalize(W.list[W.i].reading)===normalize(reading))?W.list[W.i]:null);
  var kana=text(w&&w.reading)||text(reading);
  var written=text(w&&(w.kanji||w.displayWord||w.word));
  var selected=text(el('voice')&&el('voice').value);
  var conjunct=!!(el('conjOverlay')&&el('conjOverlay').classList&&el('conjOverlay').classList.contains('is-open'));
  try{
    if(!kana)throw new Error('Missing recording reading');
    var voice=await voiceOf(selected);
    var lookup=await request(BASE+PATH+'/lookup/'+encodeURIComponent(kana)+'?voice='+encodeURIComponent(voice),false,7000);
    var result=pick(Array.isArray(lookup&&lookup.results)?lookup.results:[],kana,written);
    if(!result)throw new Error('No VOICEVOX production recording for '+kana);
    var url=assetUrl(result,voice);
    status('🔊 NAS VOICEVOX｜'+voice+'｜'+kana);
    var bytes=await request(url,true,15000);
    if(bytes.byteLength<100)throw new Error('Empty VOICEVOX MP3');
    var speed=Number(el('speed')&&el('speed').value||1);
    if(!Number.isFinite(speed)||speed<=0)speed=1;
    if(thisRequest!==requestNumber)return null;
    await playback(bytes,speed);
    track({requestedReading:kana,selectedVoice:voice,provider:'voicevox',engine:'voicevox',resolvedAsset:text(result.id||result.recording_id||result.audio_key),resolvedUrl:url,hostedHit:true,hostedMiss:false,fallbackUsed:false,playbackSuccess:true,playbackFailure:false,pending:false,catalog:'voicevox-production-nas',key:voice,nas:true,conjugation:conjunct,httpStatus:200});
    status('✅ NAS VOICEVOX 已播放｜'+voice+'｜'+kana);
    return {engine:'voicevox',nas:true,key:voice,url:url};
  }catch(err){
    console.warn('VOICEVOX production NAS unavailable; trying existing audio provider',err);
    if(thisRequest!==requestNumber)return null;
    status('VOICEVOX 新錄音未命中，正在使用原有預錄音…');
    return oldSpeak.apply(W,arguments);
  }
};
W.pause=function(){++requestNumber;stop();return typeof oldPause==='function'?oldPause.apply(W,arguments):undefined;};
W.__voicevoxProductionNasInstalled=true;
root.VOICEVOX_PRODUCTION_NAS={version:1,baseUrl:BASE,apiPath:PATH};
})(typeof window!=='undefined'?window:this);
