#!/usr/bin/env python3
from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

assert '日本語聽解挑戰 v1.6｜JLPT N1–N5' in s
s=s.replace('日本語聽解挑戰 v1.6｜JLPT N1–N5','日本語聽解挑戰 v1.7｜JLPT N1–N5',1)

old='''<div class="radios three" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked><label for="engineVoicevox">🎭 VOICEVOX<br>自動備援</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai"><label for="engineAI">✨ Supertonic<br>AI</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>語音</label></div></div>
<div id="voicevoxPanel">
<div id="voicevoxStatus" class="notice" style="margin:0 0 8px">正在載入 VOICEVOX 公開音訊索引…</div>
<div class="muted">音訊包由 GitHub Actions 自動發佈至 GitHub Releases，並可同步鏡像到 Hugging Face。播放失敗時會自動切換來源。</div>
</div>
<div id="aiPanel">
<div id="aiStatus" class="notice" style="margin:0 0 8px">尚未下載 AI 模型。首次啟用約需下載 400 MB；之後瀏覽器通常可使用快取。</div>'''
new='''<div class="radios three" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked><label for="engineVoicevox">🎭 VOICEVOX<br>自動備援</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai"><label for="engineAI">✨ Supertonic<br>AI</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>語音</label></div></div>
<button id="sampleVoice" class="btn" style="width:100%;margin:0 0 9px">▶ 試聽目前選擇的日語語音</button>
<div id="sampleVoiceStatus" class="muted" style="margin:0 0 9px">可先試聽，再決定使用哪一種語音。</div>
<div id="voicevoxPanel">
<div id="voicevoxStatus" class="notice" style="margin:0 0 8px">正在載入 VOICEVOX 公開音訊索引…</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">VOICEVOX 聲線</label><select id="voicevoxVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="random">🎲 每題使用不同預錄聲線（完整題庫）</option></select><div id="voicevoxVoiceDesc" class="notice" style="margin-top:7px">正在整理可選 VOICEVOX 聲線…</div></div>
<div class="muted" style="margin-top:8px">每個句子目前有一條已預錄 VOICEVOX 音訊。指定聲線時，遊戲會只使用已有該聲線的題目；選「每題使用不同預錄聲線」可使用完整題庫。GitHub Releases 播放失敗時會自動切換 Hugging Face。</div>
</div>
<div id="aiPanel">
<div id="aiStatus" class="notice" style="margin:0 0 8px">尚未載入 AI 模型。首次使用約需下載 400 MB；完成後會儲存在此瀏覽器的持久快取，正常情況不需要再次下載。</div>'''
assert old in s
s=s.replace(old,new,1)

old='''function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
new='''function selectedVoicevoxSpeaker(){return $("#voicevoxVoice")?.value||"random"}
function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=audioEngine]:checked")?.value==="voicevox"){const speaker=selectedVoicevoxSpeaker();if(speaker!=="random")p=p.filter(x=>voicevoxIndex?.items?.[x.id]?.speaker===speaker)}if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
assert old in s
s=s.replace(old,new,1)

