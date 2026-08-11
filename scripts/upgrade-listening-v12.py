from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

if '日本語聽解挑戰 v1.2' in s:
    print('already upgraded')
    raise SystemExit(0)

s=s.replace('<title>日本語聽解挑戰 v1.1｜JLPT N1–N5</title>','<title>日本語聽解挑戰 v1.2｜JLPT N1–N5</title>',1)

# Load the real Supertonic browser module; it does not download the model until init() is called.
needle='<script src="./vendor/kuromoji.js"></script>'
if needle not in s: raise SystemExit('kuromoji script marker not found')
s=s.replace(needle,needle+'\n<script type="module" src="./vendor/supertonic-browser.js"></script>',1)

# Replace misleading simulated style UI with two real engines.
start=s.index('<div class="source"><strong>🔊 日語語音</strong>')
end=s.index('<div class="source"><strong>🎯 相似答案規則</strong>',start)
voice_html='''<div class="source"><strong>🔊 日語語音</strong>
<div class="muted" style="margin:5px 0 8px">AI 語音是真正不同的 AI 聲線；裝置語音只作備援。</div>
<div class="radios two" style="margin-bottom:9px"><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai" checked><label for="engineAI">✨ AI 日語語音</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置語音</label></div></div>
<div id="aiPanel">
<div id="aiStatus" class="notice" style="margin:0 0 8px">尚未下載 AI 模型。首次啟用約需下載 400 MB；之後瀏覽器通常可使用快取。</div>
<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Supertonic 3 AI 聲線</label><select id="aiVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="F1">👩 F1</option><option value="F2">👩 F2</option><option value="F3">👩 F3</option><option value="F4">👩 F4</option><option value="F5">👩 F5</option><option value="M1">👨 M1</option><option value="M2">👨 M2</option><option value="M3">👨 M3</option><option value="M4">👨 M4</option><option value="M5">👨 M5</option><option value="random">🎲 每題隨機</option></select></div>
<button id="enableAI" class="btn primary" style="width:100%;margin-top:8px">下載／啟用 AI 語音</button>
<div class="muted" style="margin-top:7px">模型：Supertonic 3（日語）。模型在你的瀏覽器內運算，不會把題目送到語音 API。</div>
</div>
<div id="devicePanel" style="display:none;margin-top:8px"><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div><div class="field" style="margin-top:8px"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">裝置日語語音（備援）</label><select id="voice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">自動選擇日語語音</option></select></div></div>
</div>
'''
s=s[:start]+voice_html+s[end:]

old_decl='let items=[],wrong=new Set(load("jplistening_wrong",[])),game=null,voices=[],tokenizer=null,renderToken=0;\nconst zhCache=new Map(Object.entries(load("jplistening_zh",{})));'
new_decl='let items=[],wrong=new Set(load("jplistening_wrong",[])),game=null,voices=[],tokenizer=null,renderToken=0,activeAiAudio=null,aiInitPromise=null;\nconst zhCache=new Map(Object.entries(load("jplistening_zh",{})));\nconst jaZhCache=new Map(Object.entries(load("jplistening_jazh",{})));'
if old_decl not in s: raise SystemExit('state declaration not found')
s=s.replace(old_decl,new_decl,1)

