// Normalize only the known legacy curated shape where reading/kanji were reversed.
// This runs before the exact-key teacher overlay so display+reading matching is reliable.
(()=>{'use strict';
const A=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];
const hasKanji=s=>/[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]/.test(String(s||''));
const isKana=s=>!!String(s||'').trim()&&/^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$/.test(String(s||'').replace(/\s+/g,''));
let correctedRows=0;
for(const w of A){
  const reading=String(w?.reading||'').trim();
  const kanji=String(w?.kanji||'').trim();
  if(hasKanji(reading)&&isKana(kanji)){
    w.reading=kanji;
    w.kanji=reading;
    w.displayWord=reading;
    correctedRows++;
  }
}
window.ADVANCED_WORDS_FIELD_NORMALIZER_META={version:'20260826-v1-curated-field-order',correctedRows};
})();
