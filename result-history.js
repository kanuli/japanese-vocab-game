(()=>{'use strict';
const PAGE=(location.pathname.split('/').pop()||'index.html').toLowerCase();
const SUPPORTED=new Set(['index.html','grammar.html','listening.html','mocktest.html']);
if(!SUPPORTED.has(PAGE)||window.JapaneseResultHistory)return;

const PAGE_ID=PAGE==='index.html'?'vocab':PAGE==='grammar.html'?'grammar':PAGE==='listening.html'?'listening':'mocktest';
const PRACTICE=PAGE_ID!=='mocktest';
const DB_NAME='JapaneseLearningHistory';
const DB_VERSION=1;
const STORE='runs';
const FALLBACK_KEY='jp_learning_history_fallback_v1';
let dbPromise=null,current=null,renderTimer=0;

const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean=s=>String(s??'').replace(/\s+/g,' ').trim();
const clip=(s,n=500)=>{s=clean(s);return s.length>n?s.slice(0,n-1)+'…':s};
const uid=()=>`${PAGE_ID}-${Date.now()}-${Math.random().toString(36).slice(2,9)}`;
const visible=el=>!!el&&getComputedStyle(el).display!=='none'&&getComputedStyle(el).visibility!=='hidden';
const plainText=(el,n=600)=>{if(!el)return'';const c=el.cloneNode(true);c.querySelectorAll?.('rt,rp').forEach(x=>x.remove());return clip(c.textContent,n);};

function openDB(){
  if(dbPromise)return dbPromise;
  dbPromise=new Promise((resolve,reject)=>{
    if(!('indexedDB'in window)){reject(new Error('IndexedDB unavailable'));return;}
    const req=indexedDB.open(DB_NAME,DB_VERSION);
    req.onupgradeneeded=()=>{
      const db=req.result;
      const st=db.objectStoreNames.contains(STORE)?req.transaction.objectStore(STORE):db.createObjectStore(STORE,{keyPath:'id'});
      if(!st.indexNames.contains('page'))st.createIndex('page','page',{unique:false});
      if(!st.indexNames.contains('createdAt'))st.createIndex('createdAt','createdAt',{unique:false});
    };
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error||new Error('IndexedDB open failed'));
  });
  return dbPromise;
}
function fallbackLoad(){try{const x=JSON.parse(localStorage.getItem(FALLBACK_KEY)||'[]');return Array.isArray(x)?x:[]}catch{return[]}}
function fallbackSave(a){try{localStorage.setItem(FALLBACK_KEY,JSON.stringify(a.slice(-100)))}catch{}}
async function putRun(run){
  try{
    const db=await openDB();
    await new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readwrite');tx.objectStore(STORE).put(run);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});
  }catch{
    const a=fallbackLoad().filter(x=>x.id!==run.id);a.push(run);fallbackSave(a);
  }
}
async function getRuns(){
  try{
    const db=await openDB();
    return await new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readonly');const req=tx.objectStore(STORE).index('page').getAll(PAGE_ID);req.onsuccess=()=>resolve(req.result||[]);req.onerror=()=>reject(req.error);});
  }catch{return fallbackLoad().filter(x=>x.page===PAGE_ID)}
}
async function clearRuns(){
  try{
    const db=await openDB();
    await new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readwrite'),idx=tx.objectStore(STORE).index('page');const req=idx.openCursor(IDBKeyRange.only(PAGE_ID));req.onsuccess=()=>{const cur=req.result;if(cur){cur.delete();cur.continue();}};tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});
  }catch{fallbackSave(fallbackLoad().filter(x=>x.page!==PAGE_ID))}
}

function injectCSS(){
  if($('#resultHistoryStyles'))return;
  const s=document.createElement('style');s.id='resultHistoryStyles';s.textContent=`
  .rh-card{background:#fff;border:1px solid var(--line,#dde3ec);border-radius:18px;padding:18px;box-shadow:0 14px 38px rgba(20,35,70,.08);margin:14px 0}
  .rh-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}.rh-title{font-size:19px;font-weight:900;margin:0}.rh-sub{color:var(--muted,#687082);font-size:12px;line-height:1.55;margin-top:4px}.rh-actions{display:flex;gap:7px;flex-wrap:wrap}.rh-btn{border:1px solid var(--line,#dde3ec);background:#fff;border-radius:10px;padding:8px 10px;font-weight:800;cursor:pointer;color:var(--text,#182033)}.rh-btn.primary{background:var(--blue,#3568dd);border-color:var(--blue,#3568dd);color:#fff}.rh-btn.danger{color:var(--bad,#b42318)}
  .rh-wrap{overflow:auto;margin-top:12px;border:1px solid #edf0f4;border-radius:13px}.rh-table{width:100%;border-collapse:collapse;min-width:720px;font-size:13px}.rh-table th,.rh-table td{text-align:left;padding:10px 9px;border-bottom:1px solid #edf0f4;vertical-align:middle}.rh-table th{background:#fafbfe;color:var(--muted,#687082);font-size:12px;position:sticky;top:0;z-index:1}.rh-table tr:last-child td{border-bottom:0}.rh-rank{font-weight:950;font-size:15px}.rh-score{font-weight:900}.rh-good{color:var(--ok,#11784a)}.rh-bad{color:var(--bad,#b42318)}.rh-empty{text-align:center;color:var(--muted,#687082);padding:24px}.rh-chip{display:inline-block;padding:3px 7px;border-radius:999px;background:#f2f4f8;font-size:11px;font-weight:800;margin:2px 3px 2px 0}.rh-status{font-weight:850}
  .rh-dialog{width:min(840px,calc(100% - 24px));max-height:86vh;border:1px solid var(--line,#dde3ec);border-radius:18px;padding:0;box-shadow:0 24px 80px rgba(20,30,55,.28);color:var(--text,#182033)}.rh-dialog::backdrop{background:rgba(20,30,50,.34)}.rh-dialog-head{position:sticky;top:0;background:#fff;border-bottom:1px solid #edf0f4;padding:15px 16px;display:flex;justify-content:space-between;gap:10px;align-items:flex-start;z-index:2}.rh-dialog-title{font-size:18px;font-weight:950}.rh-dialog-body{padding:14px 16px 18px;overflow:auto}.rh-filter{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 12px}.rh-detail-list{display:grid;gap:9px}.rh-detail{border:1px solid var(--line,#dde3ec);border-radius:13px;padding:12px;background:#fff}.rh-detail.bad{border-color:#efb6b1;background:#fffafa}.rh-detail.good{border-color:#b9dfca;background:#f6fcf8}.rh-detail-q{font-weight:850;line-height:1.65;margin-bottom:7px}.rh-detail-row{display:grid;grid-template-columns:86px 1fr;gap:5px 8px;font-size:13px;line-height:1.55}.rh-detail-label{color:var(--muted,#687082);font-weight:800}.rh-sectionbox{border:1px solid var(--line,#dde3ec);border-radius:12px;padding:11px;margin:7px 0;background:#fafbfe;line-height:1.55}.rh-small{font-size:12px;color:var(--muted,#687082)}
  @media(max-width:720px){.rh-card{padding:13px}.rh-dialog-head{padding:12px}.rh-dialog-body{padding:12px}.rh-detail-row{grid-template-columns:72px 1fr}.rh-table{min-width:650px}}
  `;(document.head||document.documentElement).appendChild(s);
}

function panelTitle(){return PAGE_ID==='vocab'?'📚 單字挑戰成績排行榜':PAGE_ID==='grammar'?'📝 文法挑戰成績排行榜':PAGE_ID==='listening'?'🎧 聽解挑戰成績排行榜':'🧪 N1–N5 模擬試驗記錄';}
function mountPanel(){
  if($('#resultHistoryPanel'))return;
  injectCSS();
  const host=document.createElement('section');host.id='resultHistoryPanel';host.className='rh-card';
  host.innerHTML=`<div class="rh-head"><div><div class="rh-title">${panelTitle()}</div><div class="rh-sub">${PRACTICE?'按正確率排名；同分時題數較多者優先。每次遊戲的答案與錯題會保留，可隨時重看。':'按完成時間保存每次模擬試驗的 180 分制推定分數、各 scoring section 與合格判定。'}</div></div><div class="rh-actions"><button class="rh-btn" id="rhRefresh">重新整理</button><button class="rh-btn danger" id="rhClear">清除記錄</button></div></div><div id="rhContent" class="rh-wrap"><div class="rh-empty">尚未有成績記錄。</div></div>`;
  const footer=document.querySelector('.footer');
  if(footer)footer.insertAdjacentElement('beforebegin',host);else(document.querySelector('.wrap')||document.body).appendChild(host);
  const d=document.createElement('dialog');d.id='rhDialog';d.className='rh-dialog';d.innerHTML=`<div class="rh-dialog-head"><div><div id="rhDialogTitle" class="rh-dialog-title">成績詳情</div><div id="rhDialogSub" class="rh-small"></div></div><button class="rh-btn" id="rhClose">關閉 ✕</button></div><div id="rhDialogBody" class="rh-dialog-body"></div>`;document.body.appendChild(d);
  $('#rhRefresh').onclick=renderPanel;
  $('#rhClear').onclick=async()=>{if(confirm('確定清除這一頁的全部成績記錄？此動作不能復原。')){await clearRuns();renderPanel();}};
  $('#rhClose').onclick=()=>d.close();
  d.addEventListener('click',e=>{if(e.target===d)d.close();});
  renderPanel();
}

function fmtDate(x){try{return new Intl.DateTimeFormat('zh-Hant',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(x))}catch{return x||''}}
function fmtLevels(run){const a=Array.isArray(run.levels)?run.levels:[];return a.length?a.join('、'):(run.level||'—')}
function pct(run){return Number.isFinite(run.percent)?run.percent:(run.total?Math.round((run.score||0)/run.total*100):0)}
function modeText(v){const m={all:'全部',wrong:'錯題',full:'標準',quick:'快速',hide:'先聽後顯示',show:'立即顯示'};return m[v]||v||'—'}

async function renderPanel(){
  clearTimeout(renderTimer);
  const box=$('#rhContent');if(!box)return;
  const runs=await getRuns();
  if(!runs.length){box.innerHTML='<div class="rh-empty">尚未有成績記錄。完成下一局後會自動加入。</div>';return;}
  if(PRACTICE){
    runs.sort((a,b)=>pct(b)-pct(a)||(b.total||0)-(a.total||0)||String(b.createdAt).localeCompare(String(a.createdAt)));
    box.innerHTML=`<table class="rh-table"><thead><tr><th>排名</th><th>日期／時間</th><th>JLPT</th><th>題數</th><th>分數</th><th>正確率</th><th>錯題</th><th>模式</th><th>檢討</th></tr></thead><tbody>${runs.map((r,i)=>`<tr><td class="rh-rank">${i+1}</td><td>${esc(fmtDate(r.createdAt))}</td><td>${esc(fmtLevels(r))}</td><td>${r.total||0}${r.incomplete?' *':''}</td><td class="rh-score">${r.score||0} / ${r.total||0}</td><td class="rh-score ${pct(r)>=80?'rh-good':pct(r)<60?'rh-bad':''}">${pct(r)}%</td><td class="${(r.wrong||0)>0?'rh-bad':'rh-good'}">${r.wrong||0}</td><td>${esc(modeText(r.mode))}</td><td><button class="rh-btn" data-rh-view="${esc(r.id)}">查看</button></td></tr>`).join('')}</tbody></table>${runs.some(r=>r.incomplete)?'<div class="rh-small" style="padding:8px 10px">* 中途返回／無限模式結束時，以已回答題目計算。</div>':''}`;
  }else{
    runs.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));
    box.innerHTML=`<table class="rh-table"><thead><tr><th>日期／時間</th><th>級別</th><th>模式</th><th>總分</th><th>Scoring sections</th><th>判定</th><th>詳情</th></tr></thead><tbody>${runs.map(r=>`<tr><td>${esc(fmtDate(r.createdAt))}</td><td><b>${esc(r.level||'—')}</b></td><td>${esc(modeText(r.mode))}</td><td class="rh-score">${esc(r.totalScore||'—')}</td><td>${(r.sections||[]).map(x=>`<span class="rh-chip">${esc(clip(x,80))}</span>`).join('')||'—'}</td><td class="rh-status ${/未達|不合格|FAIL/i.test(r.status||'')?'rh-bad':/合格|PASS/i.test(r.status||'')?'rh-good':''}">${esc(r.status||'—')}</td><td><button class="rh-btn" data-rh-view="${esc(r.id)}">查看</button></td></tr>`).join('')}</tbody></table>`;
  }
  box.querySelectorAll('[data-rh-view]').forEach(b=>b.onclick=()=>showRun(b.dataset.rhView,runs));
}

