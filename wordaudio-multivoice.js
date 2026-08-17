(function(){
'use strict';
var W=window.WA=window.WA||{};
var oldSpeak=W.speak, oldPause=W.pause;
var catalogs={voicevox:null,supertonic3:null,aivis:null};
var catalogState={voicevox:'idle',supertonic3:'idle',aivis:'idle'};
var indexCache=new Map(),hostedAudio=null,hostedBlobUrl='',deviceUtterance=null;
var ST3=[
 ['F1','🌙 沉穩低柔女聲（F1）'],['F2','🌸 明亮活潑女聲（F2）'],['F3','🎙️ 專業播音女聲（F3）'],['F4','✨ 清晰自信女聲（F4）'],['F5','💕 溫柔療癒女聲（F5）'],
 ['M1','⚡ 活力自信男聲（M1）'],['M2','🌑 低沉穩重男聲（M2）'],['M3','🧭 權威專業男聲（M3）'],['M4','🙂 柔和親切男聲（M4）'],['M5','📖 溫暖舒緩男聲（M5）']
];
var CFG={
 voicevox:{label:'🎭 VOICEVOX｜伺服器預錄',catalog:'./word-voicevox-catalog.json?v=2',group:'speakers'},
 supertonic3:{label:'✨ Supertonic 3｜伺服器預錄 / 瀏覽器備援',catalog:'./word-supertonic3-catalog.json?v=1',group:'voices'},
 aivis:{label:'💠 AivisSpeech / Style-Bert-VITS｜伺服器預錄',catalog:'./word-aivis-catalog.json?v=1',group:'voices'},
 device:{label:'🔊 裝置 Japanese voice｜備援'}
};
function el(id){return document.getElementById(id);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function status(msg){var x=el('voiceStatus');if(x)x.textContent=msg;}
function sampleStatus(msg){var x=el('sampleVoiceStatus');if(x)x.textContent=msg;}
function guard(){return window.MobileSupertonicGuard||{isMobile:false,localAllowed:true,message:function(){return'';}};}
function localST3Allowed(){var g=guard();return g.localAllowed!==false&&!g.isMobile;}
function stopHosted(){if(guard().isMobile&&guard().stopHostedAudio)try{guard().stopHostedAudio();}catch(e){}if(hostedAudio){try{hostedAudio.pause();hostedAudio.currentTime=0;}catch(e){}hostedAudio=null;}if(hostedBlobUrl){try{URL.revokeObjectURL(hostedBlobUrl);}catch(e){}hostedBlobUrl='';}}
function stopDevice(){try{if('speechSynthesis' in window)speechSynthesis.cancel();}catch(e){}deviceUtterance=null;}
function stopAll(){stopHosted();stopDevice();if(W.audio){try{W.audio.pause();W.audio.currentTime=0;}catch(e){}W.audio=null;}}
function engine(){var x=el('audioEngine');return x?x.value:'supertonic3';}
function wordFor(text,override){if(override)return override;var w=W.list&&W.list[W.i];if(w&&String(w.reading||'')===String(text||''))return w;return null;}
function wordKey(w){return w?(W.key?W.key(w):String(w.reading||'')+'|'+String(w.kanji||w.displayWord||w.reading||'')):'';}
function group(c,eng){if(!c)return{};if(c.voices)return c.voices;if(c.speakers)return c.speakers;return{};}
function keys(c,eng){return Object.keys(group(c,eng));}
function voiceName(v,key){return String(v.displayName||v.speaker||v.name||key)+(v.style?'｜'+v.style:'');}
async function getJson(url){var r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
async function getJsonFallback(a,b){try{return await getJson(a);}catch(e){if(!b)throw e;return getJson(b);}}
async function loadCatalog(eng){if(!CFG[eng]||!CFG[eng].catalog)return null;if(catalogState[eng]==='ready')return catalogs[eng];if(catalogState[eng]==='loading'){
 for(var n=0;n<100&&catalogState[eng]==='loading';n++)await new Promise(function(r){setTimeout(r,50);});return catalogs[eng];
 }
 catalogState[eng]='loading';
 try{var c=await getJson(CFG[eng].catalog);catalogs[eng]=c;if(c&&c.status==='ready'&&c.words&&keys(c,eng).length){catalogState[eng]='ready';return c;}catalogState[eng]='building';return c||null;}
 catch(e){catalogState[eng]=e&&/HTTP 404/.test(String(e.message||e))?'missing':'error';return null;}
}
async function loadIndex(eng,key){var cacheKey=eng+'|'+key;if(indexCache.has(cacheKey))return indexCache.get(cacheKey);var c=catalogs[eng],v=group(c,eng)[key];if(!v)throw new Error('聲線索引不存在');var m=guard().isMobile,url1=m?(v.indexHfUrl||v.indexGithubUrl||v.indexUrl||''):(v.indexGithubUrl||v.indexUrl||v.indexHfUrl||''),url2=m?(v.indexGithubUrl||v.indexUrl||''):(v.indexHfUrl||'');if(!url1&&!url2)throw new Error('聲線索引網址不存在');var d=await getJsonFallback(url1,url2);if(!d||!d.bundles)throw new Error('聲線索引格式錯誤');indexCache.set(cacheKey,d);return d;}
async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=(guard().isMobile?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('音訊下載失敗');}
async function playHosted(eng,w){var c=await loadCatalog(eng);if(!c||c.status!=='ready'||!w)return null;var lookup=c.words&&c.words[wordKey(w)];if(!lookup)return null;var id=lookup[0],shard=String(lookup[1]),all=keys(c,eng),sel=el('voice'),requested=sel&&sel.value;var key=requested&&requested!=='random'?requested:all[Math.floor(Math.random()*all.length)];if(all.indexOf(key)<0)key=all[0];if(!key)return null;var idx=await loadIndex(eng,key),bundle=idx.bundles&&idx.bundles[shard],member=bundle&&bundle.members&&bundle.members[id];if(!bundle||!member)return null;status('正在讀取 '+CFG[eng].label.replace(/^[^ ]+ /,'')+'：'+String(w.reading||'')+'…');var bytes=await rangeBytes(bundle,Number(member[0]),Number(member[1]));stopHosted();var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;if(guard().isMobile&&guard().playHostedBytes){await guard().playHostedBytes(bytes,speed);}else{hostedBlobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=hostedAudio=new Audio(hostedBlobUrl),done=false;a.playbackRate=speed;function finish(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(hostedAudio===a)hostedAudio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('預錄音播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});}var meta=group(c,eng)[key]||{};status('✅ '+voiceName(meta,key)+' 已播放。');return{engine:eng,key:key};}
async function speakST3(text){if(!localST3Allowed())throw new Error('MOBILE_SUPERTONIC_LOCAL_DISABLED');if(typeof oldSpeak!=='function')throw new Error('Supertonic 3 browser fallback unavailable');var v=el('voice');if(v&&!/^([FM][1-5]|random)$/.test(v.value))v.value='F3';return oldSpeak(String(text||''));}
function japaneseDeviceVoices(){if(!('speechSynthesis' in window))return[];return speechSynthesis.getVoices().filter(function(v){return /^ja([-_]|$)/i.test(v.lang||'');});}
async function speakDevice(text){var voices=japaneseDeviceVoices();if(!voices.length)throw new Error('此裝置沒有 Japanese voice');var sel=el('voice'),raw=sel&&sel.value,idx=Number(raw);var voice=Number.isFinite(idx)&&voices[idx]?voices[idx]:voices[0];stopDevice();await new Promise(function(resolve,reject){var u=deviceUtterance=new SpeechSynthesisUtterance(String(text||''));u.lang='ja-JP';u.voice=voice;var s=Number(el('speed')&&el('speed').value||1);u.rate=Number.isFinite(s)&&s>0?s:1;u.onend=function(){deviceUtterance=null;resolve();};u.onerror=function(e){deviceUtterance=null;reject(e.error||new Error('裝置語音失敗'));};speechSynthesis.speak(u);});status('✅ 裝置日語聲線：'+voice.name);return{engine:'device',key:voice.name};}
async function mobileFallback(text,w,from){status('📱 手機模式：不載入本機 Supertonic，正在改用 VOICEVOX 伺服器錄音…');if(from!=='voicevox'){try{var vv=await playHosted('voicevox',w);if(vv)return vv;}catch(e){console.warn('mobile VOICEVOX fallback failed',e);}}status('📱 VOICEVOX 暫不可用，改用裝置 Japanese voice。');return speakDevice(text);}
async function fallbackST3(text,from,w){if(!localST3Allowed())return mobileFallback(text,w,from);status((from==='voicevox'?'VOICEVOX':from==='aivis'?'AivisSpeech / Style-Bert-VITS':'Supertonic 3 預錄庫')+' 此單字暫無可用伺服器錄音，使用 Supertonic 3 瀏覽器備援。');return speakST3(text);}
W.speak=async function(text,overrideWord){var eng=engine(),w=wordFor(text,overrideWord);stopHosted();if(eng==='device')return speakDevice(text);if(eng==='supertonic3'){
  try{var h=await playHosted('supertonic3',w);if(h)return h;}catch(e){console.warn('Supertonic 3 hosted failed',e);}if(!localST3Allowed())return mobileFallback(text,w,'supertonic3');return speakST3(text);
 }
 if(eng==='voicevox'||eng==='aivis'){
  try{var out=await playHosted(eng,w);if(out)return out;}catch(e){console.warn(eng+' hosted failed',e);}return fallbackST3(text,eng,w);
 }
 return localST3Allowed()?speakST3(text):mobileFallback(text,w,'supertonic3');
};
W.pause=function(){stopAll();return typeof oldPause==='function'?oldPause.apply(W,arguments):undefined;};
function renderST3(){var s=el('voice');if(!s)return;s.innerHTML='<option value="random">🎲 每個單字隨機聲線</option>'+ST3.map(function(x){return'<option value="'+x[0]+'">'+x[1]+'</option>';}).join('');s.value='F3';}
function renderDevice(){var s=el('voice');if(!s)return;var vs=japaneseDeviceVoices();s.innerHTML=vs.length?vs.map(function(v,i){return'<option value="'+i+'">'+esc(v.name)+'｜'+esc(v.lang)+'</option>';}).join(''):'<option value="">此裝置沒有日語聲線</option>';}
async function renderHosted(eng){var s=el('voice');if(!s)return;var c=await loadCatalog(eng),all=keys(c,eng);if(c&&c.status==='ready'&&all.length){s.disabled=false;s.innerHTML='<option value="random">🎲 每個單字隨機聲線</option>'+all.map(function(k){return'<option value="'+esc(k)+'">'+esc(voiceName(group(c,eng)[k],k))+'</option>';}).join('');status('✅ '+CFG[eng].label+'：'+all.length+' 種聲線可用。');}else{s.innerHTML='<option value="">伺服器聲線包尚未完成</option>';s.disabled=true;status(localST3Allowed()?'⏳ '+CFG[eng].label+' 的單字伺服器聲線包尚未完成；播放時會自動使用 Supertonic 3 備援。':'📱 '+CFG[eng].label+' 暫不可用；手機會自動改用 VOICEVOX／裝置日語語音。');}}
async function syncUI(){var eng=engine(),s=el('voice');if(s)s.disabled=false;if(eng==='supertonic3'){renderST3();var c=await loadCatalog('supertonic3');if(localST3Allowed())status(c&&c.status==='ready'?'✅ Supertonic 3：可優先使用伺服器預錄，缺漏時瀏覽器即時生成。':'✨ Supertonic 3：目前使用瀏覽器即時生成；伺服器預錄包完成後會自動優先使用。');else status(c&&c.status==='ready'?'📱 Supertonic 3 手機模式：只使用伺服器預錄；不載入本機 400 MB 模型。':'📱 此手機不載入本機 Supertonic；已啟用 VOICEVOX／裝置語音自動備援。');}
 else if(eng==='device')renderDevice();else await renderHosted(eng);
 updateDesc();}
function updateDesc(){var d=el('voiceDesc'),eng=engine();if(!d)return;if(eng==='voicevox')d.textContent='VOICEVOX：使用本站伺服器預錄單字音訊；GitHub Releases 主來源，Hugging Face 備援。';else if(eng==='aivis')d.textContent='AivisSpeech / Style-Bert-VITS：使用本站預先生成的日語聲線包；不需要本機 AivisSpeech。';else if(eng==='device')d.textContent='裝置 Japanese voice：只作備援，聲線依瀏覽器／作業系統而不同。';else d.textContent=localST3Allowed()?'Supertonic 3：10 種 F1–F5 / M1–M5 聲線；伺服器預錄未命中時可直接在瀏覽器生成。':'Supertonic 3 手機安全模式：只播放伺服器預錄；不啟動本機 WASM 模型，缺漏會自動改用 VOICEVOX／裝置語音。';}
function installUI(){var voice=el('voice');if(!voice)return;var parent=voice.parentNode;if(!el('audioEngine')){var wrap=document.createElement('div');wrap.className='field';wrap.style.marginTop='10px';wrap.innerHTML='<label for="audioEngine">語音來源</label><select id="audioEngine"><option value="voicevox">'+CFG.voicevox.label+'</option><option value="supertonic3" selected>'+CFG.supertonic3.label+'</option><option value="aivis">'+CFG.aivis.label+'</option><option value="device">'+CFG.device.label+'</option></select>';parent.parentNode.insertBefore(wrap,parent);el('audioEngine').onchange=syncUI;}
 if(!localST3Allowed()){el('audioEngine').value='voicevox';status('📱 已啟用手機安全模式：預設使用 VOICEVOX，不載入本機 Supertonic。');}
 var title=document.querySelector('#setup aside h2');if(title)title.textContent='🔊 單字語音｜VOICEVOX / Supertonic 3 / AivisSpeech';var note=document.querySelector('#setup aside .notice');if(note)note.textContent=localST3Allowed()?'三種主要日語引擎共用本站的單字聲線資料庫。伺服器預錄未完成或缺漏時會使用 Supertonic 3 瀏覽器備援；不需要連接本機 IP。':'📱 手機安全模式：優先使用伺服器預錄；不載入本機 Supertonic 400 MB 模型，以避免 WASM Out of memory。';var sample=el('sampleVoice');if(sample){sample.onclick=async function(){sample.disabled=true;sampleStatus('正在準備試聽…');try{var w=W.words&&W.words.length?W.words[0]:null,text=w?w.reading:'こんにちは';var used=await W.speak(text,w);sampleStatus('✅ 試聽完成：'+(used&&used.engine?used.engine:engine())+'｜'+text);}catch(e){sampleStatus('⚠️ 試聽失敗：'+(e&&e.message?e.message:String(e)));}finally{sample.disabled=false;}};}
 if('speechSynthesis' in window)speechSynthesis.onvoiceschanged=function(){if(engine()==='device')renderDevice();};syncUI();}
window.WORD_AUDIO_MULTI_VOICE={version:2,engines:['voicevox','supertonic3','aivis','device'],sync:syncUI,loadCatalog:loadCatalog,stop:stopAll,mobileSafe:!localST3Allowed()};
installUI();
})(window.WA);
