(()=>{'use strict';
const PATH=(location.pathname||'').toLowerCase();
if(/(?:^|\/)(?:mocktest|mock-test)(?:\.html)?(?:$|\/)/.test(PATH))return;
if(document.getElementById('siteVoiceTest'))return;
const CFG={
  voicevox:{label:'🎭 VOICEVOX',catalog:'./word-voicevox-catalog.json?v=2',group:'speakers'},
  supertonic3:{label:'✨ Supertonic 3',catalog:'./word-supertonic3-catalog.json?v=1',group:'voices'}
};
const cache={catalog:new Map(),index:new Map()};
let ctx=null,source=null,audio=null,blobUrl='';
const isMobile=()=>window.MobileSupertonicGuard?.isMobile===true||/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent||'');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const el=id=>document.getElementById(id);
function stop(){
  try{source?.stop();}catch(_){ } source=null;
  try{audio?.pause();if(audio)audio.currentTime=0;}catch(_){ } audio=null;
  if(blobUrl){try{URL.revokeObjectURL(blobUrl);}catch(_){ }blobUrl='';}
  try{window.MobileSupertonicGuard?.stopHostedAudio?.();}catch(_){ }
}
function unlock(){
  try{
    const AC=window.AudioContext||window.webkitAudioContext;
    if(!AC)return;
    if(!ctx)ctx=new AC();
    if(ctx.state==='suspended')ctx.resume();
    const b=ctx.createBuffer(1,1,22050),s=ctx.createBufferSource();s.buffer=b;s.connect(ctx.destination);s.start(0);
  }catch(_){ }
  try{window.MobileSupertonicGuard?.unlock?.();}catch(_){ }
}
async function json(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}
async function jsonFallback(a,b){try{return await json(a);}catch(e){if(!b||b===a)throw e;return json(b);}}
function group(c,eng){return c?.[CFG[eng].group]||c?.voices||c?.speakers||{};}
function voiceName(v,key){return String(v?.displayName||v?.speaker||v?.name||key)+(v?.style?'｜'+v.style:'');}
async function catalog(eng){
  if(cache.catalog.has(eng))return cache.catalog.get(eng);
  const p=json(CFG[eng].catalog).then(c=>{if(!c||c.status!=='ready'||!c.words||!Object.keys(group(c,eng)).length)throw new Error('伺服器聲線資料庫尚未就緒');return c;});
  cache.catalog.set(eng,p);
  try{return await p;}catch(e){cache.catalog.delete(eng);throw e;}
}
async function indexFor(eng,key,c){
  const ck=eng+'|'+key;if(cache.index.has(ck))return cache.index.get(ck);
  const v=group(c,eng)[key];if(!v)throw new Error('聲線索引不存在');
  const mobile=isMobile();
  const first=mobile?(v.indexHfUrl||v.indexGithubUrl||v.indexUrl):(v.indexGithubUrl||v.indexUrl||v.indexHfUrl);
  const second=mobile?(v.indexGithubUrl||v.indexUrl||v.indexHfUrl):(v.indexHfUrl||v.indexGithubUrl||v.indexUrl);
  if(!first)throw new Error('聲線索引網址不存在');
  const p=jsonFallback(first,second).then(d=>{if(!d?.bundles)throw new Error('聲線索引格式錯誤');return d;});
  cache.index.set(ck,p);
  try{return await p;}catch(e){cache.index.delete(ck);throw e;}
}
async function rangeBytes(bundle,offset,size){
  const end=offset+size-1;
  const urls=(isMobile()?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean);
  if(!urls.length)throw new Error('音訊來源不存在');
  let last;
  for(const url of urls){
    try{
      const r=await fetch(url,{headers:{Range:`bytes=${offset}-${end}`},cache:'force-cache'});
      const len=Number(r.headers.get('content-length')||0);
      if(r.status!==206&&!(r.status===200&&len===size))throw new Error('Range HTTP '+r.status+' length '+len);
      const b=await r.arrayBuffer();if(b.byteLength!==size)throw new Error('Range size '+b.byteLength+'/'+size);return b;
    }catch(e){last=e;}
  }
  throw last||new Error('音訊下載失敗');
}
async function play(bytes){
  stop();
  const g=window.MobileSupertonicGuard;
  if(g?.playHostedBytes){await g.playHostedBytes(bytes,1);return;}
  try{
    const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw new Error('AudioContext unavailable');
    if(!ctx)ctx=new AC();if(ctx.state==='suspended')await ctx.resume();
    const decoded=await ctx.decodeAudioData(bytes.slice(0));source=ctx.createBufferSource();source.buffer=decoded;source.connect(ctx.destination);
    await new Promise((resolve,reject)=>{const s=source;s.onended=()=>{if(source===s)source=null;resolve();};try{s.start(0);}catch(e){reject(e);}});return;
  }catch(e){
    blobUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/mpeg'}));
    await new Promise((resolve,reject)=>{const a=audio=new Audio(blobUrl);a.playsInline=true;a.onended=()=>{audio=null;resolve();};a.onerror=()=>{audio=null;reject(new Error('瀏覽器無法播放此預錄音'));};const p=a.play();if(p?.catch)p.catch(reject);});
  }
}
function chooseSample(c){
  const ks=Object.keys(c.words||{});if(!ks.length)throw new Error('聲音資料庫沒有可測試單字');
  for(const p of ['こんにちは','ありがとう','日本','私']){const hit=ks.find(k=>k===p||k.startsWith(p+'|'));if(hit)return hit;}
  return ks[0];
}
async function populate(eng){
  const s=el('svtVoice'),st=el('svtStatus');
  s.disabled=true;s.innerHTML='<option>聲線資料載入中…</option>';st.textContent=`正在讀取 ${CFG[eng].label} 聲線資料…`;
  const c=await catalog(eng),all=Object.keys(group(c,eng));
  s.innerHTML='<option value="random">🎲 隨機聲線</option>'+all.map(k=>`<option value="${esc(k)}">${esc(voiceName(group(c,eng)[k],k))}</option>`).join('');
  s.disabled=false;st.textContent=`✅ ${CFG[eng].label}：${all.length} 種聲線可測試。`;
  return c;
}
async function test(){
  unlock();const btn=el('svtPlay'),eng=el('svtEngine').value,st=el('svtStatus');
  btn.disabled=true;btn.textContent='載入中…';
  try{
    const c=await populate(eng),word=chooseSample(c),lookup=c.words[word];
    if(!Array.isArray(lookup)||lookup.length<2)throw new Error('測試單字索引無效');
    const id=lookup[0],shard=String(lookup[1]),voices=Object.keys(group(c,eng));
    let key=el('svtVoice').value;if(!key||key==='random'||!voices.includes(key))key=voices[Math.floor(Math.random()*voices.length)];
    const idx=await indexFor(eng,key,c),bundle=idx.bundles?.[shard],member=bundle?.members?.[id];
    if(!bundle||!member)throw new Error('此測試單字沒有對應預錄音');
    const shown=word.split('|').filter(Boolean).join('・');
    st.textContent=`🔄 ${CFG[eng].label}｜${voiceName(group(c,eng)[key],key)}｜${shown}：下載預錄音…`;
    const bytes=await rangeBytes(bundle,Number(member[0]),Number(member[1]));
    st.textContent=`▶ ${CFG[eng].label}｜${voiceName(group(c,eng)[key],key)}｜${shown}`;
    await play(bytes);
    st.textContent=`✅ 播放成功：${CFG[eng].label}｜${voiceName(group(c,eng)[key],key)}｜${shown}`;
  }catch(e){
    console.error('[site-voice-test]',e);st.textContent=`⚠️ ${CFG[eng].label} 測試失敗：${e?.message||e}`;
  }finally{btn.disabled=false;btn.textContent='▶ 試聽聲線';}
}
function mount(){
  if(document.getElementById('siteVoiceTest'))return;
  const css=document.createElement('style');css.textContent=`#siteVoiceTest{box-sizing:border-box;margin:12px auto;padding:12px 14px;max-width:1100px;border:1px solid #dbe3ef;border-radius:14px;background:#fff;box-shadow:0 4px 16px rgba(28,43,75,.06);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif;color:#182033}#siteVoiceTest *{box-sizing:border-box}#siteVoiceTest .svt-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:9px}#siteVoiceTest .svt-title{font-weight:800;font-size:15px}#siteVoiceTest .svt-badge{font-size:11px;padding:3px 7px;border-radius:999px;background:#eef4ff;color:#355db8}#siteVoiceTest .svt-grid{display:grid;grid-template-columns:minmax(150px,.8fr) minmax(180px,1.4fr) auto;gap:8px;align-items:end}#siteVoiceTest label{display:grid;gap:4px;font-size:12px;font-weight:700;color:#566176}#siteVoiceTest select,#siteVoiceTest button{min-height:40px;border:1px solid #cfd8e6;border-radius:10px;background:#fff;padding:8px 10px;font:inherit}#siteVoiceTest button{font-weight:800;cursor:pointer;background:#3568dd;color:#fff;border-color:#3568dd;white-space:nowrap}#siteVoiceTest button:disabled{opacity:.58;cursor:wait}#siteVoiceTest .svt-status{margin-top:8px;font-size:12px;line-height:1.45;color:#667085}#siteVoiceTest .svt-note{margin-top:5px;font-size:11px;color:#7b8494}@media(max-width:640px){#siteVoiceTest{margin:10px 12px;padding:11px}#siteVoiceTest .svt-grid{grid-template-columns:1fr}#siteVoiceTest button{width:100%}}`;
  document.head.appendChild(css);
  const box=document.createElement('section');box.id='siteVoiceTest';box.setAttribute('aria-label','語音測試');box.innerHTML=`<div class="svt-head"><div class="svt-title">🔊 語音測試｜Voice Test</div><span class="svt-badge">手機可用</span></div><div class="svt-grid"><label>語音引擎<select id="svtEngine"><option value="voicevox">🎭 VOICEVOX</option><option value="supertonic3">✨ Supertonic 3</option></select></label><label>聲線<select id="svtVoice"><option value="random">🎲 隨機聲線</option></select></label><button id="svtPlay" type="button">▶ 試聽聲線</button></div><div id="svtStatus" class="svt-status" aria-live="polite">選擇 VOICEVOX 或 Supertonic 3，然後按「試聽聲線」。</div><div class="svt-note">手機版只播放伺服器預錄音，不載入約 400 MB 的本機 Supertonic 模型。</div>`;
  const main=document.querySelector('main');const wrap=document.querySelector('.wrap,.container,#app');
  if(main)main.insertBefore(box,main.firstChild);else if(wrap)wrap.insertBefore(box,wrap.firstChild);else document.body.insertBefore(box,document.body.firstChild);
  el('svtPlay').addEventListener('pointerdown',unlock,{passive:true});el('svtPlay').addEventListener('touchstart',unlock,{passive:true});el('svtPlay').addEventListener('click',test);
  el('svtEngine').addEventListener('change',()=>{stop();populate(el('svtEngine').value).catch(e=>{el('svtStatus').textContent='⚠️ 聲線資料載入失敗：'+(e?.message||e);});});
  el('svtVoice').addEventListener('focus',()=>{if(el('svtVoice').options.length<=1)populate(el('svtEngine').value).catch(()=>{});},{once:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
window.JapaneseSiteVoiceTest={test,stop,populate,version:'20260817.1'};
})();