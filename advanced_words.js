// Load the curated supplement and validated repo-hosted expansion before the game initializes.
document.write('<script src="./advanced_words_curated.js?v=20260814v7"><\/script>');
document.write('<script src="./data/advanced_vocab.js?v=20260814v7"><\/script>');
document.write('<script src="./large_vocab_loader.js?v=20260814v7"><\/script>');

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
