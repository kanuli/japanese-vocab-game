from pathlib import Path
import re


def patch(path, old, new, label):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    if new in s:
        print(f'{path}: {label} already applied')
        return
    n = s.count(old)
    if n != 1:
        raise SystemExit(f'{path}: {label} expected 1 old match, got {n}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
    print(f'{path}: applied {label}')


def regex_bust(path, name, version):
    p = Path(path)
    s = p.read_text(encoding='utf-8')
    s2 = re.sub(r'(\./' + re.escape(name) + r')\?v=[^"\']+', r'\1?v=' + version, s)
    if s2 != s:
        p.write_text(s2, encoding='utf-8')
        print(f'{path}: cache-busted {name}')

# Every page must fetch the new unlock-capable guard instead of a stale cached copy.
for p in Path('.').glob('*.html'):
    regex_bust(str(p), 'mobile-supertonic-guard.js', '20260817v4')

# WORD AUDIO / WORD LIST: hosted VOICEVOX and hosted Supertonic use the unlocked mobile player.
patch('wordaudio-multivoice.js',
"function stopHosted(){if(hostedAudio){try{hostedAudio.pause();hostedAudio.currentTime=0;}catch(e){}hostedAudio=null;}if(hostedBlobUrl){try{URL.revokeObjectURL(hostedBlobUrl);}catch(e){}hostedBlobUrl='';}}",
"function stopHosted(){if(guard().isMobile&&guard().stopHostedAudio)try{guard().stopHostedAudio();}catch(e){}if(hostedAudio){try{hostedAudio.pause();hostedAudio.currentTime=0;}catch(e){}hostedAudio=null;}if(hostedBlobUrl){try{URL.revokeObjectURL(hostedBlobUrl);}catch(e){}hostedBlobUrl='';}}",
'word shared stop')
patch('wordaudio-multivoice.js',
"async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl,bundle.url].filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});if(r.status!==206)throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('音訊下載失敗');}",
"async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl,bundle.url].filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('音訊下載失敗');}",
'word safe range')
patch('wordaudio-multivoice.js',
"stopHosted();hostedBlobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=hostedAudio=new Audio(hostedBlobUrl),done=false;var speed=Number(el('speed')&&el('speed').value||1);if(Number.isFinite(speed)&&speed>0)a.playbackRate=speed;function finish(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(hostedAudio===a)hostedAudio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('預錄音播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});",
"stopHosted();var speed=Number(el('speed')&&el('speed').value||1);if(!Number.isFinite(speed)||speed<=0)speed=1;if(guard().isMobile&&guard().playHostedBytes){await guard().playHostedBytes(bytes,speed);}else{hostedBlobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=hostedAudio=new Audio(hostedBlobUrl),done=false;a.playbackRate=speed;function finish(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(hostedAudio===a)hostedAudio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('預錄音播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});}",
'word mobile hosted playback')

# Legacy word-list VOICEVOX reader: keep it safe if a page still loads it.
patch('wordlist-voicevox.js',
"function stop(){if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
"function stop(){var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.stopHostedAudio)try{g.stopHostedAudio();}catch(e){}if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
'wordlist VOICEVOX shared stop')
patch('wordlist-voicevox.js',
"async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});if(r.status!==206)throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('VOICEVOX 音訊下載失敗');}",
"async function rangeBytes(bundle,offset,size){var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('VOICEVOX 音訊下載失敗');}",
'wordlist VOICEVOX safe range')
patch('wordlist-voicevox.js',
"blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;function finish(ok,err){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(err||new Error('VOICEVOX 播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('VOICEVOX MP3 播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});",
"var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.playHostedBytes){await g.playHostedBytes(bytes,1);}else{blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;function finish(ok,err){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(err||new Error('VOICEVOX 播放失敗'));}a.onended=function(){finish(true);};a.onerror=function(){finish(false,new Error('VOICEVOX MP3 播放失敗'));};var p=a.play();if(p&&p.catch)p.catch(function(e){finish(false,e);});});}",
'wordlist VOICEVOX mobile playback')

# LISTENING hosted Supertonic range bundle.
patch('listening-supertonic-hosted.js',
"function stop(){if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
"function stop(){var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.stopHostedAudio)try{g.stopHostedAudio();}catch(e){}if(audio){try{audio.pause();audio.currentTime=0;}catch(e){}audio=null;}if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
'listening Supertonic shared stop')
patch('listening-supertonic-hosted.js',
"async function rangeBytes(bundle,offset,size){var urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null,end=offset+size-1;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});if(r.status!==206)throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size mismatch');return b;}catch(e){last=e;}}throw last||new Error('Supertonic 3 音訊下載失敗');}",
"async function rangeBytes(bundle,offset,size){var urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null,end=offset+size-1;for(var i=0;i<urls.length;i++){try{var r=await fetch(urls[i],{headers:{Range:'bytes='+offset+'-'+end},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;}catch(e){last=e;}}throw last||new Error('Supertonic 3 音訊下載失敗');}",
'listening Supertonic safe range')
patch('listening-supertonic-hosted.js',
"async function playBytes(bytes,rate){stop();blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;a.playbackRate=rate||1;function fin(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){fin(true);};a.onerror=function(){fin(false,new Error('Supertonic 3 MP3 播放失敗'));};a.play().catch(function(e){fin(false,e);});});if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
"async function playBytes(bytes,rate){stop();var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.playHostedBytes){await g.playHostedBytes(bytes,rate||1);return;}blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));await new Promise(function(resolve,reject){var a=audio=new Audio(blobUrl),done=false;a.playbackRate=rate||1;function fin(ok,e){if(done)return;done=true;a.onended=a.onerror=null;if(audio===a)audio=null;ok?resolve():reject(e||new Error('播放失敗'));}a.onended=function(){fin(true);};a.onerror=function(){fin(false,new Error('Supertonic 3 MP3 播放失敗'));};a.play().catch(function(e){fin(false,e);});});if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(e){}blobUrl='';}}",
'listening Supertonic mobile playback')

# LISTENING VOICEVOX uses remote sprite/media URLs. On mobile bypass per-candidate new Audio objects.
patch('listening.html',
"const a=await candidateAudio(c);activeAiAudio=a;await playAudioSegment(a,prepared.segment,rate);",
"const mg=window.MobileSupertonicGuard;if(mg&&mg.isMobile&&mg.playSharedUrl){activeAiAudio=null;await mg.playSharedUrl(c.url,rate,prepared.segment?prepared.segment.start:null,prepared.segment?prepared.segment.end:null);}else{const a=await candidateAudio(c);activeAiAudio=a;await playAudioSegment(a,prepared.segment,rate);}",
'listening VOICEVOX mobile player')

# CONVERSATION hosted VOICEVOX / Supertonic.
patch('conversation-hosted-audio.js',
"function stop(){if(H.timer){clearTimeout(H.timer);H.timer=null}if(H.audio){try{H.audio.pause();H.audio.currentTime=0}catch{}H.audio=null}if(H.blobUrl){try{URL.revokeObjectURL(H.blobUrl)}catch{}H.blobUrl=''}}",
"function stop(){const g=window.MobileSupertonicGuard;if(g?.isMobile&&g.stopHostedAudio)try{g.stopHostedAudio()}catch{}if(H.timer){clearTimeout(H.timer);H.timer=null}if(H.audio){try{H.audio.pause();H.audio.currentTime=0}catch{}H.audio=null}if(H.blobUrl){try{URL.revokeObjectURL(H.blobUrl)}catch{}H.blobUrl=''}}",
'conversation shared stop')
patch('conversation-hosted-audio.js',
"async function playSegment(url,start,end,rate){stop();const a=H.audio=new Audio(url);a.preload='metadata';await waitMeta(a);a.currentTime=Math.max(0,start);a.playbackRate=rate;await a.play();await new Promise((resolve,reject)=>{let done=false;const ms=Math.max(100,((end-start)/rate)*1000+120);const finish=(ok,e)=>{if(done)return;done=true;if(H.timer){clearTimeout(H.timer);H.timer=null}a.onerror=null;if(H.audio===a)H.audio=null;ok?resolve():reject(e||Error('播放失敗'))};a.onerror=()=>finish(false,Error('音訊播放失敗'));H.timer=setTimeout(()=>{try{a.pause();a.currentTime=start}catch{}finish(true)},ms)})}",
"async function playSegment(url,start,end,rate){stop();const g=window.MobileSupertonicGuard;if(g?.isMobile&&g.playSharedUrl){await g.playSharedUrl(url,rate,start,end);return}const a=H.audio=new Audio(url);a.preload='metadata';await waitMeta(a);a.currentTime=Math.max(0,start);a.playbackRate=rate;await a.play();await new Promise((resolve,reject)=>{let done=false;const ms=Math.max(100,((end-start)/rate)*1000+120);const finish=(ok,e)=>{if(done)return;done=true;if(H.timer){clearTimeout(H.timer);H.timer=null}a.onerror=null;if(H.audio===a)H.audio=null;ok?resolve():reject(e||Error('播放失敗'))};a.onerror=()=>finish(false,Error('音訊播放失敗'));H.timer=setTimeout(()=>{try{a.pause();a.currentTime=start}catch{}finish(true)},ms)})}",
'conversation mobile segment')
patch('conversation-hosted-audio.js',
"async function rangeBytes(url,offset,size){const end=offset+size-1;const r=await fetch(url,{headers:{Range:`bytes=${offset}-${end}`},cache:'force-cache'});if(r.status!==206)throw Error('Range HTTP '+r.status);const b=await r.arrayBuffer();if(b.byteLength!==size)throw Error(`Range size ${b.byteLength}/${size}`);return b}",
"async function rangeBytes(url,offset,size){const end=offset+size-1;const r=await fetch(url,{headers:{Range:`bytes=${offset}-${end}`},cache:'force-cache'});const len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw Error('Range HTTP '+r.status+' length '+len);const b=await r.arrayBuffer();if(b.byteLength!==size)throw Error(`Range size ${b.byteLength}/${size}`);return b}",
'conversation safe range')
patch('conversation-hosted-audio.js',
"async function playBytes(bytes,rate){stop();H.blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));const a=H.audio=new Audio(H.blobUrl);a.playbackRate=rate;await new Promise((resolve,reject)=>{let done=false;const finish=(ok,e)=>{if(done)return;done=true;a.onended=a.onerror=null;if(H.audio===a)H.audio=null;ok?resolve():reject(e||Error('播放失敗'))};a.onended=()=>finish(true);a.onerror=()=>finish(false,Error('MP3 播放失敗'));a.play().catch(e=>finish(false,e))});if(H.blobUrl){try{URL.revokeObjectURL(H.blobUrl)}catch{}H.blobUrl=''}}",
"async function playBytes(bytes,rate){stop();const g=window.MobileSupertonicGuard;if(g?.isMobile&&g.playHostedBytes){await g.playHostedBytes(bytes,rate);return}H.blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));const a=H.audio=new Audio(H.blobUrl);a.playbackRate=rate;await new Promise((resolve,reject)=>{let done=false;const finish=(ok,e)=>{if(done)return;done=true;a.onended=a.onerror=null;if(H.audio===a)H.audio=null;ok?resolve():reject(e||Error('播放失敗'))};a.onended=()=>finish(true);a.onerror=()=>finish(false,Error('MP3 播放失敗'));a.play().catch(e=>finish(false,e))});if(H.blobUrl){try{URL.revokeObjectURL(H.blobUrl)}catch{}H.blobUrl=''}}",
'conversation mobile bytes')

# TRANSLATOR hosted VOICEVOX/Aivis exact-match playback.
patch('translator-hosted-voice.js',
"function stop(){if(V.timer){clearTimeout(V.timer);V.timer=null;}if(V.audio){try{V.audio.pause();V.audio.currentTime=0;}catch(e){}V.audio=null;}}",
"function stop(){var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.stopHostedAudio)try{g.stopHostedAudio();}catch(e){}if(V.timer){clearTimeout(V.timer);V.timer=null;}if(V.audio){try{V.audio.pause();V.audio.currentTime=0;}catch(e){}V.audio=null;}}",
'translator shared stop')
patch('translator-hosted-voice.js',
"async function segment(url,start,end,rate){stop();var a=V.audio=new Audio(url);a.preload='metadata';await meta(a);a.currentTime=Math.max(0,start);a.playbackRate=rate||1;await a.play();await new Promise(function(resolve,reject){var done=false,ms=Math.max(100,((end-start)/(rate||1))*1000+100);function fin(ok,e){if(done)return;done=true;if(V.timer){clearTimeout(V.timer);V.timer=null;}a.onerror=null;if(V.audio===a)V.audio=null;ok?resolve():reject(e||new Error('play failed'));}a.onerror=function(){fin(false,new Error('audio failed'));};V.timer=setTimeout(function(){try{a.pause();a.currentTime=start;}catch(e){}fin(true);},ms);});}",
"async function segment(url,start,end,rate){stop();var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.playSharedUrl){await g.playSharedUrl(url,rate||1,start,end);return;}var a=V.audio=new Audio(url);a.preload='metadata';await meta(a);a.currentTime=Math.max(0,start);a.playbackRate=rate||1;await a.play();await new Promise(function(resolve,reject){var done=false,ms=Math.max(100,((end-start)/(rate||1))*1000+100);function fin(ok,e){if(done)return;done=true;if(V.timer){clearTimeout(V.timer);V.timer=null;}a.onerror=null;if(V.audio===a)V.audio=null;ok?resolve():reject(e||new Error('play failed'));}a.onerror=function(){fin(false,new Error('audio failed'));};V.timer=setTimeout(function(){try{a.pause();a.currentTime=start;}catch(e){}fin(true);},ms);});}",
'translator mobile segment')
patch('translator-hosted-voice.js',
"async function range(url,offset,size){var r=await fetch(url,{headers:{Range:'bytes='+offset+'-'+(offset+size-1)},cache:'force-cache'});if(r.status!==206)throw new Error('Range HTTP '+r.status);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size mismatch');return b;}",
"async function range(url,offset,size){var r=await fetch(url,{headers:{Range:'bytes='+offset+'-'+(offset+size-1)},cache:'force-cache'});var len=Number(r.headers.get('content-length')||0);if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);var b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size mismatch');return b;}",
'translator safe range')
patch('translator-hosted-voice.js',
"async function bytesPlay(bytes,rate){stop();var u=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));try{await new Promise(function(resolve,reject){var a=V.audio=new Audio(u);a.playbackRate=rate||1;a.onended=function(){V.audio=null;resolve();};a.onerror=function(){V.audio=null;reject(new Error('play failed'));};a.play().catch(reject);});}finally{URL.revokeObjectURL(u);}}",
"async function bytesPlay(bytes,rate){stop();var g=window.MobileSupertonicGuard;if(g&&g.isMobile&&g.playHostedBytes){await g.playHostedBytes(bytes,rate||1);return;}var u=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));try{await new Promise(function(resolve,reject){var a=V.audio=new Audio(u);a.playbackRate=rate||1;a.onended=function(){V.audio=null;resolve();};a.onerror=function(){V.audio=null;reject(new Error('play failed'));};a.play().catch(reject);});}finally{URL.revokeObjectURL(u);}}",
'translator mobile bytes')

# PRONUNCIATION hosted reference must also use the already-unlocked mobile player.
patch('pronunciation.html',
"if(ab){refBuf=ab.slice(0);let blob=new Blob([ab],{type:'audio/mpeg'});refUrl=URL.createObjectURL(blob);if(play)await new Audio(refUrl).play();$('#status').textContent='✅ 參考音已播放；現在請說一次。';return true}",
"if(ab){refBuf=ab.slice(0);let blob=new Blob([ab],{type:'audio/mpeg'});refUrl=URL.createObjectURL(blob);if(play){const mg=window.MobileSupertonicGuard;if(mg?.isMobile&&mg.playHostedBytes)await mg.playHostedBytes(ab.slice(0),1);else await new Audio(refUrl).play()}$('#status').textContent='✅ 參考音已播放；現在請說一次。';return true}",
'pronunciation mobile hosted reference')

# Cache-bust patched clients.
for page, name, version in [
    ('wordaudio.html','wordaudio-multivoice.js','20260817v4'),
    ('wordlist.html','wordaudio-multivoice.js','20260817v4'),
    ('listening.html','listening-supertonic-hosted.js','20260817v2'),
    ('conversation.html','conversation-hosted-audio.js','20260817v4'),
    ('translator.html','translator-hosted-voice.js','20260817v3'),
]:
    regex_bust(page, name, version)

print('Mobile hosted playback patch complete.')
