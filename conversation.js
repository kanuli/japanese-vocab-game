(()=>{'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const S={data:null,scene:null,item:null,mode:'learn',audio:null,blobUrl:'',stopToken:0,dictLine:0,superReady:false,systemVoices:[],apiVoices:[]};
const STVOICES=[['F1','🌙 沉穩低柔女聲（F1）'],['F2','🌸 明亮活潑女聲（F2）'],['F3','🎙️ 專業播音女聲（F3）'],['F4','✨ 清晰自信女聲（F4）'],['F5','💕 溫柔療癒女聲（F5）'],['M1','⚡ 活力自信男聲（M1）'],['M2','🌑 低沉穩重男聲（M2）'],['M3','🧭 權威專業男聲（M3）'],['M4','🙂 柔和親切男聲（M4）'],['M5','📖 溫暖舒緩男聲（M5）']];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function st(t,c=''){const e=$('#playStatus');e.textContent=t;e.className='status'+(c?' '+c:'')}
function vst(t,c=''){const e=$('#voiceStatus');e.textContent=t;e.className='status'+(c?' '+c:'')}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function levels(){const a=$$('.level input:checked').map(x=>x.value);return a.length?a:['N1','N2','N3','N4','N5']}
function sceneById(id){return S.data.scenes.find(x=>x.id===id)||S.data.scenes[0]}
function filteredItems(scene=S.scene){const l=levels();return scene.items.filter(x=>l.includes(x.level))}
function allFiltered(){const l=levels(),a=[];for(const sc of S.data.scenes)for(const it of sc.items)if(l.includes(it.level))a.push([sc,it]);return a}
function pick(a){return a[Math.floor(Math.random()*a.length)]}
function populateScenes(){
 const cur=$('#scene').value;
 $('#scene').innerHTML=S.data.scenes.map(s=>`<option value="${esc(s.id)}">${esc(s.icon)} ${esc(s.zh)}｜${esc(s.jp)}</option>`).join('');
 if(cur&&S.data.scenes.some(x=>x.id===cur))$('#scene').value=cur;
 S.scene=sceneById($('#scene').value||'station');
}
function populateSituations(prefer=null){
 const a=filteredItems(); const sel=$('#situation');
 if(!a.length){sel.innerHTML='<option>所選程度沒有內容</option>';S.item=null;render();return}
 sel.innerHTML=a.map((x,i)=>`<option value="${i}">${esc(x.level)}｜${esc(x.situation)}</option>`).join('');
 let idx=prefer!=null?a.indexOf(prefer):0;if(idx<0)idx=0;sel.value=String(idx);S.item=a[idx];render();
}
function setSelection(sc,it){
 S.scene=sc;$('#scene').value=sc.id;populateSituations(it);
 const a=filteredItems(sc),idx=a.indexOf(it);if(idx>=0){$('#situation').value=String(idx);S.item=it;render()}
}
function modeUI(){
 $$('.mode').forEach(b=>b.classList.toggle('active',b.dataset.mode===S.mode));
 const hide=S.mode==='listen'||S.mode==='dictation';
 $('#reveal').style.display=hide?'':'none';
 $('#dictation').style.display=S.mode==='dictation'?'block':'none';
 render();
}
function render(){
 if(!S.scene||!S.item)return;
 $('#sceneName').textContent=`${S.scene.icon} ${S.scene.zh}｜${S.scene.jp}`;
 $('#situationName').textContent=S.item.situation;
 $('#meta').innerHTML=`<span class="tag">${esc(S.item.level)}</span><span class="tag">${esc(S.mode==='learn'?'學習':S.mode==='listen'?'聽力':S.mode==='shadow'?'跟讀':'聽寫')}</span>`;
 const hide=(S.mode==='listen'||S.mode==='dictation')&&!$('#reveal').dataset.shown;
 $('#lines').innerHTML=S.item.lines.map((l,i)=>`<div class="line line-${l.role.toLowerCase()}"><div class="role">Speaker ${esc(l.role)}</div><div class="jp ${hide?'hidden-text':''}">${hide?'聽完後按「顯示日文」':esc(l.jp)}</div><div class="zh" style="${$('#showZh').checked?'':'display:none'}">${esc(l.zh)}</div><div class="line-actions"><button class="btn mini linePlay" data-i="${i}">🔊 只聽 ${esc(l.role)}</button></div></div>`).join('');
 $$('.linePlay').forEach(b=>b.onclick=()=>playLine(Number(b.dataset.i)));
 if(S.mode==='dictation')updateDictPrompt();
}
function resetReveal(){delete $('#reveal').dataset.shown;$('#reveal').textContent='👁 顯示日文'}
function randomDialog(){
 const a=allFiltered();if(!a.length)return;const [sc,it]=pick(a);resetReveal();setSelection(sc,it)
}
function moveDialog(d){
 const a=allFiltered();if(!a.length)return;let idx=a.findIndex(([sc,it])=>sc===S.scene&&it===S.item);if(idx<0)idx=0;idx=(idx+d+a.length)%a.length;resetReveal();setSelection(a[idx][0],a[idx][1])
}
function stop(){
 S.stopToken++;
 if(S.audio){try{S.audio.pause();S.audio.currentTime=0}catch(e){}S.audio=null}
 if(S.blobUrl){try{URL.revokeObjectURL(S.blobUrl)}catch(e){}S.blobUrl=''}
 if('speechSynthesis'in window) speechSynthesis.cancel();
 if(window.ConversationHostedAudio?.stop)window.ConversationHostedAudio.stop();
}
function selectedVoice(role){
 const s=role==='B'?$('#voiceB'):$('#voiceA'),v=s.value;
 if(v!=='random')return v;
 const opts=[...s.options].map(o=>o.value).filter(x=>x&&x!=='random');return opts.length?pick(opts):'';
}
function populateSupertonic(){
 const opts='<option value="random">🎲 每次隨機</option>'+STVOICES.map(([v,n])=>`<option value="${v}">${n}</option>`).join('');
 $('#voiceA').innerHTML=opts;$('#voiceB').innerHTML=opts;$('#voiceA').value='F3';$('#voiceB').value='M3';
 vst('Supertonic AI：10 種 AI 聲線；完整會話可讓 A / B 使用不同聲線。');
}
function refreshSystemVoices(){
 if(!('speechSynthesis'in window))return [];
 S.systemVoices=speechSynthesis.getVoices().filter(v=>/^ja([-_]|$)/i.test(v.lang));
 return S.systemVoices;
}
function renderDeviceVoices(){
 const a=S.systemVoices;
 const opts='<option value="random">🎲 每次隨機</option>'+a.map((v,i)=>`<option value="${i}">${esc(v.name)}｜${esc(v.lang)}</option>`).join('');
 $('#voiceA').innerHTML=opts;$('#voiceB').innerHTML=opts;
 if(a.length){$('#voiceA').value='0';$('#voiceB').value=String(Math.min(1,a.length-1));vst(`✅ 此裝置找到 ${a.length} 個日語系統聲線。`,'ok')}else vst('⚠️ 此裝置沒有找到日語 Speech Synthesis 聲線。','bad');
}
function loadSystemVoices(){
 refreshSystemVoices();
 if($('#engine').value==='device')renderDeviceVoices();
}
function populateDevice(){
 refreshSystemVoices();renderDeviceVoices();
}
function canonicalSpeakers(raw,limit){
 const preferred=['ノーマル','Normal','NORMAL','通常'];const rows=[];
 for(const sp of raw||[]){const styles=sp.styles||[];if(!sp.name||!styles.length)continue;const style=styles.find(x=>preferred.includes(String(x.name||'').trim()))||styles[0];rows.push({name:sp.name,style:style.name||'',id:String(style.id)})}
 return limit?rows.slice(0,limit):rows;
}
async function connectApi(engine){
 const endpoint=(engine==='voicevox'?$('#voicevoxEndpoint'):$('#aivisEndpoint')).value.replace(/\/$/,'');
 vst(`正在連接 ${engine==='voicevox'?'VOICEVOX':'AivisSpeech'}…`,'loading');
 try{
  const r=await fetch(endpoint+'/speakers',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
  const rows=canonicalSpeakers(await r.json(),engine==='voicevox'?43:0);if(!rows.length)throw Error('找不到聲線');
  S.apiVoices=rows;
  const opts='<option value="random">🎲 每句隨機</option>'+rows.map(x=>`<option value="${esc(x.id)}">${esc(x.name)}｜${esc(x.style)}</option>`).join('');
  $('#voiceA').innerHTML=opts;$('#voiceB').innerHTML=opts;if(rows[0])$('#voiceA').value=rows[0].id;if(rows[1])$('#voiceB').value=rows[1].id;
  vst(`✅ ${engine==='voicevox'?'VOICEVOX':'AivisSpeech'} 已連接：載入 ${rows.length} 個可用聲線${engine==='voicevox'?'（上限 43）':''}。`,'ok');return true;
 }catch(e){
  S.apiVoices=[];$('#voiceA').innerHTML='<option value="">未連線</option>';$('#voiceB').innerHTML='<option value="">未連線</option>';
  vst(`⚠️ 無法連接本機 ${engine==='voicevox'?'VOICEVOX':'AivisSpeech'}：${e.message||e}。可改用 Supertonic 或裝置日語。`,'bad');return false;
 }
}
async function ensureSuper(){
 try{
  for(let i=0;i<120&&!window.SupertonicAI;i++)await sleep(50);
  if(!window.SupertonicAI)throw Error('Supertonic module not ready');
  if(window.SupertonicAI.isReady&&window.SupertonicAI.isReady()){S.superReady=true;return true}
  if('serviceWorker'in navigator){try{await navigator.serviceWorker.register('./supertonic-sw.js',{scope:'./'});await navigator.serviceWorker.ready}catch(e){}}
  await window.SupertonicAI.preflight();
  await window.SupertonicAI.init(m=>vst(m,'loading'));S.superReady=true;vst('✅ Supertonic AI 日語語音已準備。','ok');return true;
 }catch(e){vst('⚠️ Supertonic 無法載入，可切換到裝置日語。','bad');return false}
}
async function playAudioObject(url,token){
 return new Promise((resolve,reject)=>{const a=S.audio=new Audio(url);let done=false;
  const end=(ok,e)=>{if(done)return;done=true;a.onended=a.onerror=null;if(S.audio===a)S.audio=null;ok?resolve():reject(e||Error('audio failed'))};
  a.onended=()=>end(true);a.onerror=()=>end(false,Error('audio playback failed'));
  if(token!==S.stopToken)return end(true);const p=a.play();if(p&&p.catch)p.catch(e=>end(false,e));
 });
}
async function speakSuper(text,role,token,voiceOverride=null){
 if(!await ensureSuper())throw Error('Supertonic unavailable');if(token!==S.stopToken)return;
 const voice=voiceOverride||selectedVoice(role)||'F3',speed=Number($('#speed').value);
 vst(`✨ Supertonic 正在產生 ${role}｜${voice}…`,'loading');
 const out=await window.SupertonicAI.synthesize(text,{voice,speed,totalSteps:5});if(token!==S.stopToken)return;
 await playAudioObject(out.url,token);vst(`✅ Supertonic ${voice} 播放完成。`,'ok');
}
async function speakApi(text,role,token,engine){
 const endpoint=(engine==='voicevox'?$('#voicevoxEndpoint'):$('#aivisEndpoint')).value.replace(/\/$/,'');
 if(!S.apiVoices.length){if(!await connectApi(engine))throw Error(engine+' not connected')}
 if(token!==S.stopToken)return;
 const speaker=selectedVoice(role);if(!speaker)throw Error('speaker unavailable');
 const q=await fetch(endpoint+`/audio_query?text=${encodeURIComponent(text)}&speaker=${encodeURIComponent(speaker)}`,{method:'POST'});
 if(!q.ok)throw Error('audio_query HTTP '+q.status);const query=await q.json();query.speedScale=Number($('#speed').value);
 const r=await fetch(endpoint+`/synthesis?speaker=${encodeURIComponent(speaker)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(query)});
 if(!r.ok)throw Error('synthesis HTTP '+r.status);const blob=await r.blob();if(token!==S.stopToken)return;
 if(S.blobUrl)URL.revokeObjectURL(S.blobUrl);S.blobUrl=URL.createObjectURL(blob);await playAudioObject(S.blobUrl,token);
}
async function speakDevice(text,role,token){
 if(!('speechSynthesis'in window))throw Error('Speech Synthesis unsupported');
 loadSystemVoices();if(!S.systemVoices.length)throw Error('No Japanese device voice');
 const raw=selectedVoice(role);let voice;
 if(raw==='random'||raw==='')voice=pick(S.systemVoices);else voice=S.systemVoices[Number(raw)]||S.systemVoices[0];
 await new Promise((resolve,reject)=>{if(token!==S.stopToken)return resolve();const u=new SpeechSynthesisUtterance(text);u.lang='ja-JP';u.rate=Number($('#speed').value);u.voice=voice;u.onend=resolve;u.onerror=e=>reject(e.error||Error('speech error'));speechSynthesis.speak(u)});
}
async function speak(text,role,token){
 const eng=$('#engine').value;
 if(eng==='supertonic')return speakSuper(text,role,token);
 if(eng==='voicevox'||eng==='aivis'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;
  if(used)return;
  vst(`${eng==='voicevox'?'VOICEVOX':'AivisSpeech'} 此句沒有本站預錄音，已自動使用 Supertonic 備援。`,'loading');
  return speakSuper(text,role,token,role==='B'?'M3':'F3');
 }
 return speakDevice(text,role,token);
}
async function playLine(i){
 stop();const token=S.stopToken;const l=S.item.lines[i];st(`🔊 正在播放 Speaker ${l.role}…`,'loading');
 try{await speak(l.jp,l.role,token);if(token===S.stopToken)st(`✅ Speaker ${l.role} 播放完成。`,'ok')}catch(e){if(token===S.stopToken)st(`播放失敗：${e.message||e}`,'bad')}
}
async function playAll(){
 stop();const token=S.stopToken;st('▶ 正在播放完整會話…','loading');
 try{
  for(let i=0;i<S.item.lines.length;i++){if(token!==S.stopToken)return;const l=S.item.lines[i];await speak(l.jp,l.role,token);if(i<S.item.lines.length-1)await sleep(S.mode==='shadow'?2200:500)}
  if(token!==S.stopToken)return;
  st(S.mode==='shadow'?'✅ 跟讀完成。每句之間已預留跟讀時間。':'✅ 完整會話播放完成。','ok');
  if($('#autoNext').checked){await sleep(700);if(token===S.stopToken){randomDialog();playAll()}}
 }catch(e){if(token===S.stopToken)st(`播放失敗：${e.message||e}`,'bad')}
}
function updateDictPrompt(){
 if(!S.item)return;const l=S.item.lines[S.dictLine];$('#dictPrompt').textContent=`聽 Speaker ${l.role}，把聽到的日文輸入下面。`;$('#dictInput').value='';$('#dictResult').textContent='';
}
function norm(s){return String(s||'').normalize('NFKC').replace(/[\s　、。！？!?「」『』（）()・,.]/g,'').trim()}
function levenshtein(a,b){a=[...a];b=[...b];const m=Array(b.length+1).fill(0).map((_,j)=>j);for(let i=1;i<=a.length;i++){let prev=m[0];m[0]=i;for(let j=1;j<=b.length;j++){const tmp=m[j];m[j]=Math.min(m[j]+1,m[j-1]+1,prev+(a[i-1]===b[j-1]?0:1));prev=tmp}}return m[b.length]}
function checkDict(){
 const target=S.item.lines[S.dictLine].jp,got=$('#dictInput').value,a=norm(target),b=norm(got);if(!b){$('#dictResult').textContent='請先輸入你聽到的日文。';return}
 const d=levenshtein(a,b),score=Math.max(0,Math.round((1-d/Math.max(a.length,b.length,1))*100));
 $('#dictResult').innerHTML=score===100?`<b style="color:#11784a">✅ 完全正確！</b>`:`相似度 <b>${score}%</b><br>正確句子：<b>${esc(target)}</b>`;
}
async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic')populateSupertonic();
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}
async function init(){
 try{
  const scenes=window.SITUATION_SCENES||[];if(!scenes.length)throw Error('沒有會話資料');
  const dialogueCount=scenes.reduce((n,s)=>n+s.items.length,0);
  const utteranceCount=scenes.reduce((n,s)=>n+s.items.reduce((m,i)=>m+i.lines.length,0),0);
  S.data={scenes,sceneCount:scenes.length,dialogueCount,utteranceCount};
  $('#total').textContent=`${S.data.sceneCount} 場景｜${S.data.dialogueCount} 組會話`;
  populateScenes();$('#scene').value='station';S.scene=sceneById('station');populateSituations();
 }catch(e){st('會話資料載入失敗：'+(e.message||e),'bad');return}
 populateSupertonic();loadSystemVoices();if('speechSynthesis'in window)speechSynthesis.onvoiceschanged=loadSystemVoices;
 $('#scene').onchange=()=>{S.scene=sceneById($('#scene').value);resetReveal();populateSituations()};
 $('#situation').onchange=()=>{const a=filteredItems();S.item=a[Number($('#situation').value)]||a[0];resetReveal();render()};
 $$('.level input').forEach(x=>x.onchange=()=>populateSituations(S.item));
 $$('.mode').forEach(b=>b.onclick=()=>{S.mode=b.dataset.mode;resetReveal();modeUI()});
 $('#showZh').onchange=render;
 $('#reveal').onclick=()=>{const shown=$('#reveal').dataset.shown==='1';if(shown){delete $('#reveal').dataset.shown;$('#reveal').textContent='👁 顯示日文'}else{$('#reveal').dataset.shown='1';$('#reveal').textContent='🙈 隱藏日文'}render()};
 $('#randomScene').onclick=randomDialog;$('#prevDialog').onclick=()=>moveDialog(-1);$('#nextDialog').onclick=()=>moveDialog(1);
 $('#playAll').onclick=playAll;$('#playA').onclick=()=>playLine(0);$('#playB').onclick=()=>playLine(1);$('#stop').onclick=()=>{stop();st('已停止。')};
 $('#dictListen').onclick=()=>playLine(S.dictLine);$('#dictCheck').onclick=checkDict;$('#dictOther').onclick=()=>{S.dictLine=S.dictLine?0:1;updateDictPrompt()};
 $('#engine').onchange=engineChanged;
 $('#speed').oninput=()=>$('#speedValue').textContent=Number($('#speed').value).toFixed(2)+'×';
 render();
}
init();
})();