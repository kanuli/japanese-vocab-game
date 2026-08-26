// Large-vocabulary loader invoked by advanced_words.js before the game initializes.
// Only accept the current audited Stage 1 prebuilt bundle. Never fall back to the old
// browser-side noisy thesaurus/Wikidict build path: if the audited bundle is missing,
// keep the already-loaded curated/core layers and surface a clear warning instead.
(function(){"use strict";
const REQUIRED="prebuilt-20260826-v6-expanded-stage12";
const MIN=30000;
const prebuilt=window.ADVANCED_WORDS_BUNDLE_META;
if(prebuilt&&prebuilt.version===REQUIRED&&Number(prebuilt.generatedCount||prebuilt.loadedCount||0)>=MIN){
  window.ADVANCED_WORDS_META={...prebuilt,prebuilt:true,audited:true};
  return;
}
const msg=`⚠️ 審核大型詞庫未載入或版本不符（需要 ${REQUIRED} / ${MIN}+ 詞）。已停用舊式瀏覽器重建，避免重新引入同音／錯義污染。`;
console.error(msg,{prebuilt});
window.ADVANCED_WORDS_META={...(prebuilt||{}),prebuilt:false,audited:false,error:"audited-prebuilt-required"};
const x=document.getElementById("advStatus");if(x)x.textContent=msg;
})();
