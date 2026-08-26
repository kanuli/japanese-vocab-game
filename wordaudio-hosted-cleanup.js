(function(){
'use strict';
async function cleanupLegacyLocalSupertonic(){
  try{if('caches' in window)await caches.delete('supertonic-model-v1');}catch(e){console.warn('Legacy Supertonic cache cleanup skipped',e);}
  try{localStorage.removeItem('jpwordlist_supertonic_installed');}catch(e){}
  try{
    if(!('serviceWorker' in navigator)||!navigator.serviceWorker.getRegistrations)return;
    var regs=await navigator.serviceWorker.getRegistrations();
    for(var i=0;i<regs.length;i++){
      var r=regs[i],urls=[r.active&&r.active.scriptURL,r.waiting&&r.waiting.scriptURL,r.installing&&r.installing.scriptURL].filter(Boolean);
      if(urls.some(function(u){return /\/supertonic-sw\.js(?:\?|$)/.test(String(u));}))await r.unregister();
    }
  }catch(e){console.warn('Legacy Supertonic service-worker cleanup skipped',e);}
}
cleanupLegacyLocalSupertonic();
})();
