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
function providerLabel(provider){return ({'plamo':'PLaMo 3 Translate 2B','gemini-3.5-flash':'Gemini 3.5 Flash Free','gemini-3.5-flash-lite':'Gemini 3.5 Flash-Lite Free','gemini-3.1-flash-lite':'Gemini 3.1 Flash-Lite Free','chrome-translator':'Chrome Translator','mymemory':'MyMemory'})[provider]||provider||'Translator'}
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

async function translateBilingual(text){
  // Default priority: PLaMo 3 Translate -> MyMemory -> Gemini Free ->
  // Chrome Translator. An explicit MyMemory selection skips only PLaMo.
  // Each candidate must produce BOTH languages; never mix engines.
  const preferPlamo=$('#translationProvider')?.value!=='mymemory';
  let plamoError=null;
  if(preferPlamo){
    try{
      if(!window.JapanesePlamoTranslator?.available?.())throw Error('PLaMo endpoint unavailable');
      const [zh,en]=await Promise.all([
        window.JapanesePlamoTranslator.translate(text,'zh-hant'),
        window.JapanesePlamoTranslator.translate(text,'en')
      ]);
      if(!String(zh||'').trim()||!String(en||'').trim())throw Error('Incomplete PLaMo bilingual response');
      return{zh:zh.trim(),en:en.trim(),provider:'plamo'};
    }catch(err){
      plamoError=err;
      console.warn('PLaMo unavailable; falling back to MyMemory.',err?.message||err);
    }
  }
  let myMemoryError=null;
  try{
    const result=await myMemoryTranslateBilingual(text);
    if(plamoError)result.plamoFallback=true;
    return result;
  }catch(err){
    myMemoryError=err;
    console.warn('MyMemory bilingual translation unavailable; trying Gemini Free.',err?.message||err);
  }
  let geminiError=null;
  try{
    const result=await edgeTranslateBilingual(text);
    result.myMemoryFallback=true;
    if(plamoError)result.plamoFallback=true;
    return result;
  }catch(err){
    geminiError=err;
    console.warn('Gemini Free bilingual translation unavailable; trying Chrome Translator.',err?.message||err);
  }
  // Chrome is the FINAL fallback. Do not pre-load Chrome Translator models
  // at the start of every request when PLaMo/MyMemory are working.
  const result=await chromeTranslateBilingual(text,
    startChromeTranslator('zh-TW'),startChromeTranslator('en'));
  result.myMemoryFallback=true;
  result.geminiFallbackReason=compactReason(geminiError);
  if(plamoError)result.plamoFallback=true;
  return result;
}

async function translate(){
  const jp=$('#jp'),zh=$('#zh'),en=$('#en'),button=$('#translate');
  const text=jp?.value.trim()||'';
  if(!text){setStatus('請先輸入日文句子。','bad');return}

  if(button)button.disabled=true;
  window.dispatchEvent(new CustomEvent('jpTranslatorTranslationStarted'));
  setOutput(zh,'');setOutput(en,'');
  if($('#copyzh'))$('#copyzh').disabled=true;
  if($('#speakzh'))$('#speakzh').disabled=true;
  if($('#copyen'))$('#copyen').disabled=true;
  if($('#speaken'))$('#speaken').disabled=true;
  setStatus('正在以同一翻譯引擎產生繁體中文及 English…','loading');

  try{
    const result=await translateBilingual(text);
    setOutput(zh,result.zh);setOutput(en,result.en);
    // Record the provider that actually returned both translations, not
    // the option selected before fallback. Emit before history autosave.
    window.dispatchEvent(new CustomEvent('jpTranslatorTranslationCompleted',{detail:{
      sourceText:text,zhText:result.zh,enText:result.en,
      provider:String(result.provider||''),plamoFallback:Boolean(result.plamoFallback)
    }}));
    if($('#copyzh'))$('#copyzh').disabled=false;
    if($('#speakzh'))$('#speakzh').disabled=false;
    if($('#copyen'))$('#copyen').disabled=false;
    if($('#speaken'))$('#speaken').disabled=false;

    const autoSave=$('#historyAutoSave');
    if(autoSave?.checked)$('#saveHistory')?.click();
    const fallback=result.geminiFallbackReason?`；Gemini 備援原因：${result.geminiFallbackReason}`:'';
    const plamoFallback=result.plamoFallback?'；PLaMo 不可用，已自動備援':'';
    const myMemoryFallback=result.myMemoryFallback?'；MyMemory 不可用，已自動備援':'';
    setStatus(`✅ 翻譯完成（${providerLabel(result.provider)}，繁中 + English 同一引擎${plamoFallback}${myMemoryFallback}${fallback}）。${autoSave?.checked?'已自動保存紀錄。':''}`,'ok');
  }catch(err){
    console.error('All bilingual translation providers failed',err);
    setStatus('翻譯暫時失敗：PLaMo、MyMemory、Gemini Free 及 Chrome Translator 均未能完成雙語翻譯。','bad');
  }finally{if(button)button.disabled=false}
}

function install(){
  const button=$('#translate'),jp=$('#jp');
  if(!button||!jp)return;
  button.onclick=translate;
  jp.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();translate()}};
  const notice=$('.notice');
  if(notice)notice.textContent='翻譯預設優先順序：PLaMo 3 Translate → MyMemory → Gemini Free → Chrome Translator。PLaMo 需先於「跨裝置同步」登入 Supabase；未登入或服務不可用時會按此順序自動備援。繁中與英文使用同一個實際翻譯來源，並記錄於翻譯紀錄。';
}

window.JPTranslationRouter=Object.freeze({translate,startChromeTranslator});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();