function detailMetaHTML(meta){
  if(!meta||typeof meta!=='object')return'';
  const skip=new Set(['你的答案','正確答案']);
  return Object.entries(meta).filter(([k,v])=>v&&!skip.has(k)).slice(0,8).map(([k,v])=>`<div class="rh-detail-label">${esc(k)}</div><div>${esc(clip(v,420))}</div>`).join('');
}
function renderDetails(run,wrongOnly=false){
  const body=$('#rhDialogBody');
  const details=(run.details||[]).filter(x=>!wrongOnly||!x.ok);
  const filters=run.details?.length?`<div class="rh-filter"><button class="rh-btn ${!wrongOnly?'primary':''}" data-rh-filter="all">全部 ${run.details.length}</button><button class="rh-btn ${wrongOnly?'primary':''}" data-rh-filter="wrong">只看錯題 ${(run.details||[]).filter(x=>!x.ok).length}</button></div>`:'';
  if(PRACTICE){
    body.innerHTML=filters+(details.length?`<div class="rh-detail-list">${details.map((d,i)=>`<div class="rh-detail ${d.ok?'good':'bad'}"><div class="rh-detail-q">${d.ok?'✅':'❌'} Q${i+1}　${esc(d.question||'')}</div><div class="rh-detail-row"><div class="rh-detail-label">你的答案</div><div class="${d.ok?'rh-good':'rh-bad'}">${esc(d.selected||'—')}</div><div class="rh-detail-label">正確答案</div><div class="rh-good"><b>${esc(d.correct||'—')}</b></div>${detailMetaHTML(d.meta)}</div></div>`).join('')}</div>`:'<div class="rh-empty">沒有錯題。</div>');
    body.querySelectorAll('[data-rh-filter]').forEach(b=>b.onclick=()=>renderDetails(run,b.dataset.rhFilter==='wrong'));
  }else{
    const sectionHtml=(run.sections||[]).map(x=>`<div class="rh-sectionbox">${esc(x)}</div>`).join('');
    const review=(run.review||[]);
    body.innerHTML=`<div class="rh-sectionbox"><b>${esc(run.level||'')}</b>　${esc(modeText(run.mode))}<br><span class="rh-score">${esc(run.totalScore||'')}</span>　<span class="rh-status">${esc(run.status||'')}</span>${run.durationSec?`<br><span class="rh-small">完成時間：約 ${Math.floor(run.durationSec/60)} 分 ${run.durationSec%60} 秒</span>`:''}</div>${sectionHtml}${run.note?`<div class="rh-sectionbox">${esc(run.note)}</div>`:''}${review.length?`<h3>答案與檢討</h3><div class="rh-detail-list">${review.map((x,i)=>`<div class="rh-detail ${x.bad?'bad':''}"><div class="rh-detail-q">Q${i+1} ${esc(x.summary||'')}</div>${x.body?`<div class="rh-small" style="white-space:pre-wrap">${esc(x.body)}</div>`:''}</div>`).join('')}</div>`:''}`;
  }
}
function showRun(id,runs){
  const run=runs.find(x=>x.id===id);if(!run)return;
  $('#rhDialogTitle').textContent=PRACTICE?`${panelTitle().replace('成績排行榜','')}｜${run.score}/${run.total}（${pct(run)}%）`:`${run.level||''} 模擬試驗｜${run.totalScore||''}`;
  $('#rhDialogSub').textContent=`${fmtDate(run.createdAt)}${run.incomplete?' · 中途結束':''}`;
  renderDetails(run,false);
  const d=$('#rhDialog');if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');
}