# Replace fake pitch/rate styles with a genuine AI engine and plain device fallback.
js_start=s.index('const VOICE_STYLES=')
js_end=s.index('function start(){',js_start)
real_audio_js=r'''function chosenDeviceVoice(){const n=$("#voice")?.value;if(n)return voices.find(v=>v.name===n)||null;const jp=voices.filter(v=>/^ja/i.test(v.lang));return jp.find(v=>/^ja-JP$/i.test(v.lang))||jp[0]||null}
function syncAudioPanels(){const ai=$("input[name=audioEngine]:checked")?.value!=="device";$("#aiPanel").style.display=ai?"block":"none";$("#devicePanel").style.display=ai?"none":"block"}
async function waitForAiModule(){if(window.SupertonicAI)return window.SupertonicAI;await new Promise((resolve,reject)=>{let done=false;const ok=()=>{if(done)return;done=true;resolve()};window.addEventListener("supertonic-ai-module-ready",ok,{once:true});setTimeout(()=>{if(done)return;done=true;reject(new Error("AI 模組載入逾時"))},12000)});if(!window.SupertonicAI)throw new Error("AI 模組未載入");return window.SupertonicAI}
async function enableAI(){const b=$("#enableAI");if(aiInitPromise)return aiInitPromise;b.disabled=true;aiInitPromise=(async()=>{try{const api=await waitForAiModule();$("#aiStatus").textContent="正在檢查 Supertonic 3 模型…";await api.preflight();await api.init(msg=>{$("#aiStatus").textContent=msg});$("#aiStatus").textContent="✅ Supertonic 3 AI 語音已準備，可選 F1–F5／M1–M5。";$("#engineAI").checked=true;syncAudioPanels();return true}catch(e){$("#aiStatus").textContent="⚠️ AI 語音無法啟用："+(e?.message||String(e))+"。已保留裝置語音備援。";$("#engineDevice").checked=true;syncAudioPanels();return false}finally{b.disabled=false;b.textContent=window.SupertonicAI?.isReady?.()?"✅ AI 語音已啟用":"重新嘗試啟用 AI 語音";aiInitPromise=null}})();return aiInitPromise}
function stopAllAudio(){try{speechSynthesis.cancel()}catch{}if(activeAiAudio){try{activeAiAudio.pause();activeAiAudio.src=""}catch{}activeAiAudio=null}}
function unlockAfterPlay(label){game.plays++;$("#playCount").textContent=`已播放 ${game.plays} 次 · ${label}`;if(game.locked){game.locked=false;$$(".choice").forEach(b=>{b.disabled=false;b.classList.remove("locked")})}}
function speakDevice(rate=1,fallback=false){try{speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(game.current.jp);u.lang="ja-JP";u.rate=rate;u.pitch=1;u.volume=1;const v=chosenDeviceVoice();if(v)u.voice=v;speechSynthesis.speak(u);unlockAfterPlay((fallback?"AI 備援 · ":"")+(v?.name||"裝置日語語音"));return true}catch{return false}}
function selectedAiVoice(){const requested=$("#aiVoice")?.value||"F1";if(requested!=="random")return requested;if(game?.aiVoiceForQuestion)return game.aiVoiceForQuestion;const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];return a[Math.floor(Math.random()*a.length)]}
async function speak(rate=1){if(!game?.current)return;stopAllAudio();const useAI=$("input[name=audioEngine]:checked")?.value!=="device";if(useAI){const api=window.SupertonicAI;if(api?.isReady?.()){try{$("#playCount").textContent="AI 正在產生語音…";const vid=selectedAiVoice();const out=await api.synthesize(game.current.jp,{voice:vid,speed:rate,totalSteps:5});activeAiAudio=new Audio(out.url);await activeAiAudio.play();unlockAfterPlay(`AI ${vid}`);return}catch(e){$("#aiStatus").textContent="⚠️ AI 本次發音失敗，已改用裝置語音："+(e?.message||String(e))}}else{$("#aiStatus").textContent="AI 尚未啟用。按「下載／啟用 AI 語音」後可使用真正 AI 聲線；本次先用裝置語音。"}}speakDevice(rate,true)}
'''
s=s[:js_start]+real_audio_js+s[js_end:]

# Add Japanese -> Traditional Chinese translation cache for hidden distractor sentences.
insert_at=s.index('async function fillZh(q,rt)')
translate_ja=r'''function validTraditionalChoice(src,z){z=String(z||"").trim();return !!z&&z!==String(src||"").trim()&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(z)}
function normChoice(z){return String(z||"").replace(/[\s，。！？、,.!?「」『』（）()]/g,"").trim()}
async function translateJaZh(jp){jp=String(jp||"").trim();if(!jp)return"";if(jaZhCache.has(jp)){const z=jaZhCache.get(jp);if(validTraditionalChoice(jp,z))return z;jaZhCache.delete(jp)}try{const u="https://api.mymemory.translated.net/get?q="+encodeURIComponent(jp.slice(0,450))+"&langpair=ja%7Czh-TW";const r=await fetch(u);if(!r.ok)throw Error();const d=await r.json();const z=String(d?.responseData?.translatedText||"").trim();if(!validTraditionalChoice(jp,z))throw Error();jaZhCache.set(jp,z);save("jplistening_jazh",Object.fromEntries([...jaZhCache.entries()].slice(-800)));return z}catch{return""}}
async function prepareChineseChoices(q,m){const rows=await Promise.all(m.choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==rows.length)return null;return rows}
'''
s=s[:insert_at]+translate_ja+s[insert_at:]

