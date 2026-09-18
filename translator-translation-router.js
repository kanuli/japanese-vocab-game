(()=>{'use strict';
const cfg=window.JP_TRANSLATOR_CLOUD_CONFIG||{};
const apiUrl=cfg.url?String(cfg.url).replace(/\/$/,'')+'/functions/v1/translate-router':'';
const publishableKey=String(cfg.anonKey||'');
const chromeTranslators=new Map();

function $(s){return document.querySelector(s)}
function setStatus(text,state=''){const el=$('#status');if(!el)return;el.textContent=text;el.className='status'+(state?' '+state:'')}
function setOutput(el,text){if(!el)return;el.textContent=text;el.classList.toggle('placeholder',!text)}
function decodeHtml(text){const x=document.createElement('textarea');x.innerHTML=String(text||'');return x.value}
function byteLength(text){return new TextEncoder().encode(text).length}
function myMemoryChunks(text,max=430){const parts=text.trim().split(/(?<=[。！？!?])/u).filter(Boolean),out=[];let cur='';for(const part of parts){if(byteLength(cur+part)<=max){cur+=part;continue}if(cur.trim())out.push(cur.trim());cur='';for(const ch of part){if(byteLength(cur+ch)>max){if(cur.trim())out.push(cur.trim());cur=ch}else cur+=ch}}if(cur.trim())out.push(cur.trim());return out}
function chromeTarget(target){return target==='zh-TW'?'zh-Hant':target}
function providerLabel(provider){return ({'google-nmt':'Google NMT','azure-translator':'Azure Translator','chrome-translator':'Chrome Translator','mymemory':'MyMemory'})[provider]||provider||'Translator'}

function startChromeTranslator(target){
  if(!('Translator' in self))return Promise.resolve(null);
  const targetLanguage=chromeTarget(target),key='ja>'+targetLanguage;
  if(chromeTranslators.has(key))return chromeTranslators.get(key);
  let promise;
  try{
    promise=self.Translator.create({
      sourceLanguage:'ja',
      targetLanguage,
      monitor(m){m.addEventListener('downloadprogress',e=>{if(Number.isFinite(e.loaded))console.debug(`Chrome Translator ${key}: ${Math.round(e.loaded*100)}%`)})}
    }).catch(err=>{chromeTranslators.delete(key);console.debug('Chrome Translator unavailable',key,err);return null});
  }catch(err){console.debug('Chrome Translator create failed',key,err);promise=Promise.resolve(null)}
  chromeTranslators.set(key,promise);
  return promise;
}

async function edgeTranslate(text,target){
  if(!apiUrl||!publishableKey)throw Error('cloud router not configured');
  const response=await fetch(apiUrl,{
    method:'POST',
    cache:'no-store',
    headers:{'Content-Type':'application/json','apikey':publishableKey},
    body:JSON.stringify({text,source:'ja',target})
  });
  let data=null;
  try{data=await response.json()}catch(_e){}
  if(!response.ok)throw Error(data?.message||data?.error||`cloud router HTTP ${response.status}`);
  const translation=String(data?.translation||'').trim();
  if(!translation)throw Error('cloud router returned an empty translation');
  return{text:translation,provider:String(data?.provider||'cloud')};
}

async function chromeTranslate(text,target,translatorPromise){
  const translator=await translatorPromise;
  if(!translator)throw Error('Chrome Translator unavailable');
  const translated=String(await translator.translate(text)).trim();
  if(!translated)throw Error('Chrome Translator returned an empty translation');
  return{text:translated,provider:'chrome-translator'};
}

async function myMemoryOne(text,target){
  const url='https://api.mymemory.translated.net/get?q='+encodeURIComponent(text)+'&langpair='+encodeURIComponent('ja|'+target)+'&mt=1';
  const response=await fetch(url,{cache:'no-store'});
  if(!response.ok)throw Error('MyMemory HTTP '+response.status);
  const data=await response.json(),translated=data?.responseData?.translatedText;
  if(!translated||Number(data?.responseStatus||200)>=400)throw Error(data?.responseDetails||'MyMemory translation failed');
  return decodeHtml(translated).trim();
}

async function myMemoryTranslate(text,target){
  const parts=byteLength(text)<=430?[text]:myMemoryChunks(text);
  const output=[];
  for(const part of parts)output.push(await myMemoryOne(part,target));
  return{text:output.join('\n'),provider:'mymemory'};
}

async function translateTarget(text,target,chromePromise){
  try{return await edgeTranslate(text,target)}catch(err){console.warn('Cloud translation router unavailable; trying free browser fallback.',err)}
  try{return await chromeTranslate(text,target,chromePromise)}catch(err){console.warn('Chrome Translator unavailable; trying MyMemory.',err)}
  return myMemoryTranslate(text,target);
}

async function translate(){
  const jp=$('#jp'),zh=$('#zh'),en=$('#en'),button=$('#translate');
  const text=jp?.value.trim()||'';
  if(!text){setStatus('請先輸入日文句子。','bad');return}

  // Start Chrome's on-device translators while the click still has user activation.
  // They are fallback-only; cloud NMT remains the first choice.
  const zhChrome=startChromeTranslator('zh-TW');
  const enChrome=startChromeTranslator('en');

  if(button)button.disabled=true;
  setOutput(zh,'');setOutput(en,'');
  if($('#copyzh'))$('#copyzh').disabled=true;
  if($('#speakzh'))$('#speakzh').disabled=true;
  if($('#copyen'))$('#copyen').disabled=true;
  if($('#speaken'))$('#speaken').disabled=true;
  setStatus('正在以免費多引擎路由翻譯繁體中文及 English…','loading');

  try{
    const [z,e]=await Promise.all([
      translateTarget(text,'zh-TW',zhChrome),
      translateTarget(text,'en',enChrome)
    ]);
    setOutput(zh,z.text);setOutput(en,e.text);
    if($('#copyzh'))$('#copyzh').disabled=false;
    if($('#speakzh'))$('#speakzh').disabled=false;
    if($('#copyen'))$('#copyen').disabled=false;
    if($('#speaken'))$('#speaken').disabled=false;

    const autoSave=$('#historyAutoSave');
    if(autoSave?.checked)$('#saveHistory')?.click();
    const engines=[...new Set([providerLabel(z.provider),providerLabel(e.provider)])].join(' + ');
    setStatus(`✅ 翻譯完成（${engines}）。${autoSave?.checked?'已自動保存紀錄。':''}`,'ok');
  }catch(err){
    console.error('All translation providers failed',err);
    setStatus('翻譯暫時失敗：Google/Azure、Chrome Translator 及 MyMemory 均不可用。','bad');
  }finally{if(button)button.disabled=false}
}

function install(){
  const button=$('#translate'),jp=$('#jp');
  if(!button||!jp)return;
  button.onclick=translate;
  button.addEventListener('pointerdown',()=>{startChromeTranslator('zh-TW');startChromeTranslator('en')},{passive:true});
  jp.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();translate()}};
  const notice=$('.notice');
  if(notice)notice.textContent='翻譯採用免費多引擎路由：Google Cloud NMT → Azure Translator → Chrome 內建 Translator → MyMemory 最後備援。Google/Azure 私人金鑰只存於 Supabase Edge Function Secrets，不會放入網站或 GitHub。翻譯紀錄仍保存在本機，登入後可同步至 Supabase。';
}

window.JPTranslationRouter=Object.freeze({translate,startChromeTranslator});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