function selectedLevels(){return $$('.level input:checked').map(x=>x.value).filter(x=>/^N[1-5]$/.test(x));}
function selectedMode(){return $('input[name="mode"]:checked')?.value||$('input[name="qmode"]:checked')?.value||'';}
function beginPractice(){
  if(current&&!current.saved&&current.details?.length)savePractice(true);
  current={id:uid(),page:PAGE_ID,createdAt:new Date().toISOString(),startedAt:Date.now(),levels:selectedLevels(),mode:selectedMode(),details:[],saved:false};
}
function collectGrid(){
  const grid=$('#sheet .answer-grid')||$('.answer-grid');if(!grid)return{};
  const kids=[...grid.children],out={};
  for(let i=0;i<kids.length-1;i+=2){const k=plainText(kids[i],80),v=plainText(kids[i+1],600);if(k&&v)out[k]=v;}
  return out;
}
function currentQuestion(meta){
  const q=plainText($('#question')||$('.question'),500);
  return clip(q||meta['正確句子']||meta['漢字']||meta['讀音']||'',500);
}
function capturePracticeAnswer(btn){
  if(!current)beginPractice();
  setTimeout(()=>{
    if(!current||current.saved)return;
    const correctBtn=$('#choices .choice.correct');
    const selected=plainText(btn,600),correct=plainText(correctBtn,600),meta=collectGrid();
    const ok=btn.classList.contains('correct')&&!btn.classList.contains('wrong')||(selected&&correct&&selected===correct);
    const detail={question:currentQuestion(meta),selected,correct:correct||meta['正確答案']||meta['繁體中文']||meta['正確句子']||'',ok,level:meta['JLPT']||meta['等級']||'',meta};
    const fingerprint=`${detail.question}|${detail.selected}|${current.details.length}`;
    if(current.lastFingerprint===fingerprint)return;current.lastFingerprint=fingerprint;
    current.details.push(detail);
  },20);
}
async function savePractice(incomplete=false){
  if(!current||current.saved||!current.details.length)return;
  current.saved=true;
  const total=current.details.length,score=current.details.filter(x=>x.ok).length;
  const levels=[...new Set([...current.levels,...current.details.map(x=>x.level).filter(x=>/^N[1-5]$/.test(x))])];
  const run={id:current.id,page:PAGE_ID,createdAt:current.createdAt,levels,mode:current.mode,total,score,wrong:total-score,percent:Math.round(score/total*100),incomplete:!!incomplete,durationSec:Math.max(0,Math.round((Date.now()-current.startedAt)/1000)),details:current.details};
  await putRun(run);renderPanel();
}
function watchPracticeEnd(){
  const end=$('#end');if(!end)return;
  const check=()=>{if(visible(end)&&current&&!current.saved&&current.details.length)savePractice(false);};
  new MutationObserver(check).observe(end,{attributes:true,childList:true,subtree:true,attributeFilter:['style','class']});check();
}
function installPractice(){
  document.addEventListener('click',e=>{
    const start=e.target.closest('#start');if(start)beginPractice();
    const quit=e.target.closest('#quit');if(quit&&current&&!current.saved&&current.details.length)savePractice(true);
  },true);
  document.addEventListener('click',e=>{const choice=e.target.closest('#choices .choice');if(choice)capturePracticeAnswer(choice);},false);
  watchPracticeEnd();
}

