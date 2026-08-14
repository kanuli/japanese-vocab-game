(function(){
'use strict';
var W=window.WA=window.WA||{};
var currentAudio=null;
var initPromise=null;
function el(id){return document.getElementById(id);}
function status(msg){var x=el('voiceStatus');if(x)x.textContent=msg;}
function sleep(ms){return new Promise(function(r){setTimeout(r,ms);});}
async function waitForModule(){
  if(window.SupertonicAI)return window.SupertonicAI;
  var eventReady=false;
  function ready(){eventReady=true;}
  window.addEventListener('supertonic-ai-module-ready',ready,{once:true});
  try{
    for(var i=0;i<300;i++){
      if(window.SupertonicAI)return window.SupertonicAI;
      if(eventReady&&window.SupertonicAI)return window.SupertonicAI;
      await sleep(50);
    }
  }finally{
    try{window.removeEventListener('supertonic-ai-module-ready',ready);}catch(e){}
  }
  throw new Error('Supertonic 模組載入逾時。請重新整理頁面後再試。');
}
async function preparePersistence(){
  if(!('serviceWorker' in navigator))return false;
  try{
    await navigator.serviceWorker.register('./supertonic-sw.js',{scope:'./'});
    await navigator.serviceWorker.ready;
    try{if(navigator.storage&&navigator.storage.persist)await navigator.storage.persist();}catch(e){}
    return true;
  }catch(e){return false;}
}
async function cacheInfo(){
  try{
    if(!('caches' in window))return{ready:false,count:0};
    var c=await caches.open('supertonic-model-v1');
    var keys=await c.keys();
    var count=keys.filter(function(r){return /\.onnx(?:\?|$)/i.test(r.url);}).length;
    return{ready:count>=4,count:count};
  }catch(e){return{ready:false,count:0};}
}
async function ensureVoice(){
  if(window.SupertonicAI&&window.SupertonicAI.isReady&&window.SupertonicAI.isReady())return true;
  if(initPromise)return initPromise;
  initPromise=(async function(){
    try{
      var info=await cacheInfo();
      status(info.ready?'正在載入已安裝的 Supertonic 模型…':'首次使用：正在準備 Supertonic AI 日語語音…');
      var api=await waitForModule();
      await preparePersistence();
      if(api.isReady&&api.isReady()){
        status('✅ Supertonic AI 日語語音已準備完成。');
        return true;
      }
      if(typeof api.preflight==='function')await api.preflight();
      if(typeof api.init!=='function')throw new Error('Supertonic init() 不存在');
      await api.init(function(m){if(m)status(String(m));});
      if(!(api.isReady&&api.isReady()))throw new Error('Supertonic 初始化完成但模型未進入 ready 狀態');
      status('✅ Supertonic AI 日語語音已準備完成。');
      return true;
    }catch(e){
      status('⚠️ Supertonic 載入失敗：'+(e&&e.message?e.message:String(e)));
      return false;
    }finally{
      initPromise=null;
    }
  })();
  return initPromise;
}
W.ensureVoice=ensureVoice;
W.stopVoice=function(){
  if(currentAudio){try{currentAudio.pause();currentAudio.currentTime=0;}catch(e){}currentAudio=null;}
};
W.speak=async function(text){
  if(!text)return null;
  if(!await ensureVoice())return null;
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
    var a=currentAudio=new Audio(out.url);
    var settled=false;
    function finish(ok,err){if(settled)return;settled=true;a.onended=null;a.onerror=null;if(currentAudio===a)currentAudio=null;ok?done():reject(err||new Error('音訊播放失敗'));}
    a.onended=function(){finish(true);};
    a.onerror=function(){finish(false,new Error('Supertonic 音訊播放失敗'));};
    var p=a.play();
    if(p&&typeof p.catch==='function')p.catch(function(e){finish(false,e);});
  });
  status('✅ Supertonic AI 日語語音已準備完成。');
  return choice;
};
(async function(){
  var info=await cacheInfo();
  if(info.ready)status('✅ 已找到本機 Supertonic 模型；按「試聽聲線」即可直接載入。');
  else status('Supertonic 模組已連接；首次播放時會初始化模型。');
})();
})();