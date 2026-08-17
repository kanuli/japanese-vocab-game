(function(){
'use strict';
var ua=String(navigator.userAgent||'');
var touch=Number(navigator.maxTouchPoints||0);
var mobileUA=/Android|iPhone|iPod|Mobile|IEMobile|Opera Mini/i.test(ua);
var ipad=/iPad/i.test(ua)||(/Macintosh/i.test(ua)&&touch>1);
var mobile=mobileUA||ipad;
var memory=Number(navigator.deviceMemory||0)||null;
var localAllowed=!mobile;
function message(){return mobile?'此手機／平板不會載入約 400 MB 的本機 Supertonic 模型，以避免 WebAssembly 記憶體不足；會優先使用伺服器預錄音，必要時自動改用 VOICEVOX／裝置日語語音。':'Desktop：可使用本機 Supertonic 3；伺服器預錄仍會優先使用。';}
function isOomError(e){var s=String(e&&e.message||e||'');return /out of memory|RangeError|no available backend found/i.test(s);}
window.MobileSupertonicGuard={version:1,isMobile:mobile,localAllowed:localAllowed,deviceMemoryGB:memory,message:message,isOomError:isOomError};
function mark(){document.documentElement.dataset.mobileSupertonic=mobile?'hosted-only':'local-ok';}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mark,{once:true});else mark();
})();
