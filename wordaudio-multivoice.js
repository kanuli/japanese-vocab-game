(function(){
'use strict';
var W=window.WA=window.WA||{};
var oldPause=W.pause;
var catalogs={voicevox:null,supertonic3:null,aivis:null};
var catalogState={voicevox:'idle',supertonic3:'idle',aivis:'idle'};
var indexCache=new Map(),hostedAudio=null,hostedBlobUrl='',deviceUtterance=null;
var CFG={
 voicevox:{label:'🎭 VOICEVOX｜伺服器預錄',catalog:'./word-voicevox-catalog.json?v=2',group:'speakers'},
 supertonic3:{label:'✨ Supertonic 3｜伺服器預錄',catalog:'./word-supertonic3-catalog.json?v=1',group:'voices'},
 aivis:{label:'💠 AivisSpeech / Style-Bert-VITS｜伺服器預錄',catalog:'./word-aivis-catalog.json?v=1',group:'voices'},
 device:{label:'🔊 裝置 Japanese voice｜緊急備援'}
};
function el(id){return document.getElementById(id);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function status(msg){var x=el('voiceStatus');if(x)x.textContent=msg;}
function sampleStatus(msg){var x=el('sampleVoiceStatus');if(x)x.textContent=msg;}
function guard(){return window.MobileSupertonicGuard||{isMobile:false};}
function stopHosted(){if(guard().isMobile&&guard().stopHostedAudio)try{guard().stopHostedAudio();}catch(e){}if(hostedAudio){try{hostedAudio.pause();hostedAudio.currentTime=0;}catch(e){}hostedAudio=null;}if(hostedBlobUrl){try{URL.revokeObjectURL(hostedBlobUrl);}catch(e){}hostedBlobUrl='';}}
function stopDevice(){try{if('speechSynthesis' in window)speechSynthesis.cancel();}catch(e){}deviceUtterance=null;}
function stopAll(){stopHosted();stopDevice();if(W.audio){try{W.audio.pause();W.audio.currentTime=0;}catch(e){}W.audio=null;}}
function engine(){var x=el('audioEngine');return x?x.value:'supertonic3';}
function wordFor(text,override){if(override)return override;var w=W.list&&W.list[W.i];if(w&&String(w.reading||'')===String(text||''))return w;return null;}
function wordKey(w){return w?(W.key?W.key(w):String(w.reading||'')+'|'+String(w.kanji||w.displayWord||w.reading||'')):'';}
function group(c){if(!c)return{};if(c.voices)return c.voices;if(c.speakers)return c.speakers;return{};}
function keys(c){return Object.keys(group(c));}
function voiceName(v,key){v=v||{};return String(v.displayName||v.speaker||v.name||key)+(v.style?'｜'+v.style:'');}
async function getJson(url){var r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
async function getJsonFallback(a,b){try{return await getJson(a);}catch(e){if(!b)throw e;return getJson(b);}}
async function loadCatalog(eng){if(!CFG[eng]||!CFG[eng].catalog)return null;if(catalogState[eng]==='ready')return catalogs[eng];if(catalogState[eng]==='loading'){for(var n=0;n<100&&catalogState[eng]==='loading';n++)await new Promise(function(r){setTimeout(r,50);});return catalogs[eng];}catalogState[eng]='loading';try{var c=await getJson(CFG[eng].catalog);catalogs[eng]=c;if(c&&c.status==='ready'&&c.words&&keys(c).length){catalogState[eng]='ready';return c;}catalogState[eng]='building';return c||null;}catch(e){catalogState[eng]=e&&/HTTP 404/.test(String(e.message||e))?'missing':'error';return null;}}
async function loadIndex(eng,key){var cacheKey=eng+'|'+key;if(indexCache.has(cacheKey))return indexCache.get(cacheKey);var c=catalogs[eng],v=group(c)[key];if(!v)throw new Error('聲線索引不存在');var m=!!guard().isMobile,url1=m?(v.indexHfUrl||v.indexGithubUrl||v.indexUrl||''):(v.indexGithubUrl||v.indexUrl||v.indexHfUrl||''),url2=m?(v.indexGithubUrl||v.indexUrl||''):(v.indexHfUrl||'');if(!url1&&!url2)throw new Error('聲線索引網址不存在');var d=await getJsonFallback(url1,url2);if(!d||!d.bundles)throw new Error('聲線索引格式錯誤');indexCache.set(cacheKey,d);return d;}
async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=(guard().isMobile?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('音訊下載失敗');}
async function playHosted(eng,w){var c=await loadCatalog(eng);if(!c||c.status!=='ready'||!w)return null;var lookup=c.words&&c.words[wordKey(w)];if(!lookup)return null;var id=lookup[0],shard=String(lookup[1]),all=keys(c),sel=el('voice'),requested=sel&&sel.value;var key=requested&&requested!=='random'?requested:all[Math.floor(Math.random()*all.length)];if(all.indexOf(key)<0)key=all[0];if(!key)return null;var idx=await loadIndex(eng,key),bundle=idx.bundles&&idx.bundles[shard],member=bundle&&bundle.members&&bundle.members[id];if(!bundle||!member)return null;status('正在讀取 '+CFG[eng].label.replace(/^[^ ]+ /,'')+'：'+String(w.reading||'')+'…');var bytes=await rangeBytes(bundle,Number(member[0]),Number(member[1]));stopHosted();var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;if(guard().isMobile&&guard().playHostedBytes){await guard().playHostedBytes(bytes,speed);}else{hostedBlobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=hostedAudio=new Audio(hostedBlobUrl),done=false;a.playbackRate=speed;function finish(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(hostedAudio===a)hostedAudio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('預錄音播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});}var meta=group(c)[key]||{};status('✅ '+voiceName(meta,key)+' 已播放。');return{engine:eng,key:key};}
function japaneseDeviceVoices(){if(!('speechSynthesis' in window))return[];return speechSynthesis.getVoices().filter(function(v){return /^ja([-_]|$)/i.test(v.lang||'');});}
async function speakDevice(text){var voices=japaneseDeviceVoices();if(!voices.length)throw new Error('此裝置沒有 Japanese voice');var sel=el('voice'),raw=sel&&sel.value,idx=Number(raw);var voice=Number.isFinite(idx)&&voices[idx]?voices[idx]:voices[0];stopDevice();await new Promise(function(resolve,reject){var u=deviceUtterance=new SpeechSynthesisUtterance(String(text||''));u.lang='ja-JP';u.voice=voice;var s=Number(el('speed')&&el('speed').value||1);u.rate=Number.isFinite(s)&&s>0?s:1;u.onend=function(){deviceUtterance=null;resolve();};u.onerror=function(e){deviceUtterance=null;reject(e.error||new Error('裝置語音失敗'));};speechSynthesis.speak(u);});status('✅ 裝置日語聲線：'+voice.name);return{engine:'device',key:voice.name};}
async function hostedFallback(text,w,from){var order=['supertonic3','voicevox','aivis'].filter(function(x){return x!==from;});for(var i=0;i<order.length;i++){var eng=order[i];status('伺服器預錄暫未命中，正在改用 '+CFG[eng].label+'…');try{var out=await playHosted(eng,w);if(out)return out;}catch(e){console.warn(eng+' hosted fallback failed',e);}}status('⚠️ 伺服器預錄暫時無法使用，改用裝置 Japanese voice。');return speakDevice(text);}
W.speak=async function(text,overrideWord){var eng=engine(),w=wordFor(text,overrideWord);stopHosted();if(eng==='device')return speakDevice(text);if(CFG[eng]&&CFG[eng].catalog){try{var out=await playHosted(eng,w);if(out)return out;}catch(e){console.warn(eng+' hosted failed',e);}return hostedFallback(text,w,eng);}return hostedFallback(text,w,'');};
W.pause=function(){stopAll();return typeof oldPause==='function'?oldPause.apply(W,arguments):undefined;};
function renderDevice(){var s=el('voice');if(!s)return;var vs=japaneseDeviceVoices();s.disabled=false;s.innerHTML=vs.length?vs.map(function(v,i){return'<option value="'+i+'">'+esc(v.name)+'｜'+esc(v.lang)+'</option>';}).join(''):'<option value="">此裝置沒有日語聲線</option>';}
async function renderHosted(eng){var s=el('voice');if(!s)return;var c=await loadCatalog(eng),all=keys(c);if(c&&c.status==='ready'&&all.length){s.disabled=false;s.innerHTML='<option value="random">🎲 每個單字隨機聲線</option>'+all.map(function(k){return'<option value="'+esc(k)+'">'+esc(voiceName(group(c)[k],k))+'</option>';}).join('');if(eng==='supertonic3'&&all.indexOf('F3')>=0)s.value='F3';status('✅ '+CFG[eng].label+'：'+all.length+' 種伺服器聲線可用。');}else{s.innerHTML='<option value="">伺服器聲線包尚未完成</option>';s.disabled=true;status('⏳ '+CFG[eng].label+' 的伺服器預錄包暫不可用；播放時會自動改用其他伺服器預錄聲線。');}}
async function syncUI(){var eng=engine();if(eng==='device')renderDevice();else await renderHosted(eng);updateDesc();}
function updateDesc(){var d=el('voiceDesc'),eng=engine();if(!d)return;if(eng==='voicevox')d.textContent='VOICEVOX：使用本站伺服器預先生成的單字音訊；播放時不需要即時生成。';else if(eng==='aivis')d.textContent='AivisSpeech / Style-Bert-VITS：使用本站伺服器預先生成的日語聲線包；不需要本機 AivisSpeech。';else if(eng==='device')d.textContent='裝置 Japanese voice：只作緊急備援，聲線依瀏覽器／作業系統而不同。';else d.textContent='Supertonic 3：使用本站伺服器預先生成的 F1–F5 / M1–M5 單字音訊；不下載、不安裝，也不在瀏覽器即時生成 Supertonic 模型。';}
async function auditionSelectedVoice(){
  var e=engine();
  if(e==='device'){
    var text='こんにちは',used=await speakDevice(text);
    return{used:used,text:text};
  }
  var c=await loadCatalog(e);
  if(!c||c.status!=='ready'||!c.words)throw new Error('所選伺服器語音 catalog 尚未可用');
  var words=Array.isArray(W.words)?W.words:[],w=null;
  for(var i=0;i<words.length;i++){
    if(c.words[wordKey(words[i])]){w=words[i];break;}
  }
  if(!w)throw new Error('找不到可用於聲線試聽的已預錄單字');
  var used=await playHosted(e,w);
  if(!used)throw new Error('所選聲線未能直接播放試聽單字');
  return{used:used,text:String(w.reading||'')};
}
function installUI(){var voice=el('voice');if(!voice)return;var parent=voice.parentNode;if(!el('audioEngine')){var wrap=document.createElement('div');wrap.className='field';wrap.style.marginTop='10px';wrap.innerHTML='<label for="audioEngine">語音來源</label><select id="audioEngine"><option value="voicevox">'+CFG.voicevox.label+'</option><option value="supertonic3" selected>'+CFG.supertonic3.label+'</option><option value="aivis">'+CFG.aivis.label+'</option><option value="device">'+CFG.device.label+'</option></select>';parent.parentNode.insertBefore(wrap,parent);el('audioEngine').onchange=syncUI;}var title=document.querySelector('#setup aside h2');if(title)title.textContent='🔊 單字語音｜VOICEVOX / Supertonic 3 / AivisSpeech';var note=document.querySelector('#setup aside .notice');if(note)note.textContent='三種主要日語引擎均使用本站伺服器預先生成的單字聲線；不需要下載或安裝 Supertonic 模型。';var sample=el('sampleVoice');if(sample){sample.onclick=async function(){sample.disabled=true;sampleStatus('正在直接測試目前選擇的日語聲線…');try{var result=await auditionSelectedVoice(),used=result.used;sampleStatus('✅ 試聽完成：'+(used&&used.engine?used.engine:engine())+'｜'+(used&&used.key?used.key:'')+'｜'+result.text);}catch(e){sampleStatus('⚠️ 試聽失敗：'+(e&&e.message?e.message:String(e)));}finally{sample.disabled=false;}};}if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=function(){if(engine()==='device')renderDevice();};syncUI();}
window.WORD_AUDIO_MULTI_VOICE={version:4,engines:['voicevox','supertonic3','aivis','device'],sync:syncUI,loadCatalog:loadCatalog,stop:stopAll,hostedOnly:true,mobileSafe:true,auditionExactVoice:true};
installUI();
})();
