(()=>{'use strict';
const BASE='./';
const MAX_AGE=48*60*60*1000;
const JLPT_DEFAULT_ALL_PAGES=new Set(['index.html','wordaudio.html','wordlist.html','grammar.html','listening.html','conversation.html','pronunciation.html']);
const JLPT_RANGE_PRESET_PAGES=new Set(['conversation.html','pronunciation.html']);
function pageName(){return(location.pathname.split('/').pop()||'index.html').toLowerCase();}
function jlptLevelInputs(){return[...document.querySelectorAll('.levels .level input[type="checkbox"]')].filter(x=>/^N[1-5]$/i.test(String(x.value||'')));}
function notifyLevelChange(inputs){if(!inputs.length)return;inputs[0].dispatchEvent(new Event('change',{bubbles:true}));}
function selectJlptLevels(inputs,values){const wanted=new Set(values);inputs.forEach(x=>{x.checked=wanted.has(String(x.value||'').toUpperCase())});notifyLevelChange(inputs);}
function mountJlptRangePresets(){
  if(!JLPT_RANGE_PRESET_PAGES.has(pageName()))return;
  const levels=document.querySelector('.levels'),inputs=jlptLevelInputs();
  if(!levels||!inputs.length||document.querySelector('[data-jlpt-range-presets]'))return;
  const row=document.createElement('div');row.className='row presets';row.dataset.jlptRangePresets='1';row.setAttribute('aria-label','JLPT 範圍快捷選擇');
  Object.assign(row.style,{display:'flex',gap:'7px',flexWrap:'wrap',margin:'9px 0 18px'});
  const presets=[['全部',['N1','N2','N3','N4','N5']],['N2–N5',['N2','N3','N4','N5']],['N3–N5',['N3','N4','N5']],['N4–N5',['N4','N5']],['只 N4',['N4']]];
  presets.forEach(([label,values])=>{const b=document.createElement('button');b.type='button';b.className='btn preset';b.textContent=label;b.dataset.l=values.join(',');b.onclick=()=>selectJlptLevels(inputs,values);row.appendChild(b)});
  levels.insertAdjacentElement('afterend',row);
}
function applyDefaultAllJlptLevels(){
  if(!JLPT_DEFAULT_ALL_PAGES.has(pageName()))return;
  const inputs=jlptLevelInputs();if(!inputs.length)return;
  const changed=inputs.some(x=>!x.checked);inputs.forEach(x=>{x.checked=true});
  if(changed)notifyLevelChange(inputs);
}
function setupJlptRangeUI(){mountJlptRangePresets();applyDefaultAllJlptLevels();}
function loadPageVoiceAudition(){
  const page=pageName();
  const allowed=new Set(['wordaudio.html','wordlist.html','listening.html','conversation.html','pronunciation.html','translator.html']);
  if(!allowed.has(page)||document.querySelector('script[data-page-voice-audition]'))return;
  const s=document.createElement('script');s.src=BASE+'page-voice-audition.js?v=20260817v5';s.defer=true;s.dataset.pageVoiceAudition='1';(document.head||document.documentElement).appendChild(s);
}
function loadGenericVoiceTest(){
  const page=pageName();
  const allowed=new Set(['index.html','grammar.html','wordaudio.html','vocab-plus-game.html','vocabulary-plus.html']);
  if(!allowed.has(page)||document.querySelector('script[data-generic-voice-test]'))return;
  const s=document.createElement('script');s.src=BASE+'generic-voice-test.js?v=20260820v1';s.defer=true;s.dataset.genericVoiceTest='1';(document.head||document.documentElement).appendChild(s);
}
function loadResultHistory(){
  const page=pageName();
  const allowed=new Set(['index.html','grammar.html','listening.html','mocktest.html']);
  if(!allowed.has(page)||document.querySelector('script[data-result-history]'))return;
  const s=document.createElement('script');s.src=BASE+'result-history.js?v=20260818v2';s.defer=true;s.dataset.resultHistory='1';(document.head||document.documentElement).appendChild(s);
}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function mount(){
  if(document.getElementById('siteHealthBadge')) return document.getElementById('siteHealthBadge');
  const el=document.createElement('button');
  el.id='siteHealthBadge';el.type='button';el.setAttribute('aria-live','polite');
  Object.assign(el.style,{position:'fixed',right:'10px',bottom:'10px',zIndex:'2147483646',border:'1px solid #cfd7e6',borderRadius:'999px',padding:'6px 9px',font:'600 11px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',boxShadow:'0 3px 12px rgba(0,0,0,.12)',cursor:'pointer',background:'#fff',color:'#526071',opacity:'.92'});
  el.textContent='系統檢查中…';
  el.onclick=()=>{const d=el.dataset.detail||'系統健康狀態載入中。';alert(d);};
  (document.body||document.documentElement).appendChild(el);return el;
}
function paint(el,state,label,detail){
  const map={ok:['#edf9f2','#177a4b','#b7dfc9'],warn:['#fff8e7','#8a5b00','#efd58b'],bad:['#fff0f0','#a4261d','#efb6b2']};
  const [bg,fg,bd]=map[state]||map.warn;el.style.background=bg;el.style.color=fg;el.style.borderColor=bd;el.textContent=label;el.dataset.detail=detail;
}
async function getJson(path){const r=await fetch(BASE+path+'?health='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error(path+' HTTP '+r.status);return r.json();}
async function run(){
  setupJlptRangeUI();
  const el=mount();
  try{
    const [m,hf,d]=await Promise.allSettled([getJson('maintenance-status.json'),getJson('huggingface-backup-status.json'),getJson('dependency-status.json')]);
    if(m.status!=='fulfilled') throw m.reason;
    const x=m.value||{},checked=Date.parse(x.checkedAt||'');const age=Number.isFinite(checked)?Date.now()-checked:Infinity;
    const maintOk=x.status==='ok'&&x.checks?.static===true&&x.checks?.browser===true&&x.checks?.live===true;
    const hfOk=hf.status==='fulfilled'&&hf.value?.status==='ok';
    const stale=age>MAX_AGE;
    const dep=d.status==='fulfilled'?d.value:null;
    const parts=[`Maintenance: ${maintOk?'PASS':'FAIL'}`,`最後檢查: ${x.checkedAt||'不明'}`,`Pages: ${x.pages??'?'}`,`Hugging Face: ${hfOk?'PASS':(hf.status==='fulfilled'?hf.value?.status||'異常':'未有狀態')}`];
    if(dep?.checkedAt)parts.push(`依賴版本檢查: ${dep.checkedAt}`);
    if(!maintOk){paint(el,'bad','⚠ 系統檢查異常',parts.join('\n'));return;}
    if(stale||!hfOk){paint(el,'warn',stale?'⚠ Maintenance 過期':'⚠ 備援檢查異常',parts.join('\n'));return;}
    paint(el,'ok','● 系統正常',parts.join('\n'));
  }catch(e){paint(el,'bad','⚠ 無法讀取健康狀態','健康檢查失敗：'+(e?.message||e));}
}
loadPageVoiceAudition();
loadGenericVoiceTest();
loadResultHistory();
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run,{once:true});else run();
window.JapaneseSiteHealth={run,loadPageVoiceAudition,loadGenericVoiceTest,loadResultHistory,setupJlptRangeUI};
})();