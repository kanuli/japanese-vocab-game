from pathlib import Path

p=Path('src/listening-onedrive-entry.js')
s=p.read_text(encoding='utf-8')

if "const ACCOUNT_HINT_KEY='jplistening_onedrive_login_hint';" in s:
    print('MSAL cache recovery already patched')
    raise SystemExit(0)

def repl(old,new,label):
    global s
    if old not in s:
        raise SystemExit(f'patch anchor not found: {label}')
    s=s.replace(old,new,1)

repl(
"const CLIENT_ID_KEY='jplistening_onedrive_client_id';\nconst GRAPH='https://graph.microsoft.com/v1.0';",
"const CLIENT_ID_KEY='jplistening_onedrive_client_id';\nconst ACCOUNT_HINT_KEY='jplistening_onedrive_login_hint';\nconst GRAPH='https://graph.microsoft.com/v1.0';",
'account hint key')

anchor="""function isConfigured(){return !!baseConfig().clientId}
function savedClientId(){return baseConfig().clientId}
function setClientId(id){"""
insert="""function isConfigured(){return !!baseConfig().clientId}
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
function setClientId(id){"""
repl(anchor,insert,'helpers')

old_getapp="""  appClientId=c.clientId;
  await app.initialize();
  const redirect=await app.handleRedirectPromise();
  account=redirect?.account||app.getActiveAccount()||app.getAllAccounts()[0]||null;
  if(account)app.setActiveAccount(account);
  return app;
}

async function init(){
  if(!isConfigured())return {configured:false,signedIn:false,account:null};
  if(initPromise)return initPromise;
  initPromise=(async()=>{
    const a=await getApp();
    account=a.getActiveAccount()||a.getAllAccounts()[0]||account||null;
    if(account)a.setActiveAccount(account);
    return {configured:true,signedIn:!!account,account:account?.username||account?.name||''};
  })().catch(e=>{initPromise=null;throw e});
  return initPromise;
}"""
new_getapp="""  appClientId=c.clientId;
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
}"""
repl(old_getapp,new_getapp,'getApp/init recovery')

old_signin="""    const r=await a.loginPopup({scopes:c.scopes,prompt:'select_account'});
    account=r.account;
    if(account)a.setActiveAccount(account);
    return {signedIn:true,account:account?.username||account?.name||''};"""
new_signin="""    const r=await a.loginPopup({scopes:c.scopes,prompt:'select_account'});
    rememberAccount(r.account);
    initPromise=null;
    return {signedIn:true,account:account?.username||account?.name||''};"""
repl(old_signin,new_signin,'signIn remember account')

old_signout="""  if(acct)await a.logoutPopup({account:acct,postLogoutRedirectUri:baseConfig().redirectUri});
  account=null;indexCache=null;urlCache.clear();
}"""
new_signout="""  if(acct)await a.logoutPopup({account:acct,postLogoutRedirectUri:baseConfig().redirectUri});
  account=null;initPromise=null;indexCache=null;urlCache.clear();
  try{localStorage.removeItem(ACCOUNT_HINT_KEY)}catch{}
}"""
repl(old_signout,new_signout,'signOut cleanup')

old_token="""async function token(){
  const a=await getApp();
  const c=baseConfig();
  const acct=a.getActiveAccount()||a.getAllAccounts()[0]||account;
  if(!acct)throw new Error('請先連接 OneDrive');
  try{
    const r=await a.acquireTokenSilent({account:acct,scopes:c.scopes});
    return r.accessToken;
  }catch(e){
    if(e instanceof InteractionRequiredAuthError||String(e?.errorCode||'').includes('interaction')){
      const r=await a.acquireTokenPopup({account:acct,scopes:c.scopes});
      return r.accessToken;
    }
    throw e;
  }
}"""
new_token="""async function token(){
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
}"""
repl(old_token,new_token,'silent token recovery')

old_connection="""async function connectionInfo(){
  const s=await init();
  if(!s.configured)return s;
  if(!s.signedIn)return s;
  const root=await ensureAppRoot();
  let count=0;
  try{const i=await loadIndex();count=Object.keys(i?.items||{}).length}catch{}
  return {...s,appFolder:root?.name||'',indexed:count};
}"""
new_connection="""async function connectionInfo(){
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
}"""
repl(old_connection,new_connection,'connectionInfo recovery')

# Keep future Client-ID changes from reusing an unrelated login hint.
repl(
"  if(id)localStorage.setItem(CLIENT_ID_KEY,id);else localStorage.removeItem(CLIENT_ID_KEY);\n  app=null;appClientId='';account=null;initPromise=null;indexCache=null;urlCache.clear();",
"  const previous=baseConfig().clientId;\n  if(id)localStorage.setItem(CLIENT_ID_KEY,id);else localStorage.removeItem(CLIENT_ID_KEY);\n  if(previous&&previous!==id){try{localStorage.removeItem(ACCOUNT_HINT_KEY)}catch{}}\n  app=null;appClientId='';account=null;initPromise=null;indexCache=null;urlCache.clear();",
'client ID reset')

p.write_text(s,encoding='utf-8')
print('Patched OneDrive MSAL cache recovery')
