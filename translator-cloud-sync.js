(()=>{'use strict';
const HISTORY_KEY='jpTranslatorHistoryV2';
const AUTO_SAVE_KEY='jpTranslatorHistoryAutoSave';
const STATE_UPDATED_KEY='jpTranslatorHistoryStateUpdatedAt';
const REMOTE_UPDATED_KEY='jpTranslatorCloudRemoteUpdatedAt';
const CONFIG_KEY='jpTranslatorSupabaseConfigV1';
const EMAIL_KEY='jpTranslatorCloudEmail';
const HISTORY_LIMIT=100;
const TABLE='translation_sync_state';
let client=null,user=null,authSubscription=null,syncTimer=null,syncing=false;

const $=s=>document.querySelector(s);
const ui={
  status:$('#cloudStatus'),
  url:$('#cloudUrl'),
  key:$('#cloudKey'),
  email:$('#cloudEmail'),
  saveConfig:$('#cloudSaveConfig'),
  login:$('#cloudLogin'),
  sync:$('#cloudSyncNow'),
  logout:$('#cloudLogout'),
  configHint:$('#cloudConfigHint')
};
if(!ui.status)return;

function setStatus(text,state='idle'){
  ui.status.textContent=text;
  ui.status.dataset.state=state;
}
function readJSON(key,fallback){try{const x=JSON.parse(localStorage.getItem(key)||'');return x??fallback}catch(e){return fallback}}
function normalizeUrl(url){return String(url||'').trim().replace(/\/+$/,'')}
function validUrl(url){return /^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(normalizeUrl(url))}
function readConfig(){
  const file=window.JP_TRANSLATOR_CLOUD_CONFIG||{};
  if(file.url&&file.anonKey)return{url:normalizeUrl(file.url),anonKey:String(file.anonKey).trim(),source:'site'};
  const saved=readJSON(CONFIG_KEY,{});
  return{url:normalizeUrl(saved.url),anonKey:String(saved.anonKey||'').trim(),source:'browser'};
}
function populateConfig(){
  const c=readConfig();
  ui.url.value=c.url||'';
  ui.key.value=c.anonKey||'';
  ui.email.value=localStorage.getItem(EMAIL_KEY)||'';
  ui.configHint.textContent=c.source==='site'&&c.url?'網站已預設雲端連線；每部裝置只需要登入。':'首次設定需要 Supabase Project URL + Publishable/anon key。設定完成後可把公開 config 寫入網站，其他裝置就只需登入。';
}
function localHistory(){const x=readJSON(HISTORY_KEY,[]);return Array.isArray(x)?x.slice(0,HISTORY_LIMIT):[]}
function localAutoSave(){return localStorage.getItem(AUTO_SAVE_KEY)!=='false'}
function timeValue(v){const n=Date.parse(v||'');return Number.isFinite(n)?n:0}
function nowISO(){return new Date().toISOString()}
function markLocalChanged(){localStorage.setItem(STATE_UPDATED_KEY,nowISO())}
function setRemoteMarker(v){if(v)localStorage.setItem(REMOTE_UPDATED_KEY,v);else localStorage.removeItem(REMOTE_UPDATED_KEY)}
function sanitizeHistory(items){
  const out=[];
  for(const raw of Array.isArray(items)?items:[]){
    if(!raw||!String(raw.sourceText||'').trim())continue;
    out.push({
      id:String(raw.id||(`${Date.now()}-${Math.random().toString(36).slice(2,8)}`)),
      sourceText:String(raw.sourceText||''),
      zhText:String(raw.zhText||''),
      enText:String(raw.enText||''),
      sourceLanguage:String(raw.sourceLanguage||'ja'),
      targetLanguages:Array.isArray(raw.targetLanguages)?raw.targetLanguages:['zh-TW','en'],
      inputType:raw.inputType==='voice'?'voice':'text',
      createdAt:String(raw.createdAt||nowISO()),
      favorite:Boolean(raw.favorite)
    });
  }
  return out.sort((a,b)=>timeValue(b.createdAt)-timeValue(a.createdAt)).slice(0,HISTORY_LIMIT);
}
function mergeFirstSync(localItems,remoteItems){
  const map=new Map();
  for(const item of [...sanitizeHistory(remoteItems),...sanitizeHistory(localItems)]){
    const key=item.sourceText.trim();
    const prev=map.get(key);
    if(!prev){map.set(key,item);continue}
    const newer=timeValue(item.createdAt)>=timeValue(prev.createdAt)?item:prev;
    map.set(key,{...newer,favorite:Boolean(item.favorite||prev.favorite)});
  }
  return [...map.values()].sort((a,b)=>timeValue(b.createdAt)-timeValue(a.createdAt)).slice(0,HISTORY_LIMIT);
}
function applyRemote(history,autoSave,updatedAt){
  localStorage.setItem(HISTORY_KEY,JSON.stringify(sanitizeHistory(history)));
  localStorage.setItem(AUTO_SAVE_KEY,autoSave===false?'false':'true');
  if(updatedAt){localStorage.setItem(STATE_UPDATED_KEY,updatedAt);setRemoteMarker(updatedAt)}
  window.dispatchEvent(new CustomEvent('jpTranslatorCloudApplied'));
}
function setButtons(){
  const configured=Boolean(client),signedIn=Boolean(user);
  ui.login.disabled=!configured||signedIn;
  ui.sync.disabled=!configured||!signedIn||syncing;
  ui.logout.disabled=!configured||!signedIn;
  ui.saveConfig.disabled=false;
}
async function configureClient(showResult=false){
  const cfg=readConfig();
  if(authSubscription){try{authSubscription.unsubscribe()}catch(e){}authSubscription=null}
  client=null;user=null;
  if(!cfg.url||!cfg.anonKey){setStatus('本機模式','idle');setButtons();return false}
  if(!validUrl(cfg.url)){setStatus('Supabase URL 格式不正確','bad');setButtons();return false}
  if(!window.supabase?.createClient){setStatus('雲端同步程式未能載入','bad');setButtons();return false}
  try{
    client=window.supabase.createClient(cfg.url,cfg.anonKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,flowType:'pkce',storageKey:'jp-translator-cloud-auth'}});
    const authResult=await client.auth.getSession();
    if(authResult.error)throw authResult.error;
    user=authResult.data.session?.user||null;
    const sub=client.auth.onAuthStateChange((event,session)=>{
      user=session?.user||null;
      updateAuthUI();
      if(user&&(event==='SIGNED_IN'||event==='TOKEN_REFRESHED'||event==='INITIAL_SESSION'))setTimeout(()=>syncNow({silent:true}),0);
    });
    authSubscription=sub.data.subscription;
    updateAuthUI();
    if(user)await syncNow({silent:!showResult});
    else if(showResult)setStatus('雲端連線已設定，請用 Email 登入','ok');
    return true;
  }catch(e){
    console.warn('cloud configure failed',e);
    client=null;user=null;
    setStatus('雲端連線失敗：'+friendlyError(e),'bad');
    setButtons();
    return false;
  }
}
function updateAuthUI(){
  if(!client)setStatus('本機模式','idle');
  else if(user)setStatus('☁️ 已登入 '+(user.email||''),'ok');
  else setStatus('☁️ 已設定・未登入','idle');
  setButtons();
}
function friendlyError(e){
  const m=String(e?.message||e||'未知錯誤');
  if(/Failed to fetch|NetworkError/i.test(m))return '網絡或 Project URL 無法連線';
  if(/Invalid API key|apikey/i.test(m))return 'Publishable/anon key 無效';
  if(/relation .*translation_sync_state.*does not exist/i.test(m))return '尚未建立 translation_sync_state 資料表';
  return m.length>120?m.slice(0,120)+'…':m;
}
async function pushState(history=localHistory(),autoSave=localAutoSave()){
  if(!client||!user)return false;
  const updatedAt=nowISO();
  const row={user_id:user.id,history:sanitizeHistory(history),auto_save:Boolean(autoSave),updated_at:updatedAt};
  const {error}=await client.from(TABLE).upsert(row,{onConflict:'user_id'});
  if(error)throw error;
  localStorage.setItem(STATE_UPDATED_KEY,updatedAt);
  setRemoteMarker(updatedAt);
  return true;
}
async function syncNow({silent=false}={}){
  if(!client||!user||syncing)return false;
  if(!navigator.onLine){if(!silent)setStatus('離線：已保留本機紀錄，恢復網絡後再同步','idle');return false}
  syncing=true;setButtons();
  if(!silent)setStatus('☁️ 正在同步…','loading');
  try{
    const {data,error}=await client.from(TABLE).select('history,auto_save,updated_at').eq('user_id',user.id).maybeSingle();
    if(error)throw error;
    const local=localHistory(),localAuto=localAutoSave();
    const localUpdated=localStorage.getItem(STATE_UPDATED_KEY)||'';
    const lastRemote=localStorage.getItem(REMOTE_UPDATED_KEY)||'';
    if(!data){
      await pushState(local,localAuto);
    }else if(!lastRemote){
      const merged=mergeFirstSync(local,data.history||[]);
      const auto=data.auto_save!==false;
      applyRemote(merged,auto,data.updated_at);
      await pushState(merged,auto);
    }else{
      const remoteUpdated=timeValue(data.updated_at),lastRemoteUpdated=timeValue(lastRemote),localChanged=timeValue(localUpdated)>lastRemoteUpdated+250,remoteChanged=remoteUpdated>lastRemoteUpdated+250;
      if(remoteChanged&&!localChanged){
        applyRemote(data.history||[],data.auto_save!==false,data.updated_at);
      }else if(localChanged&&!remoteChanged){
        await pushState(local,localAuto);
      }else if(remoteChanged&&localChanged){
        if(remoteUpdated>timeValue(localUpdated))applyRemote(data.history||[],data.auto_save!==false,data.updated_at);
        else await pushState(local,localAuto);
      }
    }
    if(!silent)setStatus('✅ 雲端同步完成','ok');else updateAuthUI();
    return true;
  }catch(e){
    console.warn('cloud sync failed',e);
    setStatus('同步失敗：'+friendlyError(e),'bad');
    return false;
  }finally{syncing=false;setButtons()}
}
function schedulePush(){
  markLocalChanged();
  if(!client||!user)return;
  clearTimeout(syncTimer);
  syncTimer=setTimeout(async()=>{
    try{await pushState();setStatus('☁️ 已自動同步','ok')}catch(e){console.warn('cloud auto push failed',e);setStatus('雲端自動同步失敗：'+friendlyError(e),'bad')}
  },700);
}
async function saveConfig(){
  const url=normalizeUrl(ui.url.value),anonKey=ui.key.value.trim();
  if(!url&&!anonKey){localStorage.removeItem(CONFIG_KEY);setRemoteMarker('');await configureClient(true);return}
  if(!validUrl(url)){setStatus('請輸入正確 Supabase Project URL','bad');return}
  if(anonKey.length<20){setStatus('請輸入 Supabase Publishable/anon key','bad');return}
  localStorage.setItem(CONFIG_KEY,JSON.stringify({url,anonKey}));
  setRemoteMarker('');
  await configureClient(true);
}
async function sendMagicLink(){
  if(!client)return setStatus('請先設定雲端連線','bad');
  const email=ui.email.value.trim();
  if(!/^\S+@\S+\.\S+$/.test(email))return setStatus('請輸入有效 Email','bad');
  localStorage.setItem(EMAIL_KEY,email);
  const redirectTo=location.origin+location.pathname;
  setStatus('正在發送登入連結…','loading');
  const {error}=await client.auth.signInWithOtp({email,options:{emailRedirectTo:redirectTo,shouldCreateUser:true}});
  if(error)return setStatus('登入連結發送失敗：'+friendlyError(error),'bad');
  setStatus('✅ 已發送登入連結到 '+email+'；在這部裝置開啟該連結即可登入。','ok');
}
async function logout(){
  if(!client)return;
  const {error}=await client.auth.signOut();
  if(error)return setStatus('登出失敗：'+friendlyError(error),'bad');
  user=null;setRemoteMarker('');updateAuthUI();
}

ui.saveConfig.addEventListener('click',saveConfig);
ui.login.addEventListener('click',sendMagicLink);
ui.sync.addEventListener('click',()=>syncNow({silent:false}));
ui.logout.addEventListener('click',logout);
window.addEventListener('jpTranslatorHistoryChanged',schedulePush);
window.addEventListener('jpTranslatorSettingsChanged',schedulePush);
window.addEventListener('online',()=>{if(user)syncNow({silent:true})});
window.addEventListener('focus',()=>{if(user)syncNow({silent:true})});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&user)syncNow({silent:true})});

populateConfig();
configureClient(false);
})();
