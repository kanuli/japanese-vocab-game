// Large-vocabulary loader invoked by advanced_words.js before the game initializes.
// Only accept the current teacher-audited prebuilt bundle. Never fall back to the old
// browser-side noisy thesaurus/Wikidict build path: if the audited bundle is missing,
// keep the already-loaded layers and surface a clear warning.
(function(){"use strict";
const REQUIRED="prebuilt-20260826-v9-teacher-audit";
const TEACHER_VERSION="20260826-teacher-v5-source-lineage";
const MIN=22000;
const prebuilt=window.ADVANCED_WORDS_BUNDLE_META;
if(prebuilt&&prebuilt.version===REQUIRED&&Number(prebuilt.generatedCount||prebuilt.loadedCount||0)>=MIN&&prebuilt.jlptRecalibration?.status==="complete"&&prebuilt.jlptRecalibration?.version===TEACHER_VERSION){
  window.ADVANCED_WORDS_META={...prebuilt,prebuilt:true,audited:true,teacherAudit:true,teacherAuditVersion:TEACHER_VERSION};
  return;
}
const msg=`⚠️ 日文老師審核詞庫／JLPT 校準資料未載入或版本不符（需要 ${REQUIRED} / ${TEACHER_VERSION} / ${MIN}+ 詞）。已停用舊式瀏覽器重建，避免重新引入同音、錯義或錯誤 N1 fallback。`;
console.error(msg,{prebuilt});
window.ADVANCED_WORDS_META={...(prebuilt||{}),prebuilt:false,audited:false,teacherAudit:false,error:"teacher-audited-jlpt-prebuilt-required"};
const x=document.getElementById("advStatus");if(x)x.textContent=msg;
})();
