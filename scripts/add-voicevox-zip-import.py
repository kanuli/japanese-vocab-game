from pathlib import Path

# Patch OneDrive client source to support importing a generated VOICEVOX ZIP directly into OneDrive App Folder.
src = Path('src/listening-onedrive-entry.js')
s = src.read_text(encoding='utf-8')

if "from 'fflate'" not in s:
    anchor = "} from '@azure/msal-browser';\n"
    if anchor not in s:
        raise SystemExit('MSAL import anchor not found')
    s = s.replace(anchor, anchor + "import { unzipSync, strFromU8 } from 'fflate';\n", 1)

if 'async function importVoicevoxZip' not in s:
    anchor = "async function ensureStructure(){\n"
    if anchor not in s:
        raise SystemExit('ensureStructure anchor not found')
    code = r'''async function putBytes(path,bytes,type='application/octet-stream'){
  const accessToken=await token();
  const p=encodePath(path);
  const r=await fetch(`${GRAPH}/me/drive/special/approot:/${p}:/content`,{
    method:'PUT',
    headers:{Authorization:`Bearer ${accessToken}`,'Content-Type':type},
    body:bytes
  });
  if(!r.ok){
    let detail='';
    try{const d=await r.json();detail=d?.error?.message||''}catch{}
    throw new GraphError(r.status,detail||`Microsoft Graph HTTP ${r.status}`);
  }
  return r.json();
}

async function ensureFolderPath(path){
  const parts=String(path||'').split('/').filter(Boolean);
  let current='';
  for(const name of parts){
    const parent=current;
    current=current?`${current}/${name}`:name;
    try{await metadata(current);continue}catch(e){if(e?.status!==404)throw e}
    const endpoint=parent
      ? `/me/drive/special/approot:/${encodePath(parent)}:/children`
      : '/me/drive/special/approot/children';
    try{
      await graph(endpoint,{method:'POST',body:{name,folder:{},'@microsoft.graph.conflictBehavior':'fail'}});
    }catch(e){
      if(e?.status!==409)throw e;
    }
  }
}

function zipMime(path){
  if(/\.mp3$/i.test(path))return 'audio/mpeg';
  if(/\.m4a$/i.test(path))return 'audio/mp4';
  if(/\.wav$/i.test(path))return 'audio/wav';
  return 'application/octet-stream';
}

function unpackVoicevoxArchive(bytes){
  let files=unzipSync(bytes);
  let names=Object.keys(files);
  let indexName=names.find(n=>n==='voicevox-index.json'||n.endsWith('/voicevox-index.json'));
  if(!indexName){
    // Backward compatibility with the old artifact that contained an inner ZIP.
    const nested=names.find(n=>/\.zip$/i.test(n)&&files[n]?.length);
    if(nested){
      files=unzipSync(files[nested]);
      names=Object.keys(files);
      indexName=names.find(n=>n==='voicevox-index.json'||n.endsWith('/voicevox-index.json'));
    }
  }
  if(!indexName)throw new Error('ZIP 內找不到 voicevox-index.json；請使用本專案 GitHub Actions 產生的 VOICEVOX 音訊包。');
  const prefix=indexName.slice(0,indexName.length-'voicevox-index.json'.length);
  const pack=JSON.parse(strFromU8(files[indexName]));
  if(pack?.version!==1||!pack?.items||typeof pack.items!=='object')throw new Error('voicevox-index.json 格式不正確');
  const audio=[];
  for(const name of names){
    if(!name.startsWith(prefix))continue;
    const rel=name.slice(prefix.length).replace(/^\/+/, '');
    if(!/^voicevox\//.test(rel)||!/(\.mp3|\.m4a|\.wav)$/i.test(rel))continue;
    if(files[name]?.length)audio.push({path:rel,bytes:files[name]});
  }
  if(!audio.length)throw new Error('ZIP 內沒有找到 VOICEVOX MP3/M4A/WAV 音訊');
  return {pack,audio};
}

async function importVoicevoxZip(file,onProgress=()=>{}){
  const state=await init();
  if(!state.signedIn)throw new Error('請先連接 OneDrive');
  if(!file||typeof file.arrayBuffer!=='function')throw new Error('請選擇 VOICEVOX ZIP 音訊包');
  onProgress({phase:'read',message:'正在讀取 ZIP…',done:0,total:0});
  const parsed=unpackVoicevoxArchive(new Uint8Array(await file.arrayBuffer()));
  await ensureStructure();

  // Create every required directory before parallel uploads.
  const dirs=[...new Set(parsed.audio.map(x=>x.path.split('/').slice(0,-1).join('/')).filter(Boolean))]
    .sort((a,b)=>a.split('/').length-b.split('/').length||a.localeCompare(b));
  for(const d of dirs)await ensureFolderPath(d);

  let done=0;
  const total=parsed.audio.length;
  let cursor=0;
  async function worker(){
    while(true){
      const i=cursor++;
      if(i>=total)return;
      const item=parsed.audio[i];
      await putBytes(item.path,item.bytes,zipMime(item.path));
      done++;
      onProgress({phase:'upload',message:`正在上傳 ${done}/${total}…`,done,total,path:item.path});
    }
  }
  const workers=Array.from({length:Math.min(3,total)},()=>worker());
  await Promise.all(workers);

  let existing={version:1,items:{}};
  try{existing=await loadIndex(true)}catch{}
  const merged={
    version:1,
    items:{...(existing?.items||{}),...(parsed.pack.items||{})}
  };
  await putText(baseConfig().indexFile,JSON.stringify(merged,null,2));
  indexCache=merged;
  urlCache.clear();
  onProgress({phase:'done',message:`✅ 已上傳 ${total} 個 VOICEVOX 音訊；索引共有 ${Object.keys(merged.items).length} 題。`,done:total,total});
  return {uploaded:total,indexed:Object.keys(merged.items).length};
}

'''
    s = s.replace(anchor, code + anchor, 1)

