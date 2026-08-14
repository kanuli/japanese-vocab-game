(function(){
'use strict';
var W=window.WA=window.WA||{};
var currentAudio=null;
var aiInitPromise=null;
function el(id){return document.getElementById(id);}
function status(msg){var x=el('voiceStatus');if(x)x.textContent=msg;}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}
function ensureEnableButton(){
  var old=el('enableAI');if(old)return old;
  var sample=el('sampleVoice');if(!sample)return null;
  var b=document.createElement('button');
  b.id='enableAI';b.className='btn';b.type='button';
  b.style.width='100%';b.style.margin='9px 0 0';
  sample.parentNode.parentNode.insertBefore(b,sample.parentNode.nextSibling);
  b.onclick=function(){enableAI(true);};
  return b;
}
async function waitForModule(){
  if(window.SupertonicAI)return window.SupertonicAI;
  var eventSeen=false;
  function onReady(){eventSeen=true;}
  window.addEventListener('supertonic-ai-module-ready',onReady,{once:true});
  try{
    for(var i=0;i<1200;i++){
      if(window.SupertonicAI)return window.SupertonicAI;
      if(eventSeen&&window.SupertonicAI)return window.SupertonicAI;
      await sleep(50);
    }
  }finally{
    try{window.removeEventListener('supertonic-ai-module-ready',onReady);}catch(e){}
  }
  throw new Error('Supertonic AI 模組 60 秒內仍未載入；請檢查網路或重新整理頁面。');
}
async function waitForController(ms){
  if(!('serviceWorker' in navigator))return false;
  if(navigator.serviceWorker.controller)return true;
  return new Promise(function(resolve){
    var done=false;
    function finish(v){if(done)return;done=true;clearTimeout(t);try{navigator.serviceWorker.removeEventListener('controllerchange',changed);}catch(e){}resolve(v);}
    function changed(){finish(!!navigator.serviceWorker.controller);}
    var t=setTimeout(function(){finish(!!navigator.serviceWorker.controller);},ms||4000);
    navigator.serviceWorker.addEventListener('controllerchange',changed);
  });
}
async function ensureSupertonicCache(){
  if(!('serviceWorker' in navigator)||!('caches' in window))return false;
  try{
    var reg=await navigator.serviceWorker.register('./supertonic-sw.js',{scope:'./'});
    try{await reg.update();}catch(e){}
    await navigator.serviceWorker.ready;
    await waitForController(5000);
    try{if(navigator.storage&&navigator.storage.persist)await navigator.storage.persist();}catch(e){}
    return true;
  }catch(e){
    console.warn('Supertonic persistence unavailable',e);
    return false;
  }
}
async function supertonicCacheInfo(){
  try{
    if(!('caches' in window))return{ready:false,modelCount:0};
    var c=await caches.open('supertonic-model-v1');
    var keys=await c.keys();
    var modelCount=keys.filter(function(r){return /\.onnx(?:\?|$)/i.test(r.url);}).length;
    return{ready:modelCount>=4,modelCount:modelCount};
  }catch(e){return{ready:false,modelCount:0};}
}
async function updateAiCacheStatus(){
  var b=ensureEnableButton();
  var info=await supertonicCacheInfo();
  if(window.SupertonicAI&&window.SupertonicAI.isReady&&window.SupertonicAI.isReady()){
    status('✅ Supertonic 3 AI 語音已載入；逐字試聽已可使用。');
    if(b){b.textContent='✅ Supertonic AI 已啟用';b.disabled=true;}
    return info;
  }
  if(info.ready){
    status('✅ 此瀏覽器已保存 Supertonic 模型（'+info.modelCount+' 個主要模型）。按下面按鈕載入，不需重新下載約 400 MB。');
    if(b){b.textContent='載入已安裝的 Supertonic AI';b.disabled=false;}
  }else{
    status('首次使用需要下載並保存約 400 MB Supertonic 模型；只需完成一次。');
    if(b){b.textContent='首次安裝 Supertonic（約 400 MB）';b.disabled=false;}
  }
  return info;
}
async function enableAI(interactive){
  var b=ensureEnableButton();
  if(window.SupertonicAI&&window.SupertonicAI.isReady&&window.SupertonicAI.isReady())return true;
  if(aiInitPromise)return aiInitPromise;
  if(b)b.disabled=true;
  aiInitPromise=(async function(){
    try{
      await ensureSupertonicCache();
      var before=await supertonicCacheInfo();
      status(before.ready?'正在從此瀏覽器的本機快取載入 Supertonic…':'正在首次下載並安裝 Supertonic 模型（約 400 MB）…');
      var api=await waitForModule();
      if(typeof api.preflight!=='function'||typeof api.init!=='function')throw new Error('Supertonic API 不完整');
      await api.preflight();
      await api.init(function(msg){
        if(before.ready)status('正在從本機快取載入 Supertonic 模型…');
        else if(msg)status(String(msg));
      });
      if(!(api.isReady&&api.isReady()))throw new Error('Supertonic 初始化完成但模型未進入 ready 狀態');
      try{localStorage.setItem('jpwordlist_supertonic_installed',JSON.stringify({installed:true,at:Date.now()}));}catch(e){}
      status(before.ready?'✅ Supertonic 3 已從本機快取載入；沒有重新下載約 400 MB。':'✅ Supertonic 3 首次安裝完成；模型已保存在此瀏覽器。');
      return true;
    }catch(e){
      var msg=e&&e.message?e.message:String(e);
      status('⚠️ Supertonic 無法啟用：'+msg);
      console.error('Supertonic word-list initialization failed',e);
      return false;
    }finally{
      aiInitPromise=null;
      await updateAiCacheStatus();
      if(b&&!(window.SupertonicAI&&window.SupertonicAI.isReady&&window.SupertonicAI.isReady()))b.disabled=false;
    }
  })();
  return aiInitPromise;
}
W.supertonicCacheInfo=supertonicCacheInfo;
W.enableSupertonic=enableAI;
W.ensureVoice=function(){return enableAI(false);};
W.stopVoice=function(){
  if(currentAudio){try{currentAudio.pause();currentAudio.currentTime=0;}catch(e){}currentAudio=null;}
};
W.speak=async function(text){
  if(!text)return null;
  if(!await enableAI(false))return null;
  var api=window.SupertonicAI;
  var voiceEl=el('voice'),speedEl=el('speed');
  var choice=voiceEl&&voiceEl.value?voiceEl.value:'F3';
  if(choice==='random'){
    var all=(api&&api.voices&&api.voices.length)?api.voices:['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];
    choice=all[Math.floor(Math.random()*all.length)];
  }
  var speed=speedEl?Number(speedEl.value):1;
  if(!Number.isFinite(speed)||speed<=0)speed=1;
  W.stopVoice();
  status('AI 正在產生日語發音…');
  var out=await api.synthesize(String(text),{voice:choice,speed:speed,totalSteps:5});
  if(!out||!out.url)throw new Error('Supertonic 沒有回傳可播放音訊');
  await new Promise(function(done,reject){
    var a=currentAudio=new Audio(out.url),settled=false;
    function finish(ok,err){if(settled)return;settled=true;a.onended=null;a.onerror=null;if(currentAudio===a)currentAudio=null;ok?done():reject(err||new Error('音訊播放失敗'));}
    a.onended=function(){finish(true);};
    a.onerror=function(){finish(false,new Error('Supertonic 音訊播放失敗'));};
    try{var p=a.play();if(p&&typeof p.catch==='function')p.catch(function(e){finish(false,e);});}catch(e){finish(false,e);}
  });
  status('✅ Supertonic AI 日語語音已準備完成。');
  return choice;
};
window.addEventListener('supertonic-ai-module-ready',function(){updateAiCacheStatus();});
(async function(){
  ensureEnableButton();
  await ensureSupertonicCache();
  await updateAiCacheStatus();
})();
})();