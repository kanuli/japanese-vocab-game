// Stage 2 exact-form level corrections and conservative JLPT re-estimation.
// Policy: N1 is never used as the catch-all bucket for missing/rare frequency data.
// Direct Waller/Tomoshi/community JLPT labels remain authoritative unless an exact
// manually cross-checked written-form+reading override exists.
(()=>{"use strict";
const O=new Map([
  ["ほてん|補填",{level:"N2",reason:"secondary exact-form cross-check"}],
  ["アップル|アップル",{level:"N5",reason:"secondary exact-form cross-check"}],
  ["すいか|西瓜",{level:"N5",reason:"時雨 exact entry explicitly labels 西瓜（すいか） N5; common beginner food vocabulary"}]
]);
const rows=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];
let exactApplied=0,frequencyN1Reclassified=0,frequencyEstimated=0;
for(const w of rows){
  const reading=String(w?.reading||"").trim();
  const display=String(w?.kanji||w?.displayWord||reading).trim();
  const key=`${reading}|${display}`;
  const src=String(w?.levelSource||"");
  const patch=O.get(key);
  if(patch){
    // Exact written-form+reading evidence may override any estimated level.
    if(src.includes("frequency-estimate")||src.includes("estimated")||!src){
      w.level=patch.level;
      w.levelSource="manual-secondary-crosscheck-exact";
      w.stage2LevelCrosscheck=true;
      w.stage2LevelReason=patch.reason;
      exactApplied++;
      continue;
    }
  }
  // The previous estimator mapped every rank > 8000, including rank=999999
  // (meaning frequency unavailable), to N1. That made N1 a garbage bucket.
  // Keep N5-N2 frequency bands, but never infer N1 from frequency absence/rarity alone.
  if(src.includes("frequency-estimate")){
    frequencyEstimated++;
    if(String(w.level).toUpperCase()==="N1"){
      w.level="N2";
      w.levelSource="frequency-estimate-conservative-N2";
      w.stage2LevelReestimated=true;
      w.stage2LevelReason="No direct N1 evidence; frequency rank/absence alone cannot justify N1";
      frequencyN1Reclassified++;
    }
  }
}
window.VOCAB_STAGE2_LEVEL_OVERRIDE_META={
  version:"20260826-v2-jlpt-recalibrated",
  configuredExact:O.size,
  exactApplied,
  frequencyEstimated,
  frequencyN1Reclassified,
  policy:"Evidence-first JLPT classification. Direct JLPT evidence is preserved. Exact secondary cross-checks may correct exact written-form+reading pairs. Frequency-only N1 is prohibited; missing/rare frequency is not N1 evidence."
};
})();
