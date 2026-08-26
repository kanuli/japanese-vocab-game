// Large-vocabulary loader invoked by advanced_words.js before the game initializes.
// Only accept the current audited world-recalibrated prebuilt bundle. Never fall back
// to the old browser-side noisy thesaurus/Wikidict build path: if the audited bundle
// is missing, keep the already-loaded curated/core layers and surface a clear warning.
(function(){"use strict";
const REQUIRED="prebuilt-20260826-v7-world-jlpt";
// Full Tomoshi/JMdict evidence scan supports 22k advanced rows without entering the
// no-JLPT/no-common/no-frequency dictionary-only tail. JLPT levels are then rebuilt
// from direct world/community evidence plus calibrated residual estimates.
const MIN=22000;
const prebuilt=window.ADVANCED_WORDS_BUNDLE_META;
if(prebuilt&&prebuilt.version===REQUIRED&&Number(prebuilt.generatedCount||prebuilt.loadedCount||0)>=MIN&&prebuilt.jlptRecalibration?.status==="complete"){
  window.ADVANCED_WORDS_META={...prebuilt,prebuilt:true,audited:true};
  return;
}
const msg=`⚠️ 審核大型詞庫／JLPT 校準資料未載入或版本不符（需要 ${REQUIRED} / ${MIN}+ 詞）。已停用舊式瀏覽器重建，避免重新引入同音、錯義或錯誤 N1 fallback。`;
console.error(msg,{prebuilt});
window.ADVANCED_WORDS_META={...(prebuilt||{}),prebuilt:false,audited:false,error:"audited-world-jlpt-prebuilt-required"};
const x=document.getElementById("advStatus");if(x)x.textContent=msg;
})();