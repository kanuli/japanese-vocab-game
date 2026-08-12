from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

start=s.find('<div id="voicevoxPanel"')
end=s.find('\n<div id="aiPanel">', start)
if start < 0 or end < 0:
    raise SystemExit('VOICEVOX panel anchors not found')

new_panel='''<div id="voicevoxPanel" style="display:none">
<div id="onedriveStatus" class="notice" style="margin:0 0 8px">正在自動連接 OneDrive…</div>
<details id="voicevoxSettings" style="margin-top:8px">
<summary style="cursor:pointer;font-weight:800;color:var(--muted)">⚙️ VOICEVOX 設定／維護</summary>
<div style="padding-top:10px">
<div class="muted" style="margin-bottom:8px">只有首次設定、重新登入或更新音訊包時才需要使用以下功能；平常開啟網站後會自動使用 OneDrive 的 VOICEVOX 音訊。</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Microsoft Application (client) ID</label><input id="onedriveClientId" type="text" autocomplete="off" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"></div>
<div class="row" style="margin-top:8px"><button id="onedriveSaveConfig" class="btn">儲存 Client ID</button><button id="onedriveConnect" class="btn primary">重新連接 OneDrive</button><button id="onedriveSetup" class="btn">修復 VOICEVOX 資料夾</button></div>
<div class="source" style="margin-top:10px;margin-bottom:0"><strong>🎵 更新 VOICEVOX 音訊包</strong><div class="muted" style="margin-top:5px">這裡只供更新／維護使用；已有音訊包後，日常使用不需要再下載或匯入。</div><div class="row" style="margin-top:8px"><a id="voicevoxGenerate" class="btn" href="https://github.com/kanuli/japanese-vocab-game/actions/workflows/generate-voicevox-pack.yml" target="_blank" rel="noopener">產生更新包</a><button id="voicevoxImport" class="btn primary" disabled>匯入更新包</button><input id="voicevoxZip" type="file" accept=".zip,application/zip" hidden></div><div id="voicevoxImportStatus" class="notice" style="margin-top:8px">已有音訊包時不需要操作。</div></div>
</div>
</details>
</div>'''

s=s[:start]+new_panel+s[end:]

# Prefer VOICEVOX in the normal UI. The status refresh below only leaves setup open when it is not ready.
s=s.replace('id="engineVoicevox" name="audioEngine" type="radio" value="voicevox">',
            'id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked>',1)
s=s.replace('id="engineAI" name="audioEngine" type="radio" value="ai" checked>',
            'id="engineAI" name="audioEngine" type="radio" value="ai">',1)

fstart=s.find('async function refreshOneDriveStatus(){')
fend=s.find('async function saveOneDriveClientId()', fstart)
if fstart < 0 or fend < 0:
    raise SystemExit('refreshOneDriveStatus anchors not found')

new_refresh='''async function refreshOneDriveStatus(){const st=$("#onedriveStatus"),radio=$("#engineVoicevox"),connect=$("#onedriveConnect"),setup=$("#onedriveSetup"),input=$("#onedriveClientId"),importBtn=$("#voicevoxImport"),settings=$("#voicevoxSettings");try{const api=await waitForOneDriveModule();if(input&&!input.value)input.value=api.savedClientId?.()||"";radio.disabled=false;if(!api.isConfigured?.()){connect.disabled=true;setup.disabled=true;if(importBtn)importBtn.disabled=true;if(settings)settings.open=true;st.textContent="⚙️ VOICEVOX 尚未完成首次設定。完成一次設定後，日常開啟網站會自動使用。";return{ready:false}}connect.disabled=false;const info=await api.connectionInfo();if(info.signedIn){setup.disabled=false;if(importBtn)importBtn.disabled=false;const indexed=Number(info.indexed||0);if(indexed>0){radio.checked=true;syncAudioPanels();if(settings)settings.open=false;st.textContent=`✅ VOICEVOX 已準備：OneDrive 已自動連接 · ${indexed.toLocaleString()} 題音訊。現在可直接開始。`;return{ready:true,indexed}}if(settings)settings.open=true;st.textContent="⚠️ OneDrive 已自動連接，但尚未找到 VOICEVOX 音訊包。只需完成一次音訊包設定。";return{ready:false,indexed:0}}setup.disabled=true;if(importBtn)importBtn.disabled=true;if(settings)settings.open=true;st.textContent="⚠️ Microsoft 登入狀態已失效。請在設定／維護內重新連接一次 OneDrive。";return{ready:false}}catch(e){radio.disabled=false;connect.disabled=false;setup.disabled=true;if(importBtn)importBtn.disabled=true;if(settings)settings.open=true;st.textContent="⚠️ OneDrive 自動連接失敗："+(e?.message||String(e));return{ready:false}}}
'''

s=s[:fstart]+new_refresh+s[fend:]

# Ensure the maintenance text from the old UI is gone.
for forbidden in [
    '只要求 <strong>Files.ReadWrite.AppFolder</strong>',
    '音訊命名：<code>voicevox/N5/N5-0-0.mp3</code>',
    '① 產生／下載音訊包',
    '② 匯入 ZIP 到 OneDrive'
]:
    if forbidden in s:
        raise SystemExit(f'old setup text still present: {forbidden}')

p.write_text(s,encoding='utf-8')
print('Patched Listening UI for automatic VOICEVOX startup')