# Prepare four Chinese meanings before rendering; Japanese remains internal until result reveal.
next_start=s.index('function next(){')
next_end=s.index('function answer(v){',next_start)
new_next=r'''async function next(){hideSheet();if(!game)return;if(!game.infinite&&game.index>=game.limit){finish();return}$("#choices").innerHTML='<div class="muted" style="grid-column:1/-1;text-align:center;padding:24px">正在準備 4 個繁體中文相似選項…</div>';let tries=0,q,m,prepared=null;const maxTry=Math.min(35,Math.max(1,game.order.length));while(tries<maxTry&&!prepared){if(game.index>=game.order.length)game.order=shuffle(game.pool);q=game.order[(game.index+tries)%game.order.length];m=makeChoices(q);if(m)prepared=await prepareChineseChoices(q,m);tries++}if(!m||!prepared){alert("目前無法產生 4 個可靠而不重複的繁體中文選項。請按重新載入 Web 後再試。");quit();return}game.current=q;game.quality=m.quality;game.currentZh=prepared.find(x=>x.jp===q.jp)?.zh||"";game.plays=0;game.aiVoiceForQuestion=null;if($("#aiVoice")?.value==="random"){const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];game.aiVoiceForQuestion=a[Math.floor(Math.random()*a.length)]}game.locked=$("input[name=reveal]:checked").value==="hide";$("#playCount").textContent=game.locked?"請先播放音訊":"可直接選擇，亦可播放音訊";$("#choices").innerHTML=prepared.map((x,i)=>`<button class="choice${game.locked?" locked":""}" ${game.locked?"disabled":""} data-v="${encodeURIComponent(x.jp)}"><strong>${String.fromCharCode(65+i)}.</strong> ${esc(x.zh)}</button>`).join("");$$(".choice").forEach(b=>b.onclick=()=>answer(decodeURIComponent(b.dataset.v)));stats()}
'''
s=s[:next_start]+new_next+s[next_end:]

old_answer='$("#aZh").textContent="正在載入繁體中文意思…";fillZh(q,rt);'
new_answer='if(game.currentZh){$("#aZh").textContent=game.currentZh}else{$("#aZh").textContent="正在載入繁體中文意思…";fillZh(q,rt)};'
if old_answer not in s: raise SystemExit('answer translation marker not found')
s=s.replace(old_answer,new_answer,1)

s=s.replace('function finish(){speechSynthesis.cancel();hideSheet();','function finish(){stopAllAudio();hideSheet();',1)
s=s.replace('function quit(){speechSynthesis.cancel();hideSheet();','function quit(){stopAllAudio();hideSheet();',1)

old_handlers='$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;'
new_handlers='$("#reload").onclick=loadWeb;$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#playNormal").onclick=()=>speak(1);$("#playSlow").onclick=()=>speak(.75);$("#replay").onclick=()=>speak(1);$("#next").onclick=next;$("#enableAI").onclick=enableAI;$$('+'"input[name=audioEngine]"'+').forEach(x=>x.onchange=syncAudioPanels);syncAudioPanels();'
if old_handlers not in s: raise SystemExit('handler marker not found')
s=s.replace(old_handlers,new_handlers,1)

# Footer transparency and visible revision marker.
s=s.replace('Web 句子來源：Hanabira / tristcoil hanabira.org-japanese-content。聽解音訊由裝置／瀏覽器的 Japanese Speech Synthesis 即時產生，不需要付費語音 API。JLPT 等級屬學習用分類。','Web 句子來源：Hanabira。AI 語音：Supertonic 3（瀏覽器內 ONNX 運算；首次啟用需下載大型模型）；裝置日語語音只作備援。A/B/C/D 僅顯示繁體中文意思，回答後才顯示日文原句。JLPT 等級屬學習用分類。',1)

p.write_text(s,encoding='utf-8')
print('upgraded listening.html to v1.2')
