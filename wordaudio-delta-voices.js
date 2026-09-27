(function(){
'use strict';
function install(){
var W=window.WA=window.WA||{},baseSpeak=W.speak;
if(typeof baseSpeak!=='function')return;
if(W.__hostedDeltaVoiceInstalled)return;W.__hostedDeltaVoiceInstalled=true;
var CFG={
 voicevox:['./word-voicevox-delta-catalog.json?v=1','./word-voicevox-conj-catalog.json?v=1'],
 supertonic3:['./word-supertonic3-runtime-delta-catalog.json?v=2','./word-supertonic3-delta-catalog.json?v=1','./word-supertonic3-conj-catalog.json?v=2','./word-supertonic3-conj-v2-catalog.json?v=1'],
 aivis:['./word-aivis-delta-catalog.json?v=1','./word-aivis-conj-catalog.json?v=1']
};
var NAS_BASE='https://kanu-rustdesk.synology.me:8443';
var catalogs={},catalogPromises={},indexes=new Map(),audio=null,blobUrl='',nasVoices=null,nasVoicesPromise=null;
function el(id){return document.getElementById(id);}
function eng(){var x=el('audioEngine');return x?x.value:'supertonic3';}
function wordFor(text,override){if(override)return override;var w=W.list&&W.list[W.i];return w&&String(w.reading||'')===String(text||'')?w:null;}
function key(w){return w?(W.key?W.key(w):String(w.reading||'')+'|'+String(w.kanji||w.displayWord||w.reading||'')):'';}
function normReading(s){s=String(s==null?'':s);try{s=s.normalize('NFKC');}catch(e){}return s.replace(/[ァ-ヶ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-96);}).replace(/\s+/g,'');}
function readingIndex(c){if(c.__byReading)return c.__byReading;var idx={},words=c&&c.words||{},k,nr;for(k in words){if(!Object.prototype.hasOwnProperty.call(words,k))continue;nr=normReading(String(k).split('|')[0]);if(nr&&!idx[nr])idx[nr]=words[k];}c.__byReading=idx;return idx;}
function lookupDelta(c,w){if(!c||!c.words||!w)return null;var exact=c.words[key(w)];if(exact)return exact;var r=normReading(w.reading);if(!r)return null;return readingIndex(c)[r]||null;}
function group(c){return c?(c.voices||c.speakers||{}):{};}
function stop(){if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}
async function json(url){var r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
async function catalog(url){if(catalogs[url])return catalogs[url];if(catalogPromises[url])return catalogPromises[url];catalogPromises[url]=json(url).then(function(c){if(!c||c.status!=='ready'||!c.words)throw new Error('delta catalog not ready');c.__catalogUrl=url;catalogs[url]=c;return c;}).catch(function(){return null;});return catalogPromises[url];}
async function index(e,c,v){var source=c.__catalogUrl||'',ck=e+'|'+source+'|'+v,hit=indexes.get(ck);if(hit)return hit;var m=group(c)[v];if(!m)return null;var g=window.MobileSupertonicGuard||{},mobile=!!g.isMobile,url1=mobile?(m.indexHfUrl||m.indexGithubUrl||m.indexUrl):(m.indexGithubUrl||m.indexUrl||m.indexHfUrl),url2=mobile?(m.indexGithubUrl||m.indexUrl):(m.indexHfUrl||'');var d=null;try{d=await json(url1);}catch(err){if(url2)d=await json(url2);else throw err;}if(!d||!d.bundles)return null;indexes.set(ck,d);return d;}
async function bytes(bundle,offset,size){var end=offset+size-1,g=window.MobileSupertonicGuard||{},mobile=!!g.isMobile,urls=(mobile?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'}),len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size mismatch');bytes.lastUrl=urls[i];bytes.lastStatus=r.status;return b;}catch(e){last=e;}}throw last||new Error('delta audio download failed');}
function publishSpeak(rec){
  W.lastSpeak=rec;
  try{
    if(typeof window!=='undefined'){
      window.W=window.W||W;
      window.W.lastSpeak=rec;
      if(window.WordlistConjugation) window.WordlistConjugation.lastSpeak=rec;
    }
  }catch(err){}
  return rec;
}
async function playBuffer(b,speed,label){
  stop();
  var g=window.MobileSupertonicGuard||{};
  if(g.isMobile&&g.playHostedBytes){await g.playHostedBytes(b,speed);return;}
  blobUrl=URL.createObjectURL(new Blob([b],{type:'audio/mpeg'}));
  await new Promise(function(resolve,reject){
    var a=audio=new Audio(blobUrl),done=false;
    a.playbackRate=speed;
    function fin(ok,x){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(x||new Error(label||'playback failed'));}
    a.onended=function(){fin(true);};
    a.onerror=function(){fin(false,new Error(label||'playback failed'));};
    setTimeout(function(){fin(false,new Error('playback timeout'));},10000);
    var p=a.play();if(p&&p.catch)p.catch(function(x){fin(false,x);});
  });
}
async function nasJson(path){
  var controller=typeof AbortController!=='undefined'?new AbortController():null;
  var timer=controller?setTimeout(function(){controller.abort();},5000):null;
  try{
    var r=await fetch(NAS_BASE+path,{cache:'no-store',signal:controller?controller.signal:undefined});
    if(!r.ok)throw new Error('NAS HTTP '+r.status);
    return await r.json();
  }finally{if(timer)clearTimeout(timer);}
}
async function getNasVoices(){
  if(nasVoices)return nasVoices;
  if(nasVoicesPromise)return nasVoicesPromise;
  nasVoicesPromise=nasJson('/api/v1/voices').then(function(d){nasVoices=Array.isArray(d&&d.voices)?d.voices:[];return nasVoices;}).finally(function(){nasVoicesPromise=null;});
  return nasVoicesPromise;
}
function nasTerm(w){return String(w&&(w.kanji||w.displayWord||w.word||w.reading)||'');}
function selectNasResult(d,w){
  var rows=Array.isArray(d&&d.results)?d.results:[],targetWord=nasTerm(w),targetReading=String(w&&w.reading||'');
  for(var i=0;i<rows.length;i++)if(String(rows[i].word||'')===targetWord&&String(rows[i].reading||'')===targetReading)return rows[i];
  for(var j=0;j<rows.length;j++)if(String(rows[j].reading||'')===targetReading)return rows[j];
  return rows[0]||null;
}
async function chooseNasVoice(e,requested){
  if(requested&&requested!=='random')return requested;
  var vs=(await getNasVoices()).filter(function(v){return v&&v.engine===e;});
  if(!vs.length)return '';
  return String(vs[Math.floor(Math.random()*vs.length)].voice||'');
}
async function playNas(e,w){
  if(!w||e==='device')return null;
  var requested=(el('voice')&&el('voice').value)||'',v=await chooseNasVoice(e,requested);
  if(!v)return null;
  var term=nasTerm(w);if(!term)return null;
  var path='/api/v1/vocabulary/'+encodeURIComponent(term)+'?engine='+encodeURIComponent(e)+'&voice='+encodeURIComponent(v);
  var d=await nasJson(path),row=selectNasResult(d,w);if(!row)return null;
  var audios=Array.isArray(row.audios)?row.audios:[],asset=null;
  for(var i=0;i<audios.length;i++)if(audios[i]&&audios[i].engine===e&&audios[i].voice===v){asset=audios[i];break;}
  if(!asset||!asset.audio_url)return null;
  var url=/^https?:\/\//i.test(asset.audio_url)?asset.audio_url:NAS_BASE+asset.audio_url;
  var st=el('voiceStatus');if(st)st.textContent='正在從 NAS Japanese API 讀取：'+String(w.reading||'')+'…';
  var controller=typeof AbortController!=='undefined'?new AbortController():null;
  var timer=controller?setTimeout(function(){controller.abort();},7000):null;
  var r;
  try{r=await fetch(url,{cache:'force-cache',signal:controller?controller.signal:undefined});}
  finally{if(timer)clearTimeout(timer);}
  if(!r.ok)throw new Error('NAS audio HTTP '+r.status);
  var b=await r.arrayBuffer();if(!b.byteLength)throw new Error('NAS audio empty');
  var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;
  try{
    await playBuffer(b,speed,'NAS audio playback failed');
    publishSpeak({requestedReading:String(w.reading||''),selectedVoice:requested||v,provider:e,resolvedAsset:String(asset.audio_key||''),resolvedUrl:url,hostedHit:true,hostedMiss:false,fallbackUsed:false,playbackSuccess:true,playbackFailure:false,pending:false,seq:W.__speakSeq,catalog:'nas-api',key:v,httpStatus:r.status,nas:true});
  }catch(playErr){
    publishSpeak({requestedReading:String(w.reading||''),selectedVoice:requested||v,provider:e,resolvedAsset:String(asset.audio_key||''),resolvedUrl:url,hostedHit:true,hostedMiss:false,fallbackUsed:false,playbackSuccess:false,playbackFailure:true,pending:false,seq:W.__speakSeq,catalog:'nas-api',key:v,error:String(playErr&&playErr.message||playErr),nas:true});
    return{engine:e,nas:true,key:v,url:url,playbackFailure:true};
  }
  if(st)st.textContent='✅ NAS Japanese API 已播放｜'+e+'｜'+v;
  return{engine:e,nas:true,key:v,url:url};
}
async function play(e,w,url){var c=await catalog(url),lookup=lookupDelta(c,w);if(!lookup)return null;var all=Object.keys(group(c));if(!all.length)return null;var s=el('voice'),requested=s&&s.value,v;if(requested&&requested!=='random'){if(all.indexOf(requested)<0)return null;v=requested;}else{v=all[Math.floor(Math.random()*all.length)];}var idx=await index(e,c,v),bundle=idx&&idx.bundles&&idx.bundles[String(lookup[1])],member=bundle&&bundle.members&&bundle.members[lookup[0]];if(!member)return null;var b=await bytes(bundle,Number(member[0]),Number(member[1]));var usedUrl=bytes.lastUrl||'';stop();var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;var g=window.MobileSupertonicGuard||{};try{if(g.isMobile&&g.playHostedBytes){await g.playHostedBytes(b,speed);}else{blobUrl=URL.createObjectURL(new Blob([b],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;a.playbackRate=speed;function fin(ok,x){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(x||new Error('delta playback failed'));}a.onended=function(){fin(true);};a.onerror=function(){fin(false);};setTimeout(function(){fin(false,new Error('playback timeout'));},4000);var p=a.play();if(p&&p.catch)p.catch(function(x){fin(false,x);});});}publishSpeak({requestedReading:String(w.reading||''),selectedVoice:requested||v,provider:e,resolvedAsset:String(bundle.githubUrl||bundle.hfUrl||bundle.url||''),resolvedUrl:usedUrl,hostedHit:true,hostedMiss:false,fallbackUsed:false,playbackSuccess:true,playbackFailure:false,pending:false,seq:W.__speakSeq,catalog:url,key:v,httpStatus:bytes.lastStatus||0,delta:true});}catch(playErr){publishSpeak({requestedReading:String(w.reading||''),selectedVoice:requested||v,provider:e,resolvedUrl:usedUrl,hostedHit:true,hostedMiss:false,fallbackUsed:false,playbackSuccess:false,playbackFailure:true,pending:false,seq:W.__speakSeq,catalog:url,key:v,error:String(playErr&&playErr.message||playErr)});return{engine:e,delta:true,key:v,catalog:url,url:usedUrl,playbackFailure:true};}var st=el('voiceStatus');if(st)st.textContent='✅ 伺服器預錄單字聲線已播放。';return{engine:e,delta:true,key:v,catalog:url,url:usedUrl};}
W.speak=async function(text,overrideWord){var e=eng(),w=wordFor(text,overrideWord),urls=CFG[e]||[];W.__speakSeq=(W.__speakSeq||0)+1;publishSpeak({requestedReading:String(text||''),selectedVoice:(el('voice')&&el('voice').value)||'',provider:e,resolvedAsset:'',resolvedUrl:'',hostedHit:false,hostedMiss:false,fallbackUsed:false,playbackSuccess:false,playbackFailure:false,catalog:'',key:'',error:'',pending:true,seq:W.__speakSeq});if(w&&e!=='device'){try{var nas=await playNas(e,w);if(nas)return nas;}catch(nasErr){console.warn('NAS Japanese API failed; using GitHub/HF fallback',e,nasErr);}}if(w){for(var i=0;i<urls.length;i++){try{var x=await play(e,w,urls[i]);if(x)return x;}catch(err){console.warn('hosted delta voice failed',e,urls[i],err);}}}var out=await baseSpeak.apply(W,arguments);if(out&&out.engine==='device'){publishSpeak(Object.assign({},W.lastSpeak||{},{fallbackUsed:true,provider:'device',hostedHit:false,hostedMiss:true,pending:false,seq:W.__speakSeq}));}return out;};
var basePause=W.pause;W.pause=function(){stop();return typeof basePause==='function'?basePause.apply(W,arguments):undefined;};
window.JAPANESE_NAS_AUDIO={baseUrl:NAS_BASE,primary:true,fallback:'GitHub/HuggingFace',voices:getNasVoices};
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
