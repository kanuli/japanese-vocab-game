from pathlib import Path


def replace_once(path, old, new, label):
    p=Path(path); s=p.read_text(encoding='utf-8')
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{path}: {label} expected 1 match, got {n}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

# Inject one shared policy guard into every root HTML page.
for p in Path('.').glob('*.html'):
    s=p.read_text(encoding='utf-8')
    if 'mobile-supertonic-guard.js' in s:
        continue
    marker='<script defer src="./site-health.js?v=20260817v1"></script>'
    guard='<script src="./mobile-supertonic-guard.js?v=20260817v1"></script>'
    if marker in s:
        s=s.replace(marker,guard+'\n'+marker,1)
    elif '</head>' in s:
        s=s.replace('</head>',guard+'\n</head>',1)
    else:
        raise SystemExit(f'{p}: cannot inject mobile guard')
    p.write_text(s,encoding='utf-8')

# Cache bust word audio clients already changed on main.
for path in ['wordaudio.html','wordlist.html']:
    p=Path(path); s=p.read_text(encoding='utf-8')
    s=s.replace('wordaudio-multivoice.js?v=20260815v2','wordaudio-multivoice.js?v=20260817v3')
    if path=='wordlist.html': s=s.replace('wordlist-audio.js?v=5','wordlist-audio.js?v=6')
    p.write_text(s,encoding='utf-8')

# Conversation: hosted Supertonic stays available on mobile; local WASM fallback is blocked.
replace_once('conversation.js',
"const sleep=ms=>new Promise(r=>setTimeout(r,ms));",
"const sleep=ms=>new Promise(r=>setTimeout(r,ms));\nconst localSuperAllowed=()=>window.MobileSupertonicGuard?.localAllowed!==false;",
'conversation guard helper')
replace_once('conversation.js',
"async function ensureSuper(){\n try{",
"async function ensureSuper(){\n if(!localSuperAllowed()){vst('📱 手機安全模式：不載入本機 Supertonic；使用伺服器預錄／VOICEVOX 備援。','loading');return false}\n try{",
'conversation ensureSuper')
old=""" if(eng==='supertonic'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;if(used)return;
  vst('Supertonic 3 此句暫無本站預錄音，改用瀏覽器即時生成。','loading');
  return speakSuper(text,role,token);
 }
 if(eng==='voicevox'||eng==='aivis'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;
  if(used)return;
  vst(`${eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS'} 此句沒有本站預錄音，已自動使用 Supertonic 3 備援。`,'loading');
  return speakSuper(text,role,token,role==='B'?'M3':'F3');
 }
"""
new=""" if(eng==='supertonic'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;if(used)return;
  if(!localSuperAllowed()){
   vst('📱 Supertonic 伺服器錄音暫不可用；手機改用 VOICEVOX 伺服器備援。','loading');
   try{used=await window.ConversationHostedAudio?.speakEngine?.('voicevox',text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
   if(token!==S.stopToken)return;if(used)return;
   vst('📱 VOICEVOX 亦暫不可用，改用裝置 Japanese voice。','loading');
   return speakDevice(text,role,token);
  }
  vst('Supertonic 3 此句暫無本站預錄音，改用瀏覽器即時生成。','loading');
  return speakSuper(text,role,token);
 }
 if(eng==='voicevox'||eng==='aivis'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;
  if(used)return;
  if(!localSuperAllowed()){
   if(eng!=='voicevox')try{used=await window.ConversationHostedAudio?.speakEngine?.('voicevox',text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
   if(token!==S.stopToken)return;if(used)return;
   vst('📱 手機不啟動本機 Supertonic；改用裝置 Japanese voice。','loading');
   return speakDevice(text,role,token);
  }
  vst(`${eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS'} 此句沒有本站預錄音，已自動使用 Supertonic 3 備援。`,'loading');
  return speakSuper(text,role,token,role==='B'?'M3':'F3');
 }
"""
replace_once('conversation.js',old,new,'conversation mobile fallback')

replace_once('conversation-hosted-audio.js',
"async function speak(text,role,rate){if(H.engine==='supertonic')return speakSupertonic(text,role,rate);if(H.engine==='voicevox')return speakVoicevox(text,role,rate);if(H.engine==='aivis')return speakAivis(text,role,rate);return false}\nwindow.ConversationHostedAudio={configure,speak,stop};",
"async function speakEngine(engine,text,role,rate){if(engine==='supertonic')return speakSupertonic(text,role,rate);if(engine==='voicevox')return speakVoicevox(text,role,rate);if(engine==='aivis')return speakAivis(text,role,rate);return false}\nasync function speak(text,role,rate){return speakEngine(H.engine,text,role,rate)}\nwindow.ConversationHostedAudio={configure,speak,speakEngine,stop};",
'conversation hosted explicit engine')

