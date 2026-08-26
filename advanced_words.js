// Load the curated supplement and validated repo-hosted expansion before the game initializes.
document.write('<script src="./advanced_words_curated.js?v=20260821v1"><\/script>');
// Full-database audit outputs. Load the core overlay before any page fetches notes.csv,
// then apply conservative secondary dictionary cross-checks to exact ambiguous keys.
document.write('<script src="./data/vocab_core_verified.js?v=20260826v1"><\/script>');
document.write('<script src="./data/vocab_external_crosscheck.js?v=20260826v2"><\/script>');
document.write('<script src="./core_vocab_fetch_patch.js?v=20260826v2"><\/script>');
document.write('<script src="./data/advanced_vocab.js?v=20260826v1"><\/script>');
// Strict surface-form completion layer: the 185 direct-reviewed forms that were
// previously deferred only because the automatic sources had no reliable TC meaning.
document.write('<script src="./data/coverage_deferred_manual.js?v=20260821v1"><\/script>');
// Source-check completion layer: 66 additional approved exact written-form + reading
// pairs whose Traditional-Chinese meanings were manually resolved after the full
// automated source scan. This is loaded synchronously so every vocabulary consumer
// (quiz, word list, and word audio) sees the same completed runtime inventory.
document.write('<script src="./data/coverage_sourcecheck_manual.js?v=20260821v1"><\/script>');
// Final residual cleanup discovered by the post-completion strict audit.
document.write('<script src="./data/coverage_postreview_manual.js?v=20260821v1"><\/script>');
document.write('<script src="./large_vocab_loader.js?v=20260821v1"><\/script>');
// Direct-reviewed common words that must remain present even if an upstream deck changes.
document.write('<script src="./data/vocab_common_fixups.js?v=20260825v2"><\/script>');
// Hosted-audio delta overlay. It waits for wordaudio-multivoice.js before installing,
// so non-audio vocabulary pages simply ignore it.
document.write('<script src="./wordaudio-delta-voices.js?v=20260821v1"><\/script>');

// Pronunciation fix: always speak the explicit kana reading shown in the answer sheet.
// This prevents browser TTS from guessing an incorrect reading from kanji such as 白粉（おしろい）.
document.addEventListener("click",function(event){
  const button=event.target.closest?.("#speak");
  if(!button)return;
  const reading=document.querySelector("#aReading")?.textContent?.trim();
  if(!reading||!("speechSynthesis" in window))return;
  event.preventDefault();
  event.stopImmediatePropagation();
  speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(reading);
  utterance.lang="ja-JP";
  utterance.rate=.85;
  const japaneseVoice=speechSynthesis.getVoices().find(v=>/^ja(?:-|_)/i.test(v.lang));
  if(japaneseVoice)utterance.voice=japaneseVoice;
  speechSynthesis.speak(utterance);
},true);