old = "  init,signIn,signOut,isConfigured,savedClientId,setClientId,\n  ensureStructure,connectionInfo,getAudio,loadIndex\n};"
new = "  init,signIn,signOut,isConfigured,savedClientId,setClientId,\n  ensureStructure,connectionInfo,getAudio,loadIndex,importVoicevoxZip\n};"
if old in s:
    s = s.replace(old,new,1)
elif 'importVoicevoxZip' not in s.split('window.OneDriveVoicevox={',1)[-1]:
    raise SystemExit('OneDrive export anchor not found')
src.write_text(s,encoding='utf-8')

# Patch listening UI and handlers.
p=Path('listening.html')
h=p.read_text(encoding='utf-8')

if 'id="voicevoxZip"' not in h:
    anchor='<div class="muted" style="margin-top:5px">音訊命名：<code>voicevox/N5/N5-0-0.mp3</code>。如果有 <code>voicevox-index.json</code>，回答後亦可顯示角色／風格。</div>'
    if anchor not in h:
        raise SystemExit('VOICEVOX panel anchor not found')
    block='''<div class="source" style="margin-top:10px;margin-bottom:0"><strong>🎵 VOICEVOX 音訊包</strong><div class="muted" style="margin-top:5px">不需要在手機安裝 VOICEVOX。先到 GitHub Actions 產生音訊包並下載 ZIP，再回來把 ZIP 直接匯入 OneDrive；本頁會自動解壓、建立資料夾、上傳音訊並合併索引。</div><div class="row" style="margin-top:8px"><a id="voicevoxGenerate" class="btn" href="https://github.com/kanuli/japanese-vocab-game/actions/workflows/generate-voicevox-pack.yml" target="_blank" rel="noopener">① 產生／下載音訊包</a><button id="voicevoxImport" class="btn primary" disabled>② 匯入 ZIP 到 OneDrive</button><input id="voicevoxZip" type="file" accept=".zip,application/zip" hidden></div><div id="voicevoxImportStatus" class="notice" style="margin-top:8px">先連接 OneDrive，再下載 GitHub Actions 產生的 ZIP。</div></div>'''
    h=h.replace(anchor,anchor+block,1)

# Add import button state to OneDrive status function.
old='const st=$("#onedriveStatus"),radio=$("#engineVoicevox"),connect=$("#onedriveConnect"),setup=$("#onedriveSetup"),input=$("#onedriveClientId");'
new='const st=$("#onedriveStatus"),radio=$("#engineVoicevox"),connect=$("#onedriveConnect"),setup=$("#onedriveSetup"),input=$("#onedriveClientId"),importBtn=$("#voicevoxImport");'
if old in h:
    h=h.replace(old,new,1)