# Listening: allow hosted Supertonic, never initialize local model on mobile.
replace_once('listening.html',
"const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];",
"const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];\nconst localSuperAllowed=()=>window.MobileSupertonicGuard?.localAllowed!==false;",
'listening guard helper')
replace_once('listening.html',
"async function updateAiCacheStatus(){const info=await supertonicCacheInfo(),b=$(\"#enableAI\");",
"async function updateAiCacheStatus(){if(!localSuperAllowed()){const b=$(\"#enableAI\");$(\"#aiStatus\").textContent=\"📱 手機安全模式：Supertonic 只使用伺服器預錄，不載入本機 400 MB WASM 模型。\";b.textContent=\"📱 手機使用伺服器 Supertonic\";b.disabled=true;return{ready:false,modelCount:0,mobile:true}}const info=await supertonicCacheInfo(),b=$(\"#enableAI\");",
'listening cache status')
replace_once('listening.html',
"async function enableAI(selectEngine=true){const b=$(\"#enableAI\");if(aiInitPromise)return aiInitPromise;",
"async function enableAI(selectEngine=true){const b=$(\"#enableAI\");if(!localSuperAllowed()){$(\"#aiStatus\").textContent=\"📱 此手機不啟動本機 Supertonic；請使用伺服器 Supertonic／VOICEVOX。\";b.disabled=true;return false}if(aiInitPromise)return aiInitPromise;",
'listening enableAI')
replace_once('listening.html',
"async function initializeSupertonicPersistence(){await ensureSupertonicCache();const info=await updateAiCacheStatus();",
"async function initializeSupertonicPersistence(){if(!localSuperAllowed())return updateAiCacheStatus();await ensureSupertonicCache();const info=await updateAiCacheStatus();",
'listening persistence')
replace_once('listening.html',
"if(mode===\"ai\"||mode===\"aivis\"){if(!window.SupertonicAI?.isReady?.()){const ok=await enableAI(false);if(!ok)throw new Error(\"Supertonic 尚未準備完成\")}const vid=$(\"#aiVoice\")?.value===\"random\"?\"F1\":selectedAiVoice();",
"if(mode===\"ai\"||mode===\"aivis\"){if(!localSuperAllowed()){status.textContent=\"📱 此句沒有伺服器預錄；手機改用裝置 Japanese voice。\";const u=new SpeechSynthesisUtterance(sample);u.lang=\"ja-JP\";u.rate=1;const dv=chosenDeviceVoice();if(dv)u.voice=dv;speechSynthesis.speak(u);return}if(!window.SupertonicAI?.isReady?.()){const ok=await enableAI(false);if(!ok)throw new Error(\"Supertonic 尚未準備完成\")}const vid=$(\"#aiVoice\")?.value===\"random\"?\"F1\":selectedAiVoice();",
'listening sample fallback')
replace_once('listening.html',
"if(ai?.isReady?.()){try{$(\"#playCount\").textContent=\"VOICEVOX 不可用，AI 正在產生備援語音…\";",
"if(localSuperAllowed()&&ai?.isReady?.()){try{$(\"#playCount\").textContent=\"VOICEVOX 不可用，AI 正在產生備援語音…\";",
'listening voicevox fallback guard')
replace_once('listening.html',
"if(mode===\"ai\"||mode===\"aivis\"){const api=window.SupertonicAI;",
"if(mode===\"ai\"||mode===\"aivis\"){if(!localSuperAllowed()){$(\"#aiStatus\").textContent=\"📱 此題沒有可用伺服器錄音；手機已改用裝置 Japanese voice。\";speakDevice(rate,\"Mobile safe fallback\");return}const api=window.SupertonicAI;",
'listening main fallback guard')

# Translator: arbitrary new text cannot be pre-generated; mobile falls to device Japanese voice rather than local WASM.
replace_once('translator.html',
"(()=>{'use strict';const $=s=>document.querySelector(s),jp=$('#jp'),zh=$('#zh'),en=$('#en'),status=$('#status');let voices=[],audio=null;const st3VoiceOptions=$('#voice').innerHTML;",
"(()=>{'use strict';const $=s=>document.querySelector(s),jp=$('#jp'),zh=$('#zh'),en=$('#en'),status=$('#status');let voices=[],audio=null;const st3VoiceOptions=$('#voice').innerHTML;const localSuperAllowed=()=>window.MobileSupertonicGuard?.localAllowed!==false;",
'translator guard helper')
replace_once('translator.html',
"async function ensureAI(){try{",
"async function ensureAI(){if(!localSuperAllowed()){st('📱 手機安全模式：不載入本機 Supertonic；任意新句會改用裝置 Japanese voice。','loading');return false}try{",
'translator ensureAI')
replace_once('translator.html',
"st((eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS')+' 沒有這個任意新句的本站預錄，改用 Supertonic 3 即時生成。','loading')}await speakSupertonic3(t,rate)}",
"st((eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS')+' 沒有這個任意新句的本站預錄。','loading')}if(!localSuperAllowed()){st('📱 手機不載入本機 Supertonic；此新句改用裝置 Japanese voice。','loading');speakDevice(t,'ja-JP',rate);return}await speakSupertonic3(t,rate)}",
'translator mobile fallback')
replace_once('translator.html',
"if('speechSynthesis'in window){loadvoices();speechSynthesis.onvoiceschanged=loadvoices}syncEngine();",
"if('speechSynthesis'in window){loadvoices();speechSynthesis.onvoiceschanged=loadvoices}if(!localSuperAllowed())$('#engine').value='voicevox';syncEngine();",
'translator mobile default')

