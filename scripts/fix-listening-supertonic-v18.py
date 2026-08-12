#!/usr/bin/env python3
from pathlib import Path

p = Path('listening.html')
s = p.read_text(encoding='utf-8')

assert '日本語聽解挑戰 v1.7｜JLPT N1–N5' in s
s = s.replace('日本語聽解挑戰 v1.7｜JLPT N1–N5', '日本語聽解挑戰 v1.8｜JLPT N1–N5', 1)

s = s.replace(
    '尚未載入 AI 模型。首次使用約需下載 400 MB；完成後會儲存在此瀏覽器的持久快取，正常情況不需要再次下載。',
    '正在檢查此瀏覽器是否已安裝 Supertonic AI 模型…首次使用需要保存約 400 MB；之後會直接從本機載入，不會再次從網路下載。',
    1,
)
s = s.replace(
    '<button id="enableAI" class="btn primary" style="width:100%;margin-top:8px">下載／啟用 AI 語音</button>',
    '<button id="enableAI" class="btn primary" style="width:100%;margin-top:8px">檢查 Supertonic AI</button>',
    1,
)

old_sync = '''function syncAudioPanels(){const mode=$("input[name=audioEngine]:checked")?.value||"ai";$("#voicevoxPanel").style.display=mode==="voicevox"?"block":"none";$("#aiPanel").style.display=mode==="ai"?"block":"none";$("#devicePanel").style.display=mode==="device"?"block":"none"}'''
new_sync = '''async function syncAudioPanels(){const mode=$("input[name=audioEngine]:checked")?.value||"ai";$("#voicevoxPanel").style.display=mode==="voicevox"?"block":"none";$("#aiPanel").style.display=mode==="ai"?"block":"none";$("#devicePanel").style.display=mode==="device"?"block":"none";if(mode==="ai"&&!window.SupertonicAI?.isReady?.()){const info=await supertonicCacheInfo();if(info.ready)void enableAI(false)}}'''
assert old_sync in s
s = s.replace(old_sync, new_sync, 1)

start = s.index('async function ensureSupertonicCache()')
end = s.index('\nfunction stopAllAudio()', start)
new_ai = r'''async function ensureSupertonicCache(){if(!("serviceWorker" in navigator)||!("caches" in window))return false;try{await navigator.serviceWorker.register("./supertonic-sw.js",{scope:"./"});await navigator.serviceWorker.ready;try{await navigator.storage?.persist?.()}catch{}return true}catch{return false}}
async function supertonicCacheInfo(){try{if(!("caches" in window))return{ready:false,modelCount:0};const c=await caches.open("supertonic-model-v1"),keys=await c.keys();const modelCount=keys.filter(r=>/\.onnx(?:\?|$)/i.test(r.url)).length;return{ready:modelCount>=4,modelCount}}catch{return{ready:false,modelCount:0}}}
async function updateAiCacheStatus(){const info=await supertonicCacheInfo(),b=$("#enableAI");if(window.SupertonicAI?.isReady?.()){$("#aiStatus").textContent="✅ Supertonic 3 AI 語音已載入；目前使用本機模型。";b.textContent="✅ Supertonic AI 已啟用";b.disabled=true;return info}if(info.ready){$("#aiStatus").textContent=`✅ 此瀏覽器已安裝 Supertonic 模型（${info.modelCount} 個主要模型）。選擇 Supertonic 時會直接從本機載入，不會重新下載 400 MB。`;b.textContent="載入已安裝的 Supertonic AI"}else{$("#aiStatus").textContent="首次使用：需要在此瀏覽器保存約 400 MB 的 Supertonic 模型。這只需安裝一次；完成後會直接從本機載入。";b.textContent="首次安裝 Supertonic（約 400 MB）"}return info}
async function enableAI(selectEngine=true){const b=$("#enableAI");if(aiInitPromise)return aiInitPromise;b.disabled=true;aiInitPromise=(async()=>{try{await ensureSupertonicCache();const before=await supertonicCacheInfo();const api=await waitForAiModule();$("#aiStatus").textContent=before.ready?"正在從此瀏覽器的本機快取載入 Supertonic…":"正在首次下載並安裝 Supertonic 模型（約 400 MB）…";await api.preflight();await api.init(msg=>{$("#aiStatus").textContent=before.ready?"正在從本機快取載入 Supertonic 模型…":msg});save("jplistening_supertonic_installed",{installed:true,at:Date.now()});$("#aiStatus").textContent=before.ready?"✅ Supertonic 3 已從本機快取載入；沒有重新下載 400 MB。":"✅ Supertonic 3 首次安裝完成；模型已保存在此瀏覽器，之後不需再次下載。";if(selectEngine){$("#engineAI").checked=true;await syncAudioPanels()}return true}catch(e){$("#aiStatus").textContent="⚠️ Supertonic 無法啟用："+(e?.message||String(e))+"。裝置語音仍可使用。";return false}finally{b.disabled=false;await updateAiCacheStatus();aiInitPromise=null}})();return aiInitPromise}
async function initializeSupertonicPersistence(){await ensureSupertonicCache();const info=await updateAiCacheStatus();if($("input[name=audioEngine]:checked")?.value==="ai"&&info.ready&&!window.SupertonicAI?.isReady?.())void enableAI(false);return info}'''
s = s[:start] + new_ai + s[end:]

old_sample = 'const ok=await enableAI();if(!ok)throw new Error("Supertonic 尚未準備完成")'
assert old_sample in s
s = s.replace(old_sample, 'const ok=await enableAI(false);if(!ok)throw new Error("Supertonic 尚未準備完成")', 1)

old_speak = '''else{$("#aiStatus").textContent="AI 尚未啟用。按「下載／啟用 AI 語音」後可使用真正 AI 聲線；本次先用裝置語音。"}speakDevice(rate,"AI 備援");return'''
new_speak = '''else{const info=await supertonicCacheInfo();if(info.ready){const ok=await enableAI(false);if(ok&&window.SupertonicAI?.isReady?.()){try{const vid=selectedAiVoice();const out=await window.SupertonicAI.synthesize(game.current.jp,{voice:vid,speed:rate,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();unlockAfterPlay(`AI ${vid}`);return}catch{}}}$("#aiStatus").textContent=info.ready?"⚠️ 已安裝的 Supertonic 本次載入失敗；暫用裝置語音。":"Supertonic 尚未在此瀏覽器安裝。首次安裝約 400 MB；本次先用裝置語音。"}speakDevice(rate,"AI 備援");return'''
assert old_speak in s
s = s.replace(old_speak, new_speak, 1)

old_bind = '$("#next").onclick=next;$("#enableAI").onclick=enableAI;$("#sampleVoice").onclick=playSetupSample;'
new_bind = '$("#next").onclick=next;$("#enableAI").onclick=()=>enableAI(true);$("#sampleVoice").onclick=playSetupSample;'
assert old_bind in s
s = s.replace(old_bind, new_bind, 1)

old_init = 'ensureSupertonicCache().then(updateAiCacheStatus);Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex()]).then(render);'
assert old_init in s
s = s.replace(old_init, 'Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex(),initializeSupertonicPersistence()]).then(render);', 1)

p.write_text(s, encoding='utf-8')
print('Patched Listening Supertonic behavior to v1.8')