old='radio.disabled=false;connect.disabled=true;setup.disabled=true;st.textContent="⚠️ 尚未設定 Microsoft Client ID。請依照下方設定步驟建立 Microsoft SPA，貼上 Client ID 後儲存。";return'
new='radio.disabled=false;connect.disabled=true;setup.disabled=true;if(importBtn)importBtn.disabled=true;st.textContent="⚠️ 尚未設定 Microsoft Client ID。請依照下方設定步驟建立 Microsoft SPA，貼上 Client ID 後儲存。";return'
if old in h:h=h.replace(old,new,1)
old='if(info.signedIn){setup.disabled=false;st.textContent=`✅ OneDrive 已連接：${info.account||"Microsoft 帳戶"} · 索引 ${info.indexed||0} 題。`}else{setup.disabled=true;st.textContent="✅ Client ID 已設定。請按「連接 OneDrive」登入；只會要求本遊戲 App Folder 權限。"}'
new='if(info.signedIn){setup.disabled=false;if(importBtn)importBtn.disabled=false;st.textContent=`✅ OneDrive 已連接：${info.account||"Microsoft 帳戶"} · 索引 ${info.indexed||0} 題。`}else{setup.disabled=true;if(importBtn)importBtn.disabled=true;st.textContent="✅ Client ID 已設定。請按「連接 OneDrive」登入；只會要求本遊戲 App Folder 權限。"}'
if old in h:h=h.replace(old,new,1)
old='radio.disabled=false;connect.disabled=false;setup.disabled=true;st.textContent="⚠️ OneDrive 狀態檢查失敗："+(e?.message||String(e))'
new='radio.disabled=false;connect.disabled=false;setup.disabled=true;if(importBtn)importBtn.disabled=true;st.textContent="⚠️ OneDrive 狀態檢查失敗："+(e?.message||String(e))'
if old in h:h=h.replace(old,new,1)

if 'async function importVoicevoxPack' not in h:
    anchor='async function setupOneDrive(){'
    if anchor not in h:
        raise SystemExit('setupOneDrive function anchor not found')
    code='''async function importVoicevoxPack(file){const status=$("#voicevoxImportStatus"),button=$("#voicevoxImport");button.disabled=true;try{const api=await waitForOneDriveModule();const result=await api.importVoicevoxZip(file,p=>{status.textContent=p.message||"正在匯入…"});status.textContent=`✅ 匯入完成：${result.uploaded} 個音訊；OneDrive 索引共 ${result.indexed} 題。`;await refreshOneDriveStatus()}catch(e){status.textContent="⚠️ 匯入失敗："+(e?.message||String(e))}finally{$("#voicevoxZip").value="";try{const info=await (await waitForOneDriveModule()).connectionInfo();button.disabled=!info.signedIn}catch{button.disabled=true}}}\n'''
    h=h.replace(anchor,code+anchor,1)

# Add event handlers next to existing OneDrive handlers.
if 'voicevoxZip").addEventListener' not in h:
    anchor='$("#onedriveSetup").addEventListener("click",setupOneDrive);'
    if anchor not in h:
        # Older style might use onclick assignment.
        anchor='$("#onedriveSetup").onclick=setupOneDrive;'
    if anchor not in h:
        raise SystemExit('OneDrive event handler anchor not found')
    extra='''\n$("#voicevoxImport").addEventListener("click",()=>$("#voicevoxZip").click());\n$("#voicevoxZip").addEventListener("change",e=>{const f=e.target.files?.[0];if(f)importVoicevoxPack(f)});'''
    h=h.replace(anchor,anchor+extra,1)

p.write_text(h,encoding='utf-8')

# Simplify generator artifact: upload the pack directory directly so the user downloads exactly one ZIP.
w=Path('.github/workflows/generate-voicevox-pack.yml')
y=w.read_text(encoding='utf-8')
create='''      - name: Create ZIP\n        run: |\n          cd voicevox-pack\n          zip -qr ../voicevox-${{ inputs.jlpt }}-${{ inputs.speaker_name }}.zip .\n\n'''
y=y.replace(create,'')
y=y.replace('          path: voicevox-${{ inputs.jlpt }}-${{ inputs.speaker_name }}.zip','          path: voicevox-pack/')
w.write_text(y,encoding='utf-8')
print('VOICEVOX ZIP import flow patched')
