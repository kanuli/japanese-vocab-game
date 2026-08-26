// Stage 2 exact-form level corrections from manual secondary validation.
// These overrides apply ONLY where the Stage 1 level was a frequency-only estimate.
// They do not override direct Waller/Tomoshi community JLPT labels because no official
// post-2010 per-word JLPT list exists and third-party sources can legitimately differ.
(()=>{"use strict";
const O=new Map([
  ["ほてん|補填",{level:"N2",reason:"時雨/MOJi exact sense confirmed; Stage 1 level was frequency-only estimate"}],
  ["アップル|アップル",{level:"N5",reason:"時雨 exact fruit sense/read/level confirmed; Stage 1 level was frequency-only estimate"}]
]);
const rows=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];
let applied=0,eligible=0;
for(const w of rows){
  const reading=String(w?.reading||"").trim();
  const display=String(w?.kanji||w?.displayWord||reading).trim();
  const patch=O.get(`${reading}|${display}`);
  if(!patch)continue;
  eligible++;
  const src=String(w?.levelSource||"");
  if(!src.includes("frequency-estimate"))continue;
  w.level=patch.level;
  w.levelSource="manual-secondary-crosscheck-frequency-estimate";
  w.stage2LevelCrosscheck=true;
  w.stage2LevelReason=patch.reason;
  applied++;
}
window.VOCAB_STAGE2_LEVEL_OVERRIDE_META={
  version:"20260826-v1",
  configured:O.size,
  eligible,
  applied,
  policy:"Exact form+reading only; frequency-only estimates may be corrected from secondary manual validation; direct Waller/Tomoshi JLPT labels are never overwritten."
};
})();