function beginMock(){
  current={id:uid(),page:PAGE_ID,createdAt:new Date().toISOString(),startedAt:Date.now(),level:$('input[name="level"]:checked')?.value||'',mode:$('input[name="mode"]:checked')?.value||'',saved:false};
}
function parseMockReview(){return $$('#reviewList .review-item').map(x=>({bad:x.classList.contains('bad'),summary:clip(x.querySelector('summary')?.textContent||x.firstElementChild?.textContent||'',500),body:clip(x.querySelector('.review-body')?.textContent||x.textContent||'',1400)})).slice(0,250);}
async function saveMock(){
  if(current?.saved)return;
  if(!current)beginMock();
  const totalScore=clip($('#resultTotal')?.textContent||'',120),status=clip($('#resultStatus')?.textContent||'',120);if(!totalScore&&!status)return;
  current.saved=true;
  const level=clip($('#resultLevel')?.textContent||current.level,120);
  const run={id:current.id,page:PAGE_ID,createdAt:current.createdAt,level:level.match(/N[1-5]/)?.[0]||current.level||level,mode:current.mode,totalScore,status,sections:$$('#scoreGrid .scorebox').map(x=>clip(x.textContent,300)),note:clip($('#resultNote')?.textContent||'',700),durationSec:Math.max(0,Math.round((Date.now()-current.startedAt)/1000)),review:parseMockReview()};
  await putRun(run);renderPanel();
}
async function migrateLegacyMock(){
  const marker='jp_mock_history_migrated_v1';if(localStorage.getItem(marker))return;
  try{
    const hist=JSON.parse(localStorage.getItem('jlpt_mock_history')||'[]');
    if(Array.isArray(hist)){for(const x of hist){if(!x?.at)continue;await putRun({id:`mock-legacy-${x.at}`,page:PAGE_ID,createdAt:x.at,level:x.level||'',mode:x.mode||'',totalScore:Number.isFinite(x.total)?`${x.total} / 180`:'—',status:x.passed?'合格圏':'未達合格圏',sections:[],note:'舊版模擬試驗記錄：當時只保存總分與合格判定。',review:[],legacy:true});}}
  }catch{}
  try{localStorage.setItem(marker,'1')}catch{}
}
function installMock(){
  migrateLegacyMock().then(renderPanel);
  document.addEventListener('click',e=>{if(e.target.closest('#start'))beginMock();},true);
  const result=$('#resultPage');if(!result)return;
  const check=()=>{if(visible(result))setTimeout(saveMock,80);};
  new MutationObserver(check).observe(result,{attributes:true,childList:true,subtree:true,attributeFilter:['style','class']});check();
}

function init(){mountPanel();PRACTICE?installPractice():installMock();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
window.JapaneseResultHistory={render:renderPanel,getRuns,clear:clearRuns};
})();