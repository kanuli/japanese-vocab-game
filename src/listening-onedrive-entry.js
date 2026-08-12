import {
  PublicClientApplication,
  BrowserCacheLocation,
  InteractionRequiredAuthError
} from '@azure/msal-browser';
import { unzipSync, strFromU8 } from 'fflate';

const CLIENT_ID_KEY='jplistening_onedrive_client_id';
const ACCOUNT_HINT_KEY='jplistening_onedrive_login_hint';
const GRAPH='https://graph.microsoft.com/v1.0';
let app=null;
let appClientId='';
let account=null;
let initPromise=null;
let indexCache=null;
const urlCache=new Map();

function baseConfig(){
  const c=window.ONEDRIVE_VOICEVOX_CONFIG||{};
  const stored=(localStorage.getItem(CLIENT_ID_KEY)||'').trim();
  return {
    clientId:stored||String(c.clientId||'').trim(),
    authority:c.authority||'https://login.microsoftonline.com/consumers',
    redirectUri:c.redirectUri||`${location.origin}${location.pathname}`,
    scopes:Array.isArray(c.scopes)&&c.scopes.length?c.scopes:['Files.ReadWrite.AppFolder'],
    indexFile:c.indexFile||'voicevox-index.json',
    audioDir:c.audioDir||'voicevox'
  };
}