# Pronunciation: hosted references remain; local install is disabled on mobile.
replace_once('pronunciation.html',
"(()=>{'use strict';const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];",
"(()=>{'use strict';const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];const localSuperAllowed=()=>window.MobileSupertonicGuard?.localAllowed!==false;",
'pronunciation guard helper')
replace_once('pronunciation.html',
"$('#enableLocal').onclick=async()=>{let b=$('#enableLocal');b.disabled=true;try{",
"if(!localSuperAllowed()){$('#enableLocal').disabled=true;$('#enableLocal').textContent='📱 手機使用伺服器參考音';$('#modelStatus').textContent='手機不載入本機 Supertonic；有伺服器參考音時照常使用，缺漏時改用裝置日語。'}$('#enableLocal').onclick=async()=>{let b=$('#enableLocal');if(!localSuperAllowed())return;b.disabled=true;try{",
'pronunciation local button')
replace_once('pronunciation.html',
"async function localReference(q){if(!localReady)return null;",
"async function localReference(q){if(!localSuperAllowed()||!localReady)return null;",
'pronunciation local reference')

# Update maintenance to require the shared guard on every page and test mobile policy.
p=Path('.github/workflows/site-maintenance.yml'); s=p.read_text(encoding='utf-8')
s=s.replace("if text.count('site-health.js')!=1: failures.append(f'{page}: site-health.js count={text.count(\"site-health.js\")}')",
            "if text.count('site-health.js')!=1: failures.append(f'{page}: site-health.js count={text.count(\"site-health.js\")}')\n              if text.count('mobile-supertonic-guard.js')!=1: failures.append(f'{page}: mobile guard count={text.count(\"mobile-supertonic-guard.js\")}')")
s=s.replace("required=['site-health.js','conversation.js'", "required=['site-health.js','mobile-supertonic-guard.js','conversation.js'")
s=s.replace("for f in site-health.js conversation.js", "for f in site-health.js mobile-supertonic-guard.js conversation.js")
needle="""      - name: Verify every live GitHub Pages page
        id: live
"""
mobile="""      - name: Mobile Supertonic safety smoke test
        id: mobile
        run: |
          cat >/tmp/mobile-safe.cjs <<'NODE'
          const {chromium}=require(process.cwd()+'/node_modules/playwright');
          (async()=>{const browser=await chromium.launch({headless:true});const context=await browser.newContext({userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1',viewport:{width:390,height:844},hasTouch:true,isMobile:true});const pages=['wordaudio.html','wordlist.html','listening.html','conversation.html','pronunciation.html','translator.html'];let fail=false;for(const p of pages){const page=await context.newPage();const errs=[];page.on('pageerror',e=>errs.push(String(e)));try{await page.goto('http://127.0.0.1:4173/'+p+'?mobileSafety='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});await page.waitForTimeout(2600);const s=await page.evaluate(()=>({guard:window.MobileSupertonicGuard||null,mode:document.documentElement.dataset.mobileSupertonic,audioEngine:document.querySelector('#audioEngine')?.value||'',translatorEngine:location.pathname.endsWith('/translator.html')?document.querySelector('#engine')?.value||'':'',enableLocal:document.querySelector('#enableLocal')?.disabled??null,enableAI:document.querySelector('#enableAI')?.disabled??null}));if(!s.guard||s.guard.localAllowed!==false||s.mode!=='hosted-only')throw Error('mobile guard inactive '+JSON.stringify(s));if((p==='wordaudio.html'||p==='wordlist.html')&&s.audioEngine!=='voicevox')throw Error('word page did not default to VOICEVOX '+JSON.stringify(s));if(p==='translator.html'&&s.translatorEngine!=='voicevox')throw Error('translator did not default to VOICEVOX '+JSON.stringify(s));if(p==='pronunciation.html'&&s.enableLocal!==true)throw Error('pronunciation local model button not disabled');if(p==='listening.html'&&s.enableAI!==true)throw Error('listening local model button not disabled');if(errs.length)throw Error(errs.join(' | '));console.log('MOBILE PASS',p,JSON.stringify(s));}catch(e){fail=true;console.error('MOBILE FAIL',p,e.message)}await page.close()}await browser.close();if(fail)process.exit(1)})();
          NODE
          node /tmp/mobile-safe.cjs

"""
if mobile.strip() not in s:
    if needle not in s: raise SystemExit('maintenance: live step marker not found')
    s=s.replace(needle,mobile+needle,1)
p.write_text(s,encoding='utf-8')
print('Mobile Supertonic safety patch prepared.')
