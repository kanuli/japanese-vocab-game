from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

if 'id="engineVoicevox"' in s:
    print('OneDrive VOICEVOX UI already present')
    raise SystemExit(0)

def repl(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'patch anchor not found: {label}')
    s=s.replace(old,new,1)

s=s.replace('日本語聽解挑戰 v1.2｜JLPT N1–N5','日本語聽解挑戰 v1.3｜JLPT N1–N5',1)

repl(
'<script type="module" src="./vendor/supertonic-browser.js"></script>',
'<script type="module" src="./vendor/supertonic-browser.js"></script>\n<script src="./onedrive-config.js"></script>\n<script type="module" src="./vendor/onedrive-voicevox.js"></script>',
'head scripts')

repl(
'.radios{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-bottom:18px}.radios.two{grid-template-columns:1fr 1fr}',
'.radios{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-bottom:18px}.radios.two{grid-template-columns:1fr 1fr}.radios.three{grid-template-columns:repeat(3,1fr)}',
'radio css')
repl(
'@media(max-width:720px){.wrap{padding:12px}.top{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:1fr}.choices{grid-template-columns:1fr}.choice{min-height:68px}.radios{grid-template-columns:1fr 1fr}.answer-grid{grid-template-columns:82px 1fr}.sheet{bottom:max(8px,env(safe-area-inset-bottom))}.ear{font-size:60px}}',
'@media(max-width:720px){.wrap{padding:12px}.top{align-items:flex-start;flex-direction:column}.grid{grid-template-columns:1fr}.choices{grid-template-columns:1fr}.choice{min-height:68px}.radios{grid-template-columns:1fr 1fr}.radios.three{grid-template-columns:1fr}.answer-grid{grid-template-columns:82px 1fr}.sheet{bottom:max(8px,env(safe-area-inset-bottom))}.ear{font-size:60px}}',
'mobile css')

old_audio='''<div class="source"><strong>🔊 日語語音</strong>
<div class="muted" style="margin:5px 0 8px">AI 語音是真正不同的 AI 聲線；裝置語音只作備援。</div>
<div class="radios two" style="margin-bottom:9px"><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai" checked><label for="engineAI">✨ AI 日語語音</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置語音</label></div></div>
<div id="aiPanel">
<div id="aiStatus" class="notice" style="margin:0 0 8px">尚未下載 AI 模型。首次啟用約需下載 400 MB；之後瀏覽器通常可使用快取。</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Supertonic 3 AI 聲線</label><select id="aiVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="F1">🌙 沉穩低柔女聲（F1）</option><option value="F2">🌸 明亮活潑女聲（F2）</option><option value="F3">🎙️ 專業播音女聲（F3）</option><option value="F4">✨ 清晰自信女聲（F4）</option><option value="F5">💕 溫柔療癒女聲（F5）</option><option value="M1">⚡ 活力自信男聲（M1）</option><option value="M2">🌑 低沉穩重男聲（M2）</option><option value="M3">🧭 權威專業男聲（M3）</option><option value="M4">🙂 柔和親切男聲（M4）</option><option value="M5">📖 溫暖舒緩男聲（M5）</option><option value="random">🎲 每題隨機聲線</option></select><div id="aiVoiceDesc" class="notice" style="margin-top:7px">F1：沉穩、略低音、平靜而穩定。適合想聽較成熟、低柔的女聲。</div></div>
<button id="enableAI" class="btn primary" style="width:100%;margin-top:8px">下載／啟用 AI 語音</button>
<div class="muted" style="margin-top:7px">模型：Supertonic 3（日語）。模型在你的瀏覽器內運算，不會把題目送到語音 API。</div>
</div>
<div id="devicePanel" style="display:none;margin-top:8px"><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div><div class="field" style="margin-top:8px"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">裝置日語語音（備援）</label><select id="voice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">自動選擇日語語音</option></select></div></div>
</div>'''
new_audio='''<div class="source"><strong>🔊 日語語音</strong>
<div class="muted" style="margin:5px 0 8px">VOICEVOX 使用預先生成並存於你的 OneDrive 的真正角色音訊；Supertonic 可在瀏覽器動態生成；裝置語音只作備援。</div>
<div class="radios three" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox"><label for="engineVoicevox">🎭 VOICEVOX<br>OneDrive</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai" checked><label for="engineAI">✨ Supertonic<br>AI</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>語音</label></div></div>
<div id="voicevoxPanel" style="display:none">
<div id="onedriveStatus" class="notice" style="margin:0 0 8px">正在檢查 OneDrive 設定…</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Microsoft Application (client) ID</label><input id="onedriveClientId" type="text" autocomplete="off" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"></div>
<div class="row" style="margin-top:8px"><button id="onedriveSaveConfig" class="btn">儲存 Client ID</button><button id="onedriveConnect" class="btn primary">連接 OneDrive</button><button id="onedriveSetup" class="btn">建立 VOICEVOX 資料夾</button></div>
<div class="muted" style="margin-top:7px">只要求 <strong>Files.ReadWrite.AppFolder</strong>：遊戲只可存取 OneDrive 的「Apps／本遊戲」專用資料夾，不需讀取你整個 OneDrive。Client ID 不是密碼；本頁不需要 Client Secret。</div>
<div class="muted" style="margin-top:5px">音訊命名：<code>voicevox/N5/N5-0-0.mp3</code>。如果有 <code>voicevox-index.json</code>，回答後亦可顯示角色／風格。</div>
</div>
<div id="aiPanel">
<div id="aiStatus" class="notice" style="margin:0 0 8px">尚未下載 AI 模型。首次啟用約需下載 400 MB；之後瀏覽器通常可使用快取。</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Supertonic 3 AI 聲線</label><select id="aiVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="F1">🌙 沉穩低柔女聲（F1）</option><option value="F2">🌸 明亮活潑女聲（F2）</option><option value="F3">🎙️ 專業播音女聲（F3）</option><option value="F4">✨ 清晰自信女聲（F4）</option><option value="F5">💕 溫柔療癒女聲（F5）</option><option value="M1">⚡ 活力自信男聲（M1）</option><option value="M2">🌑 低沉穩重男聲（M2）</option><option value="M3">🧭 權威專業男聲（M3）</option><option value="M4">🙂 柔和親切男聲（M4）</option><option value="M5">📖 溫暖舒緩男聲（M5）</option><option value="random">🎲 每題隨機聲線</option></select><div id="aiVoiceDesc" class="notice" style="margin-top:7px">F1：沉穩、略低音、平靜而穩定。適合想聽較成熟、低柔的女聲。</div></div>
<button id="enableAI" class="btn primary" style="width:100%;margin-top:8px">下載／啟用 AI 語音</button>
<div class="muted" style="margin-top:7px">模型：Supertonic 3（日語）。模型在你的瀏覽器內運算，不會把題目送到語音 API。</div>
</div>
<div id="devicePanel" style="display:none;margin-top:8px"><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div><div class="field" style="margin-top:8px"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">裝置日語語音（備援）</label><select id="voice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">自動選擇日語語音</option></select></div></div>
</div>'''
repl(old_audio,new_audio,'audio source block')