start=s.index('let voicevoxIndex={version:2,items:{}};')
end=s.index('\n\nasync function waitForAiModule()', start)
replacement=r'''let voicevoxIndex={version:2,items:{}};
function voicevoxUrls(rec){const raw=Array.isArray(rec?.urls)?rec.urls:[rec?.url,rec?.backupUrl];return[...new Set(raw.filter(x=>typeof x==="string"&&x.trim()).map(x=>x.trim()))]}
function voicevoxProvider(url){return /huggingface\.co\//i.test(url)?"Hugging Face 備援":"GitHub Releases"}
function populateVoicevoxVoices(){const sel=$("#voicevoxVoice"),desc=$("#voicevoxVoiceDesc");if(!sel)return;const counts=new Map();Object.values(voicevoxIndex?.items||{}).forEach(r=>{const n=String(r?.speaker||"").trim();if(n)counts.set(n,(counts.get(n)||0)+1)});const wanted=load("jplistening_voicevox_speaker","random");const rows=[...counts.entries()].sort((a,b)=>a[0].localeCompare(b[0],"ja"));sel.innerHTML='<option value="random">🎲 每題使用不同預錄聲線（完整題庫）</option>'+rows.map(([name,n])=>`<option value="${esc(name)}">${esc(name)}（${n.toLocaleString()} 題）</option>`).join("");sel.value=rows.some(([name])=>name===wanted)?wanted:"random";updateVoicevoxVoice()}
function updateVoicevoxVoice(){const sel=$("#voicevoxVoice"),desc=$("#voicevoxVoiceDesc");if(!sel||!desc)return;const name=sel.value||"random";save("jplistening_voicevox_speaker",name);if(name==="random"){desc.textContent=`完整 VOICEVOX 題庫：${Object.keys(voicevoxIndex?.items||{}).length.toLocaleString()} 題；每題使用該句已預錄的聲線。`}else{const rows=Object.values(voicevoxIndex?.items||{}).filter(r=>r?.speaker===name);const styles=[...new Set(rows.map(r=>r?.style).filter(Boolean))];desc.textContent=`${name}：目前有 ${rows.length.toLocaleString()} 題預錄音訊${styles.length?`；包含 ${styles.slice(0,4).join("、")}${styles.length>4?"…":""}`:""}。開始後只抽選這個聲線的題目。`}availability()}
async function loadVoicevoxIndex(){const st=$("#voicevoxStatus");try{const r=await fetch("./voicevox-release-index.json",{cache:"no-cache"});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();if(!d||typeof d!=="object"||!d.items)throw new Error("索引格式不正確");voicevoxIndex=d;const n=Object.keys(d.items||{}).length;const backed=Object.values(d.items||{}).filter(rec=>voicevoxUrls(rec).some(u=>/huggingface\.co\//i.test(u))).length;populateVoicevoxVoices();st.textContent=n?`✅ VOICEVOX 已準備：${n.toLocaleString()} 題${backed?` · ${backed.toLocaleString()} 題已設定 Hugging Face 自動備援`:""}。現在可直接開始。`:"⚠️ VOICEVOX 音訊索引目前是空的，將使用其他語音備援。";return n}catch(e){voicevoxIndex={version:2,items:{}};populateVoicevoxVoices();st.textContent="⚠️ VOICEVOX 公開音訊包尚未發佈或暫時無法讀取；將使用其他語音備援。";return 0}}
async function prepareVoicevoxAudio(q){const rec=voicevoxIndex?.items?.[q.id],urls=voicevoxUrls(rec);if(!urls.length)return null;return{candidates:urls.map(url=>({url,provider:voicevoxProvider(url),audio:null})),out:{...rec,source:"VOICEVOX"}}}
function candidateAudio(candidate){if(!candidate.audio||!candidate.audio.src){candidate.audio=new Audio(candidate.url);candidate.audio.preload="auto"}return candidate.audio}
async function playVoicevoxRecord(rec,rate=1,forSample=false){const prepared={candidates:voicevoxUrls(rec).map(url=>({url,provider:voicevoxProvider(url),audio:null})),out:{...rec,source:"VOICEVOX"}};if(!prepared.candidates.length)throw new Error("此音訊沒有可用來源");let lastError=null;for(const candidate of prepared.candidates){const a=candidateAudio(candidate);activeAiAudio=a;try{a.pause();a.currentTime=0;a.playbackRate=rate;await a.play()}catch(e){lastError=e;candidate.audio=null;activeAiAudio=null;continue}const who=[rec.speaker,rec.style].filter(Boolean).join("／");if(forSample){$("#sampleVoiceStatus").textContent=`✅ 試聽：${who||"VOICEVOX"} · ${candidate.provider} · ${rec.text||""}`;return true}unlockAfterPlay(`VOICEVOX${who?" · "+who:""} · ${candidate.provider}`);return true}throw lastError||new Error("所有 VOICEVOX 音訊來源均無法播放")}
async function speakVoicevox(rate=1){const st=$("#voicevoxStatus");try{let prepared=game.voicevoxPrepared;if(!prepared&&game.voicevoxPromise)prepared=await game.voicevoxPromise;if(!prepared)prepared=await prepareVoicevoxAudio(game.current);if(!prepared?.candidates?.length)throw new Error("此題尚未有 VOICEVOX 音訊");game.voicevoxPrepared=prepared;let lastError=null;for(const candidate of prepared.candidates){const a=candidateAudio(candidate);activeAiAudio=a;try{a.pause();a.currentTime=0;a.playbackRate=rate;await a.play()}catch(e){lastError=e;if(String(e?.name||"").includes("NotAllowed")){$("#playCount").textContent=`✅ VOICEVOX 已載入（${candidate.provider}）；iPhone/Safari 請再按一次播放。`;return true}candidate.audio=null;activeAiAudio=null;continue}const meta=prepared.out,who=[meta.speaker,meta.style].filter(Boolean).join("／");st.textContent=candidate.provider==="Hugging Face 備援"?"✅ GitHub 音訊不可用，已自動切換 Hugging Face 備援。":`✅ VOICEVOX 正在使用 ${candidate.provider}。`;unlockAfterPlay(`VOICEVOX${who?" · "+who:""} · ${candidate.provider}`);return true}throw lastError||new Error("所有 VOICEVOX 音訊來源均無法播放")}catch(e){st.textContent="⚠️ GitHub 與 Hugging Face 的 VOICEVOX 音訊暫時都無法播放；已改用其他語音備援。";return false}}'''
s=s[:start]+replacement+s[end:]

