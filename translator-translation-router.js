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
function providerLabel(provider){return ({'gemini-3.5-flash':'Gemini 3.5 Flash Free','gemini-3.5-flash-lite':'Gemini 3.5 Flash-Lite Free','gemini-3.1-flash-lite':'Gemini 3.1 Flash-Lite Free','chrome-translator':'Chrome Translator','mymemory':'MyMemory'})[provider]||provider||'Translator'}
function compactReason(err){
  const code=String(err?.code||'').trim();
  const msg=String(err?.message||err||'').trim();
  if(code==='unsupported_target')return 'Supabase function 仍是舊版（unsupported_target）';
  if(code==='gemini_free_unavailable')return 'Gemini Free 暫時不可用／限速';
  if(code==='site_safety_limit')return '本站 Gemini 每日安全上限已到';
  if(code==='gemini_not_configured')return 'Supabase 未讀到 GEMINI_API_KEY';
  if(code==='server_config_error')return 'Supabase function server config error';
  if(/429|RESOURCE_EXHAUSTED|quota/i.test(msg))return 'Gemini Free quota／rate limit';
  if(/HTTP 404|not found|model/i.test(msg))return 'Gemini model/API error';
  return code||msg.slice(0,120)||'Gemini unavailable';
}

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

async function edgeTranslateBilingual(text){
  if(!apiUrl||!publishableKey)throw Object.assign(Error('cloud router not configured'),{code:'cloud_not_configured'});
  const response=await fetch(apiUrl,{
    method:'POST',
    cache:'no-store',
    headers:{'Content-Type':'application/json','apikey':publishableKey},
    body:JSON.stringify({text,source:'ja'})
  });
  let data=null;
  try{data=await response.json()}catch(_e){}
  if(!response.ok){
    const err=Error(data?.message||data?.error||`cloud router HTTP ${response.status}`);
    err.code=data?.error||`http_${response.status}`;
    err.routerVersion=data?.routerVersion||'';
    err.attempts=Array.isArray(data?.attempts)?data.attempts:[];
    throw err;
  }
  const zh=String(data?.zh||'').trim(),en=String(data?.en||'').trim();
  if(!zh||!en)throw Object.assign(Error('cloud router returned an incomplete bilingual translation'),{code:'incomplete_bilingual'});
  return{zh,en,provider:String(data?.provider||'cloud'),routerVersion:String(data?.routerVersion||'')};
}

async function chromeTranslateBilingual(text,zhPromise,enPromise){
  const [zhTranslator,enTranslator]=await Promise.all([zhPromise,enPromise]);
  if(!zhTranslator||!enTranslator)throw Error('Chrome Translator bilingual pair unavailable');
  const [zh,en]=await Promise.all([
    zhTranslator.translate(text),
    enTranslator.translate(text)
  ]);
  const zhText=String(zh||'').trim(),enText=String(en||'').trim();
  if(!zhText||!enText)throw Error('Chrome Translator returned an incomplete bilingual translation');
  return{zh:zhText,en:enText,provider:'chrome-translator'};
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
  return output.join('\n');
}

async function myMemoryTranslateBilingual(text){
  const [zh,en]=await Promise.all([
    myMemoryTranslate(text,'zh-TW'),
    myMemoryTranslate(text,'en')
  ]);
  if(!zh||!en)throw Error('MyMemory returned an incomplete bilingual translation');
  return{zh,en,provider:'mymemory'};
}

async function translateBilingual(text,zhChrome,enChrome){
  let geminiError=null;
  try{return await edgeTranslateBilingual(text)}catch(err){geminiError=err;console.warn('Gemini Free bilingual translation unavailable; trying Chrome Translator for both languages.',err,err?.attempts||'')}
  try{
    const result=await chromeTranslateBilingual(text,zhChrome,enChrome);
    result.fallbackReason=compactReason(geminiError);
    return result;
  }catch(err){console.warn('Chrome Translator bilingual pair unavailable; trying MyMemory for both languages.',err)}
  const result=await myMemoryTranslateBilingual(text);
  result.fallbackReason=compactReason(geminiError);
  return result;
}

async function translate(){
  const jp=$('#jp'),zh=$('#zh'),en=$('#en'),button=$('#translate');
  const text=jp?.value.trim()||'';
  if(!text){setStatus('請先輸入日文句子。','bad');return}

  const zhChrome=startChromeTranslator('zh-TW');
  const enChrome=startChromeTranslator('en');

  if(button)button.disabled=true;
  setOutput(zh,'');setOutput(en,'');
  if($('#copyzh'))$('#copyzh').disabled=true;
  if($('#speakzh'))$('#speakzh').disabled=true;
  if($('#copyen'))$('#copyen').disabled=true;
  if($('#speaken'))$('#speaken').disabled=true;
  setStatus('正在以同一翻譯引擎產生繁體中文及 English…','loading');

  try{
    const result=await translateBilingual(text,zhChrome,enChrome);
    setOutput(zh,result.zh);setOutput(en,result.en);
    if($('#copyzh'))$('#copyzh').disabled=false;
    if($('#speakzh'))$('#speakzh').disabled=false;
    if($('#copyen'))$('#copyen').disabled=false;
    if($('#speaken'))$('#speaken').disabled=false;

    const autoSave=$('#historyAutoSave');
    if(autoSave?.checked)$('#saveHistory')?.click();
    const fallback=result.fallbackReason?`；Gemini fallback 原因：${result.fallbackReason}`:'';
    setStatus(`✅ 翻譯完成（${providerLabel(result.provider)}，繁中 + English 同一引擎${fallback}）。${autoSave?.checked?'已自動保存紀錄。':''}`,'ok');
  }catch(err){
    console.error('All bilingual translation providers failed',err);
    setStatus('翻譯暫時失敗：Gemini Free、Chrome Translator 及 MyMemory 均無法完整產生兩種語言。','bad');
  }finally{if(button)button.disabled=false}
}

function install(){
  const button=$('#translate'),jp=$('#jp');
  if(!button||!jp)return;
  button.onclick=translate;
  button.addEventListener('pointerdown',()=>{startChromeTranslator('zh-TW');startChromeTranslator('en')},{passive:true});
  jp.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();translate()}};
  const notice=$('.notice');
  if(notice)notice.textContent='翻譯採用零信用卡免費多引擎路由：Gemini API Free Tier → Chrome 內建 Translator → MyMemory 最後備援。繁體中文與 English 會鎖定使用同一個翻譯引擎；如 Gemini fallback，狀態列會顯示原因。Gemini API key 只存於 Supabase Edge Function Secrets。';
}

window.JPTranslationRouter=Object.freeze({translate,startChromeTranslator});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