repl(
'<div class="label">來源</div><div>Hanabira Web 例句</div>',
'<div class="label">語音</div><div id="aVoiceSource">尚未播放</div>\n<div class="label">來源</div><div>Hanabira Web 例句</div>',
'answer voice source')

s=s.replace(
'Web 句子來源：Hanabira。AI 語音：Supertonic 3（瀏覽器內 ONNX 運算；首次啟用需下載大型模型）；裝置日語語音只作備援。',
'Web 句子來源：Hanabira。VOICEVOX 音訊可存於你的 OneDrive App Folder；Supertonic 3 在瀏覽器內 ONNX 運算；裝置日語語音只作備援。',1)

repl(
'function syncAudioPanels(){const ai=$("input[name=audioEngine]:checked")?.value!=="device";$("#aiPanel").style.display=ai?"block":"none";$("#devicePanel").style.display=ai?"none":"block"}',
'''function syncAudioPanels(){const mode=$("input[name=audioEngine]:checked")?.value||"ai";$("#voicevoxPanel").style.display=mode==="voicevox"?"block":"none";$("#aiPanel").style.display=mode==="ai"?"block":"none";$("#devicePanel").style.display=mode==="device"?"block":"none"}''',
'syncAudioPanels')

onedrive_code='''
async function waitForOneDriveModule(){if(window.OneDriveVoicevox)return window.OneDriveVoicevox;await new Promise((resolve,reject)=>{let done=false;const ok=()=>{if(done)return;done=true;resolve()};window.addEventListener("onedrive-voicevox-module-ready",ok,{once:true});setTimeout(()=>{if(done)return;done=true;reject(new Error("OneDrive 模組載入逾時"))},12000)});if(!window.OneDriveVoicevox)throw new Error("OneDrive 模組未載入");return window.OneDriveVoicevox}
async function refreshOneDriveStatus(){const st=$("#onedriveStatus"),radio=$("#engineVoicevox"),connect=$("#onedriveConnect"),setup=$("#onedriveSetup"),input=$("#onedriveClientId");try{const api=await waitForOneDriveModule();if(input&&!input.value)input.value=api.savedClientId?.()||"";if(!api.isConfigured?.()){radio.disabled=true;connect.disabled=true;setup.disabled=true;st.textContent="⚠️ 尚未設定 Microsoft Client ID。請依照下方設定步驟建立 Microsoft SPA，貼上 Client ID 後儲存。";return}radio.disabled=false;connect.disabled=false;const info=await api.connectionInfo();if(info.signedIn){setup.disabled=false;st.textContent=`✅ OneDrive 已連接：${info.account||"Microsoft 帳戶"} · 索引 ${info.indexed||0} 題。`}else{setup.disabled=true;st.textContent="✅ Client ID 已設定。請按「連接 OneDrive」登入；只會要求本遊戲 App Folder 權限。"}}catch(e){radio.disabled=false;connect.disabled=false;setup.disabled=true;st.textContent="⚠️ OneDrive 狀態檢查失敗："+(e?.message||String(e))}}
async function saveOneDriveClientId(){try{const api=await waitForOneDriveModule();const id=$("#onedriveClientId").value.trim();if(!id){alert("請貼上 Microsoft Application (client) ID。");return}api.setClientId(id);location.reload()}catch(e){alert("無法儲存 Client ID："+(e?.message||String(e)))}}
async function connectOneDrive(){const b=$("#onedriveConnect");b.disabled=true;try{const api=await waitForOneDriveModule();await api.signIn();await refreshOneDriveStatus()}catch(e){$("#onedriveStatus").textContent="⚠️ OneDrive 登入失敗："+(e?.message||String(e))}finally{b.disabled=false}}
async function setupOneDrive(){const b=$("#onedriveSetup");b.disabled=true;try{const api=await waitForOneDriveModule();const r=await api.ensureStructure();$("#onedriveStatus").textContent=`✅ OneDrive 專用資料夾已準備：${r.audioDir}/；索引：${r.indexFile}`;await refreshOneDriveStatus()}catch(e){$("#onedriveStatus").textContent="⚠️ 建立 OneDrive 資料夾失敗："+(e?.message||String(e))}finally{b.disabled=false}}
async function prepareOneDriveAudio(q){try{const api=await waitForOneDriveModule();if(!api.isConfigured?.())return null;const info=await api.init();if(!info.signedIn)return null;const out=await api.getAudio(q);const audio=new Audio(out.url);audio.preload="auto";return{audio,out}}catch{return null}}
async function speakOneDrive(rate=1){const st=$("#onedriveStatus");try{let prepared=game.voicevoxPrepared;if(!prepared&&game.voicevoxPromise)prepared=await game.voicevoxPromise;if(!prepared){const api=await waitForOneDriveModule();if(!api.isConfigured?.())throw new Error("請先設定 Microsoft Client ID");const info=await api.init();if(!info.signedIn)throw new Error("請先按「連接 OneDrive」登入 Microsoft 帳戶");prepared=await prepareOneDriveAudio(game.current)}if(!prepared)throw new Error("此題尚未有 VOICEVOX 音訊");game.voicevoxPrepared=prepared;activeAiAudio=prepared.audio;activeAiAudio.currentTime=0;activeAiAudio.playbackRate=rate;try{await activeAiAudio.play()}catch(e){if(String(e?.name||"").includes("NotAllowed")){$("#playCount").textContent="✅ VOICEVOX 已載入；iPhone/Safari 請再按一次播放。";return true}throw e}const meta=prepared.out;const who=[meta.speaker,meta.style].filter(Boolean).join("／");unlockAfterPlay(`VOICEVOX${who?" · "+who:""}`);return true}catch(e){st.textContent="⚠️ VOICEVOX 無法播放："+(e?.message||String(e))+"。將使用其他語音備援。";return false}}
'''
repl(
'async function waitForAiModule(){',
onedrive_code+'\nasync function waitForAiModule(){',
'OneDrive helper insertion')