old='''async function enableAI(){const b=$("#enableAI");if(aiInitPromise)return aiInitPromise;b.disabled=true;aiInitPromise=(async()=>{try{const api=await waitForAiModule();$("#aiStatus").textContent="正在檢查 Supertonic 3 模型…";await api.preflight();await api.init(msg=>{$("#aiStatus").textContent=msg});$("#aiStatus").textContent="✅ Supertonic 3 AI 語音已準備，可選 F1–F5／M1–M5。";$("#engineAI").checked=true;syncAudioPanels();return true}catch(e){$("#aiStatus").textContent="⚠️ AI 語音無法啟用："+(e?.message||String(e))+"。已保留裝置語音備援。";$("#engineDevice").checked=true;syncAudioPanels();return false}finally{b.disabled=false;b.textContent=window.SupertonicAI?.isReady?.()?"✅ AI 語音已啟用":"重新嘗試啟用 AI 語音";aiInitPromise=null}})();return aiInitPromise}
function stopAllAudio(){try{speechSynthesis.cancel()}catch{}if(activeAiAudio){try{activeAiAudio.pause();activeAiAudio.src=""}catch{}activeAiAudio=null}}'''
new='''async function ensureSupertonicCache(){if(!("serviceWorker" in navigator)||!("caches" in window))return false;try{await navigator.serviceWorker.register("./supertonic-sw.js",{scope:"./"});await navigator.serviceWorker.ready;try{await navigator.storage?.persist?.()}catch{}return true}catch{return false}}
async function updateAiCacheStatus(){try{if(!("caches" in window))return;const c=await caches.open("supertonic-model-v1"),keys=await c.keys();const modelCount=keys.filter(r=>/\\.onnx(?:\\?|$)/i.test(r.url)).length;if(modelCount>=4&&!window.SupertonicAI?.isReady?.())$("#aiStatus").textContent=`✅ 已找到此瀏覽器的 Supertonic 模型快取（${modelCount} 個模型）。啟用時會直接使用本機快取，不需重新下載。`}catch{}}
async function enableAI(){const b=$("#enableAI");if(aiInitPromise)return aiInitPromise;b.disabled=true;aiInitPromise=(async()=>{try{await ensureSupertonicCache();const api=await waitForAiModule();$("#aiStatus").textContent="正在檢查 Supertonic 3 本機模型快取…";await api.preflight();await api.init(msg=>{$(("#aiStatus")).textContent=msg});$("#aiStatus").textContent="✅ Supertonic 3 AI 語音已準備；模型已保留在此瀏覽器快取，之後正常不需再次下載。";$("#engineAI").checked=true;syncAudioPanels();return true}catch(e){$("#aiStatus").textContent="⚠️ AI 語音無法啟用："+(e?.message||String(e))+"。已保留裝置語音備援。";$("#engineDevice").checked=true;syncAudioPanels();return false}finally{b.disabled=false;b.textContent=window.SupertonicAI?.isReady?.()?"✅ AI 語音已啟用":"重新嘗試啟用 AI 語音";aiInitPromise=null}})();return aiInitPromise}
function stopAllAudio(){try{speechSynthesis.cancel()}catch{}if(activeAiAudio){try{activeAiAudio.pause();activeAiAudio.currentTime=0}catch{}activeAiAudio=null}}'''
assert old in s
s=s.replace(old,new,1)
# Fix harmless double wrapper introduced above and keep the patch literal easy to validate.
s=s.replace('$(($("#aiStatus")).textContent=msg)', '$("#aiStatus").textContent=msg')
s=s.replace('$(("#aiStatus")).textContent=msg', '$("#aiStatus").textContent=msg')

