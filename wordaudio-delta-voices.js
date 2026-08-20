(function(){
'use strict';
var W=window.WA=window.WA||{},baseSpeak=W.speak;
if(typeof baseSpeak!=='function')return;
var CFG={
 voicevox:'./word-voicevox-delta-catalog.json?v=1',
 supertonic3:'./word-supertonic3-delta-catalog.json?v=1',
 aivis:'./word-aivis-delta-catalog.json?v=1'
};
var catalogs={},catalogPromises={},indexes=new Map(),audio=null,blobUrl='';
function el(id){return document.getElementById(id);}
function eng(){var x=el('audioEngine');return x?x.value:'supertonic3';}
function wordFor(text,override){if(override)return override;var w=W.list&&W.list[W.i];return w&&String(w.reading||'')===String(text||'')?w:null;}
function key(w){return w?(W.key?W.key(w):String(w.reading||'')+'|'+String(w.kanji||w.displayWord||w.reading||'')):'';}
function group(c){return c?(c.voices||c.speakers||{}):{};}
function stop(){if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}
async function json(url){var r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
async function catalog(e){if(catalogs[e])return catalogs[e];if(catalogPromises[e])return catalogPromises[e];catalogPromises[e]=json(CFG[e]).then(function(c){if(!c||c.status!=='ready'||!c.words)throw new Error('delta catalog not ready');catalogs[e]=c;return c;}).catch(function(){return null;});return catalogPromises[e];}
async function index(e,c,v){var ck=e+'|'+v,hit=indexes.get(ck);if(hit)return hit;var m=group(c)[v];if(!m)return null;var g=window.MobileSupertonicGuard||{},mobile=!!g.isMobile,url1=mobile?(m.indexHfUrl||m.indexGithubUrl||m.indexUrl):(m.indexGithubUrl||m.indexUrl||m.indexHfUrl),url2=mobile?(m.indexGithubUrl||m.indexUrl):(m.indexHfUrl||'');var d=null;try{d=await json(url1);}catch(err){if(url2)d=await json(url2);else throw err;}if(!d||!d.bundles)return null;indexes.set(ck,d);return d;}
async function bytes(bundle,offset,size){var end=offset+size-1,g=window.MobileSupertonicGuard||{},mobile=!!g.isMobile,urls=(mobile?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'}),len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size mismatch');return b;}catch(e){last=e;}}throw last||new Error('delta audio download failed');}
async function play(e,w){var c=await catalog(e),lookup=c&&c.words&&c.words[key(w)];if(!lookup)return null;var all=Object.keys(group(c));if(!all.length)return null;var s=el('voice'),requested=s&&s.value,v=requested&&requested!=='random'&&all.indexOf(requested)>=0?requested:all[Math.floor(Math.random()*all.length)],idx=await index(e,c,v),bundle=idx&&idx.bundles&&idx.bundles[String(lookup[1])],member=bundle&&bundle.members&&bundle.members[lookup[0]];if(!member)return null;var b=await bytes(bundle,Number(member[0]),Number(member[1]));stop();var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;var g=window.MobileSupertonicGuard||{};if(g.isMobile&&g.playHostedBytes){await g.playHostedBytes(b,speed);}else{blobUrl=URL.createObjectURL(new Blob([b],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;a.playbackRate=speed;function fin(ok,x){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(x||new Error('delta playback failed'));}a.onended=function(){fin(true);};a.onerror=function(){fin(false);};var p=a.play();if(p&&p.catch)p.catch(function(x){fin(false,x);});});}var st=el('voiceStatus');if(st)st.textContent='✅ 新增單字預錄聲線已播放。';return{engine:e,delta:true,key:v};}
W.speak=async function(text,overrideWord){var e=eng(),w=wordFor(text,overrideWord);if(CFG[e]&&w){try{var x=await play(e,w);if(x)return x;}catch(err){console.warn('hosted delta voice failed',e,err);}}return baseSpeak.apply(W,arguments);};
var basePause=W.pause;W.pause=function(){stop();return typeof basePause==='function'?basePause.apply(W,arguments):undefined;};
})();