repl(
'function unlockAfterPlay(label){game.plays++;$("#playCount").textContent=`已播放 ${game.plays} 次 · ${label}`;if(game.locked){game.locked=false;$$(".choice").forEach(b=>{b.disabled=false;b.classList.remove("locked")})}}',
'function unlockAfterPlay(label){game.lastAudioLabel=label;game.plays++;$("#playCount").textContent=`已播放 ${game.plays} 次 · ${label}`;if(game.locked){game.locked=false;$$(".choice").forEach(b=>{b.disabled=false;b.classList.remove("locked")})}}',
'unlock label')

repl(
'function speakDevice(rate=1,fallback=false){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(game.current.jp);u.lang="ja-JP";u.rate=rate;u.pitch=1;u.volume=1;const v=chosenDeviceVoice();if(v)u.voice=v;speechSynthesis.speak(u);unlockAfterPlay((fallback?"AI 備援 · ":"")+(v?.name||"裝置日語語音"));return true}catch{return false}}',
'function speakDevice(rate=1,fallbackLabel=""){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(game.current.jp);u.lang="ja-JP";u.rate=rate;u.pitch=1;u.volume=1;const v=chosenDeviceVoice();if(v)u.voice=v;speechSynthesis.speak(u);unlockAfterPlay((fallbackLabel?fallbackLabel+" · ":"")+(v?.name||"裝置日語語音"));return true}catch{return false}}',
'speakDevice')

