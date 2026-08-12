from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

s=s.replace('日本語聽解挑戰 v1.3｜JLPT N1–N5','日本語聽解挑戰 v1.4｜JLPT N1–N5',1)
s=s.replace('<script src="./onedrive-config.js"></script>\n','',1)
s=s.replace('<script type="module" src="./vendor/onedrive-voicevox.js"></script>\n','',1)

start=s.find('<div class="source"><strong>🔊 日語語音</strong>')
ai=s.find('<div id="aiPanel">', start)
if start<0 or ai<0:
    raise SystemExit('audio panel anchors not found')

new='''<div class="source"><strong>🔊 日語語音</strong>
<div class="muted" style="margin:5px 0 8px">VOICEVOX 音訊直接由公開 GitHub Releases 播放；不需外部雲端帳戶、信用卡或額外登入。Supertonic 與裝置語音只作備援。</div>
<div class="radios three" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked><label for="engineVoicevox">🎭 VOICEVOX<br>GitHub</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai"><label for="engineAI">✨ Supertonic<br>AI</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>語音</label></div></div>
<div id="voicevoxPanel">
<div id="voicevoxStatus" class="notice" style="margin:0 0 8px">正在載入 VOICEVOX 公開音訊索引…</div>
<div class="muted">音訊包由本專案 GitHub Actions 產生並直接發佈至 GitHub Releases。正常使用只需開啟網站並開始練習。</div>
</div>
'''
s=s[:start]+new+s[ai:]

block_start=s.find('async function waitForOneDriveModule(){')
block_end=s.find('async function waitForAiModule(){', block_start)
if block_start<0 or block_end<0:
    raise SystemExit('OneDrive JS anchors not found')

replacement='''let voicevoxIndex={version:2,items:{}};
async function loadVoicevoxIndex(){const st=$("#voicevoxStatus");try{const r=await fetch("./voicevox-release-index.json",{cache:"no-cache"});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();if(!d||typeof d!=="object"||!d.items)throw new Error("索引格式不正確");voicevoxIndex=d;const n=Object.keys(d.items||{}).length;st.textContent=n?`✅ VOICEVOX 已準備：GitHub Releases 共 ${n.toLocaleString()} 題音訊。現在可直接開始。`:"⚠️ VOICEVOX 音訊索引目前是空的，將使用其他語音備援。";return n}catch(e){voicevoxIndex={version:2,items:{}};st.textContent="⚠️ VOICEVOX 公開音訊包尚未發佈或暫時無法讀取；將使用其他語音備援。";return 0}}
async function prepareVoicevoxAudio(q){const rec=voicevoxIndex?.items?.[q.id];if(!rec?.url)return null;try{const audio=new Audio(rec.url);audio.preload="auto";return{audio,out:{...rec,source:"VOICEVOX / GitHub Releases"}}}catch{return null}}
async function speakVoicevox(rate=1){const st=$("#voicevoxStatus");try{let prepared=game.voicevoxPrepared;if(!prepared&&game.voicevoxPromise)prepared=await game.voicevoxPromise;if(!prepared)prepared=await prepareVoicevoxAudio(game.current);if(!prepared)throw new Error("此題尚未有 VOICEVOX 音訊");game.voicevoxPrepared=prepared;activeAiAudio=prepared.audio;activeAiAudio.currentTime=0;activeAiAudio.playbackRate=rate;try{await activeAiAudio.play()}catch(e){if(String(e?.name||"").includes("NotAllowed")){$("#playCount").textContent="✅ VOICEVOX 已載入；iPhone/Safari 請再按一次播放。";return true}throw e}const meta=prepared.out;const who=[meta.speaker,meta.style].filter(Boolean).join("／");unlockAfterPlay(`VOICEVOX${who?" · "+who:""}`);return true}catch(e){st.textContent="⚠️ VOICEVOX 此題無法播放，已改用其他語音備援。";return false}}

'''
s=s[:block_start]+replacement+s[block_end:]

s=s.replace('if(mode==="voicevox"){if(await speakOneDrive(rate))return;', 'if(mode==="voicevox"){if(await speakVoicevox(rate))return;',1)
s=s.replace('game.voicevoxPromise=$("input[name=audioEngine]:checked")?.value==="voicevox"?prepareOneDriveAudio(q):null;', 'game.voicevoxPromise=$("input[name=audioEngine]:checked")?.value==="voicevox"?prepareVoicevoxAudio(q):null;',1)

for old in [
'$("#onedriveSaveConfig").onclick=saveOneDriveClientId;$("#onedriveConnect").onclick=connectOneDrive;$("#onedriveSetup").onclick=setupOneDrive;\n',
'$("#voicevoxImport").addEventListener("click",()=>$("#voicevoxZip").click());\n',
'$("#voicevoxZip").addEventListener("change",e=>{const f=e.target.files?.[0];if(f)importVoicevoxPack(f)});'
]:
    s=s.replace(old,'',1)

s=s.replace('Promise.allSettled([loadWeb(),initFurigana(),refreshOneDriveStatus()]).then(render);','Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex()]).then(render);',1)
s=s.replace('Web 句子來源：Hanabira。VOICEVOX 音訊可存於你的 OneDrive App Folder；Supertonic 3 在瀏覽器內 ONNX 運算；裝置日語語音只作備援。','Web 句子來源：Hanabira。VOICEVOX 音訊由公開 GitHub Releases 提供，不需登入；Supertonic 3 在瀏覽器內 ONNX 運算；裝置日語語音只作備援。',1)

for bad in ['OneDrive','Microsoft Application (client) ID','Files.ReadWrite.AppFolder','voicevoxImport','onedriveStatus','waitForOneDriveModule','prepareOneDriveAudio','speakOneDrive']:
    if bad in s:
        raise SystemExit(f'old storage content still present: {bad}')

p.write_text(s,encoding='utf-8')
print('Patched listening.html to GitHub Releases VOICEVOX storage')