anchor='''function selectedAiVoice(){const requested=$("#aiVoice")?.value||"F1";if(requested!=="random")return requested;if(game?.aiVoiceForQuestion)return game.aiVoiceForQuestion;const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];return a[Math.floor(Math.random()*a.length)]}
'''
insert=r'''async function playSetupSample(){const status=$("#sampleVoiceStatus");status.textContent="正在準備試聽…";stopAllAudio();const mode=$("input[name=audioEngine]:checked")?.value||"voicevox";try{if(mode==="voicevox"){const name=selectedVoicevoxSpeaker();const rec=Object.values(voicevoxIndex?.items||{}).find(r=>name==="random"||r?.speaker===name);if(!rec)throw new Error("目前找不到這個 VOICEVOX 聲線的試聽音訊");await playVoicevoxRecord(rec,1,true);return}const sample="こんにちは。日本語の聴解練習を始めましょう。";if(mode==="ai"){if(!window.SupertonicAI?.isReady?.()){const ok=await enableAI();if(!ok)throw new Error("Supertonic 尚未準備完成")}const vid=$("#aiVoice")?.value==="random"?"F1":selectedAiVoice();const out=await window.SupertonicAI.synthesize(sample,{voice:vid,speed:1,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();status.textContent=`✅ 試聽：Supertonic ${vid} · ${sample}`;return}const u=new SpeechSynthesisUtterance(sample);u.lang="ja-JP";u.rate=1;const v=chosenDeviceVoice();if(v)u.voice=v;speechSynthesis.speak(u);status.textContent=`✅ 試聽：${v?.name||"裝置日語語音"} · ${sample}`}catch(e){status.textContent="⚠️ 試聽失敗："+(e?.message||String(e))}}
'''
assert anchor in s
s=s.replace(anchor,anchor+insert,1)

old='''$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();$$("input[name=audioEngine]").forEach(x=>x.onchange=syncAudioPanels);syncAudioPanels();
loadVoices();if("speechSynthesis"in window&&speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=loadVoices;Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex()]).then(render);'''
new='''$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;$("#enableAI").onclick=enableAI;$("#sampleVoice").onclick=playSetupSample;$("#voicevoxVoice").onchange=updateVoicevoxVoice;$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();$$("input[name=audioEngine]").forEach(x=>x.onchange=()=>{syncAudioPanels();availability()});syncAudioPanels();
loadVoices();if("speechSynthesis"in window&&speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=loadVoices;ensureSupertonicCache().then(updateAiCacheStatus);Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex()]).then(render);'''
assert old in s
s=s.replace(old,new,1)

# Guard against reintroducing the repeat-play bug.
assert 'activeAiAudio.src=""' not in s
assert 'candidate.audio.src=""' not in s
assert 'id="voicevoxVoice"' in s
assert 'id="sampleVoice"' in s
assert 'supertonic-sw.js' in s

p.write_text(s,encoding='utf-8')

sw=Path('supertonic-sw.js')
sw.write_text(r'''const CACHE_NAME="supertonic-model-v1";
self.addEventListener("install",event=>{self.skipWaiting()});
self.addEventListener("activate",event=>{event.waitUntil(self.clients.claim())});
function isSupertonicAsset(request){try{const u=new URL(request.url);return u.hostname==="huggingface.co"&&u.pathname.startsWith("/Supertone/supertonic-3/resolve/")&&(u.pathname.includes("/onnx/")||u.pathname.includes("/voice_styles/"))}catch{return false}}
self.addEventListener("fetch",event=>{if(!isSupertonicAsset(event.request))return;event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const hit=await cache.match(event.request,{ignoreSearch:true});if(hit)return hit;const response=await fetch(event.request);if(response.ok||response.type==="opaque")await cache.put(event.request,response.clone());return response})())});
''',encoding='utf-8')
print('Patched Listening to v1.7 audio controls and persistent Supertonic cache')