old_speak='''async function speak(rate=1){if(!game?.current)return;stopAllAudio();const useAI=$("input[name=audioEngine]:checked")?.value!=="device";if(useAI){const api=window.SupertonicAI;if(api?.isReady?.()){try{$("#playCount").textContent="AI 正在產生語音…";const vid=selectedAiVoice();const out=await api.synthesize(game.current.jp,{voice:vid,speed:rate,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();unlockAfterPlay(`AI ${vid}`);return}catch(e){$("#aiStatus").textContent="⚠️ AI 本次發音失敗，已改用裝置語音："+(e?.message||String(e))}}else{$("#aiStatus").textContent="AI 尚未啟用。按「下載／啟用 AI 語音」後可使用真正 AI 聲線；本次先用裝置語音。"}}speakDevice(rate,true)}'''
new_speak='''async function speak(rate=1){if(!game?.current)return;stopAllAudio();const mode=$("input[name=audioEngine]:checked")?.value||"ai";if(mode==="voicevox"){if(await speakOneDrive(rate))return;const ai=window.SupertonicAI;if(ai?.isReady?.()){try{$("#playCount").textContent="VOICEVOX 不可用，AI 正在產生備援語音…";const vid=selectedAiVoice();const out=await ai.synthesize(game.current.jp,{voice:vid,speed:rate,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();unlockAfterPlay(`VOICEVOX 備援 · AI ${vid}`);return}catch{}}speakDevice(rate,"VOICEVOX 備援");return}if(mode==="ai"){const api=window.SupertonicAI;if(api?.isReady?.()){try{$("#playCount").textContent="AI 正在產生語音…";const vid=selectedAiVoice();const out=await api.synthesize(game.current.jp,{voice:vid,speed:rate,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();unlockAfterPlay(`AI ${vid}`);return}catch(e){$("#aiStatus").textContent="⚠️ AI 本次發音失敗，已改用裝置語音："+(e?.message||String(e))}}else{$("#aiStatus").textContent="AI 尚未啟用。按「下載／啟用 AI 語音」後可使用真正 AI 聲線；本次先用裝置語音。"}speakDevice(rate,"AI 備援");return}speakDevice(rate)}'''
repl(old_speak,new_speak,'speak routing')

repl(
'game={pool:p,order:shuffle(p),limit:n,infinite:n===0,index:0,score:0,streak:0,current:null,plays:0,locked:false,quality:""}',
'game={pool:p,order:shuffle(p),limit:n,infinite:n===0,index:0,score:0,streak:0,current:null,plays:0,locked:false,quality:"",lastAudioLabel:"",voicevoxPromise:null,voicevoxPrepared:null}',
'game start state')

needle='''game.current=q;game.quality=m.quality;game.currentZh=prepared.find(x=>x.jp===q.jp)?.zh||"";game.plays=0;game.aiVoiceForQuestion=null;'''
replace='''game.current=q;game.quality=m.quality;game.currentZh=prepared.find(x=>x.jp===q.jp)?.zh||"";game.plays=0;game.lastAudioLabel="";game.voicevoxPrepared=null;game.voicevoxPromise=$("input[name=audioEngine]:checked")?.value==="voicevox"?prepareOneDriveAudio(q):null;game.aiVoiceForQuestion=null;'''
repl(needle,replace,'question preload')

repl(
'$("#aQuality").innerHTML=`<span class=quality>${esc(game.quality)}</span>`;',
'$("#aQuality").innerHTML=`<span class=quality>${esc(game.quality)}</span>`;$("#aVoiceSource").textContent=game.lastAudioLabel||"尚未播放";',
'answer audio label')

old_events='''$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();$$("input[name=audioEngine]").forEach(x=>x.onchange=syncAudioPanels);syncAudioPanels();
loadVoices();if("speechSynthesis"in window&&speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=loadVoices;Promise.allSettled([loadWeb(),initFurigana()]).then(render);'''
new_events='''$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();$("#onedriveSaveConfig").onclick=saveOneDriveClientId;$("#onedriveConnect").onclick=connectOneDrive;$("#onedriveSetup").onclick=setupOneDrive;$$("input[name=audioEngine]").forEach(x=>x.onchange=syncAudioPanels);syncAudioPanels();
loadVoices();if("speechSynthesis"in window&&speechSynthesis.onvoiceschanged!==undefined)speechSynthesis.onvoiceschanged=loadVoices;Promise.allSettled([loadWeb(),initFurigana(),refreshOneDriveStatus()]).then(render);'''
repl(old_events,new_events,'event bindings')

p.write_text(s,encoding='utf-8')
print('patched Listening Game with direct OneDrive VOICEVOX support')