function isConfigured(){return !!baseConfig().clientId}
function savedClientId(){return baseConfig().clientId}
function savedLoginHint(){
  try{return (localStorage.getItem(ACCOUNT_HINT_KEY)||'').trim()}catch{return ''}
}
function rememberAccount(acct){
  account=acct||null;
  if(account){
    try{
      const hint=String(account.username||'').trim();
      if(hint)localStorage.setItem(ACCOUNT_HINT_KEY,hint);
    }catch{}
    try{app?.setActiveAccount(account)}catch{}
  }
  return account;
}
function authErrorCode(e){
  return String(e?.errorCode||e?.code||e?.name||'').toLowerCase();
}
function isLostRequestCacheError(e){
  const c=authErrorCode(e);
  return c==='no_token_request_cache_error'||c==='unable_to_parse_token_request_cache_error';
}
function clearStaleAuthResponse(){
  try{
    const u=new URL(location.href);
    const keys=['code','state','session_state','client_info','error','error_description','error_subcode'];
    let changed=false;
    for(const k of keys)if(u.searchParams.has(k)){u.searchParams.delete(k);changed=true}
    if(u.hash&&/[#&](code|state|session_state|client_info|error|error_description)=/i.test(u.hash)){
      u.hash='';changed=true;
    }
    if(changed)history.replaceState(history.state,'',u.pathname+u.search+u.hash);
  }catch{}
}
function reconnectError(){
  const e=new Error('Microsoft 登入已失效。請在「⚙️ VOICEVOX 設定／維護」內按「重新連接 OneDrive」一次。');
  e.code='onedrive_reconnect_required';
  return e;
}
function setClientId(id){
  id=String(id||'').trim();
  const previous=baseConfig().clientId;
  if(id)localStorage.setItem(CLIENT_ID_KEY,id);else localStorage.removeItem(CLIENT_ID_KEY);
  if(previous&&previous!==id){try{localStorage.removeItem(ACCOUNT_HINT_KEY)}catch{}}
  app=null;appClientId='';account=null;initPromise=null;indexCache=null;urlCache.clear();
  return id;
}

async function getApp(){
  const c=baseConfig();
  if(!c.clientId)throw new Error('尚未設定 Microsoft Application (client) ID');
  if(app&&appClientId===c.clientId)return app;
  app=new PublicClientApplication({
    auth:{
      clientId:c.clientId,
      authority:c.authority,
      redirectUri:c.redirectUri,
      postLogoutRedirectUri:c.redirectUri,
      navigateToLoginRequestUrl:false
    },
    cache:{cacheLocation:BrowserCacheLocation.LocalStorage}
  });
  appClientId=c.clientId;
  await app.initialize();
  let redirect=null;
  try{
    redirect=await app.handleRedirectPromise();
  }catch(e){
    if(!isLostRequestCacheError(e))throw e;
    // MSAL v4+ can lose the encrypted redirect request when the browser-session
    // encryption cookie disappears. The authorization response cannot be reused;
    // remove it so the site does not fail on every subsequent load.
    clearStaleAuthResponse();
  }
  rememberAccount(redirect?.account||app.getActiveAccount()||app.getAllAccounts()[0]||null);
  return app;
}

async function recoverSilentSession(a){
  const c=baseConfig();
  const hint=savedLoginHint();
  if(!hint)return null;
  try{
    const r=await a.ssoSilent({scopes:c.scopes,loginHint:hint});
    rememberAccount(r?.account||a.getActiveAccount()||a.getAllAccounts()[0]||null);
    return r||null;
  }catch{
    return null;
  }
}

async function init(){
  if(!isConfigured())return {configured:false,signedIn:false,account:null};
  if(initPromise)return initPromise;
  initPromise=(async()=>{
    const a=await getApp();
    rememberAccount(a.getActiveAccount()||a.getAllAccounts()[0]||account||null);
    if(!account)await recoverSilentSession(a);
    return {configured:true,signedIn:!!account,account:account?.username||account?.name||''};
  })().catch(e=>{initPromise=null;throw e});
  return initPromise;
}

async function signIn(){
  const a=await getApp();
  const c=baseConfig();
  try{
    const r=await a.loginPopup({scopes:c.scopes,prompt:'select_account'});
    rememberAccount(r.account);
    initPromise=null;
    return {signedIn:true,account:account?.username||account?.name||''};
  }catch(e){
    // Popup restrictions are common on mobile Safari. Redirect is the reliable fallback.
    const code=String(e?.errorCode||e?.name||'').toLowerCase();
    if(code.includes('popup')||code.includes('empty_window')||code.includes('block')){
      await a.loginRedirect({scopes:c.scopes,prompt:'select_account'});
      return {signedIn:false,redirecting:true,account:''};
    }
    throw e;
  }
}

async function signOut(){
  if(!app)return;
  const a=await getApp();
  const acct=a.getActiveAccount()||a.getAllAccounts()[0]||null;
  if(acct)await a.logoutPopup({account:acct,postLogoutRedirectUri:baseConfig().redirectUri});
  account=null;initPromise=null;indexCache=null;urlCache.clear();
  try{localStorage.removeItem(ACCOUNT_HINT_KEY)}catch{}
}

async function token(){
  const a=await getApp();
  const c=baseConfig();
  let acct=a.getActiveAccount()||a.getAllAccounts()[0]||account;
  if(!acct){
    const recovered=await recoverSilentSession(a);
    if(recovered?.accessToken)return recovered.accessToken;
    acct=a.getActiveAccount()||a.getAllAccounts()[0]||account;
  }
  if(!acct)throw reconnectError();
  try{
    const r=await a.acquireTokenSilent({account:acct,scopes:c.scopes});
    rememberAccount(r?.account||acct);
    return r.accessToken;
  }catch(e){
    const code=authErrorCode(e);
    if(e instanceof InteractionRequiredAuthError||code.includes('interaction')||code==='no_account_error'||isLostRequestCacheError(e)){
      const recovered=await recoverSilentSession(a);
      if(recovered?.accessToken)return recovered.accessToken;
      throw reconnectError();
    }
    throw e;
  }
}

class GraphError extends Error{
  constructor(status,message){super(message);this.status=status}
}

async function graph(path,{method='GET',body=null,headers={}}={}){
  const accessToken=await token();
  const h={Authorization:`Bearer ${accessToken}`,...headers};
  let payload=body;
  if(body&&typeof body==='object'&&!(body instanceof Blob)&&!(body instanceof ArrayBuffer)){
    h['Content-Type']=h['Content-Type']||'application/json';
    payload=JSON.stringify(body);
  }
  const r=await fetch(GRAPH+path,{method,headers:h,body:payload});
  if(!r.ok){
    let detail='';
    try{const d=await r.json();detail=d?.error?.message||''}catch{}
    throw new GraphError(r.status,detail||`Microsoft Graph HTTP ${r.status}`);
  }
  if(r.status===204)return null;
  const type=r.headers.get('content-type')||'';
  if(type.includes('application/json'))return r.json();
  return r;
}

function encodePath(path){
  return String(path||'').split('/').filter(Boolean).map(encodeURIComponent).join('/');
}

async function ensureAppRoot(){
  return graph('/me/drive/special/approot');
}

async function ensureFolder(name){
  try{
    return await graph('/me/drive/special/approot/children',{
      method:'POST',
      body:{name,folder:{},'@microsoft.graph.conflictBehavior':'fail'}
    });
  }catch(e){
    if(e?.status!==409)throw e;
    return graph(`/me/drive/special/approot:/${encodePath(name)}`);
  }
}

async function metadata(path){
  const p=encodePath(path);
  return graph(`/me/drive/special/approot:/${p}?%24select=id,name,size,file,%40microsoft.graph.downloadUrl`);
}

async function downloadUrl(path){
  const cached=urlCache.get(path);
  if(cached&&cached.until>Date.now())return cached.value;
  const item=await metadata(path);
  const url=item?.['@microsoft.graph.downloadUrl'];
  if(!url)throw new Error(`OneDrive 沒有提供下載網址：${path}`);
  const value={url,path,name:item.name||'',size:Number(item.size||0)};
  // Graph download URLs are short-lived. Cache only briefly, never persist them.
  urlCache.set(path,{value,until:Date.now()+15*60*1000});
  return value;
}

async function putText(path,text,type='application/json'){
  const accessToken=await token();
  const p=encodePath(path);
  const r=await fetch(`${GRAPH}/me/drive/special/approot:/${p}:/content`,{
    method:'PUT',
    headers:{Authorization:`Bearer ${accessToken}`,'Content-Type':type},
    body:String(text)
  });
  if(!r.ok){
    let detail='';
    try{const d=await r.json();detail=d?.error?.message||''}catch{}
    throw new GraphError(r.status,detail||`Microsoft Graph HTTP ${r.status}`);
  }
  return r.json();
}

async function putBytes(path,bytes,type='application/octet-stream'){
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

async function ensureStructure(){
  const c=baseConfig();
  await ensureAppRoot();
  await ensureFolder(c.audioDir);
  try{await metadata(c.indexFile)}catch(e){
    if(e?.status!==404)throw e;
    await putText(c.indexFile,JSON.stringify({version:1,items:{}},null,2));
  }
  indexCache=null;
  return {audioDir:c.audioDir,indexFile:c.indexFile};
}

async function loadIndex(force=false){
  if(indexCache&&!force)return indexCache;
  const c=baseConfig();
  try{
    const f=await downloadUrl(c.indexFile);
    const r=await fetch(f.url,{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    const d=await r.json();
    indexCache=d&&typeof d==='object'?d:{version:1,items:{}};
  }catch(e){
    if(e?.status===404)indexCache={version:1,items:{}};else throw e;
  }
  return indexCache;
}

async function getAudio(question){
  await init();
  if(!account)throw new Error('請先按「連接 OneDrive」登入 Microsoft 帳戶');
  const c=baseConfig();
  let index={version:1,items:{}};
  try{index=await loadIndex()}catch{}
  const rec=index?.items?.[question.id]||{};
  const candidates=[];
  if(rec.path)candidates.push(rec.path);
  if(!rec.path){
    const base=`${c.audioDir}/${question.level}/${question.id}`;
    candidates.push(`${base}.mp3`,`${base}.m4a`,`${base}.wav`);
  }
  let last=null;
  for(const path of candidates){
    try{
      const file=await downloadUrl(path);
      return {
        ...file,
        speaker:rec.speaker||'',
        style:rec.style||'',
        credit:rec.credit||'',
        source:'VOICEVOX / OneDrive'
      };
    }catch(e){last=e;if(e?.status!==404)break}
  }
  if(last?.status&&last.status!==404)throw last;
  throw new GraphError(404,`OneDrive 找不到此題的 VOICEVOX 音訊：${question.id}`);
}

async function connectionInfo(){
  const s=await init();
  if(!s.configured)return s;
  if(!s.signedIn)return s;
  try{
    const root=await ensureAppRoot();
    let count=0;
    try{const i=await loadIndex();count=Object.keys(i?.items||{}).length}catch{}
    return {...s,appFolder:root?.name||'',indexed:count};
  }catch(e){
    if(e?.code==='onedrive_reconnect_required')return {...s,signedIn:false,reconnectRequired:true};
    throw e;
  }
}

window.OneDriveVoicevox={
  init,signIn,signOut,isConfigured,savedClientId,setClientId,
  ensureStructure,connectionInfo,getAudio,loadIndex,importVoicevoxZip
};
window.dispatchEvent(new Event('onedrive-voicevox-module-ready'));
