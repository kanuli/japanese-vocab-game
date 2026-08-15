#!/usr/bin/env python3
from pathlib import Path
hp=Path('wordlist.html');jp=Path('wordlist.js')
h=hp.read_text(encoding='utf-8');j=jp.read_text(encoding='utf-8')

h=h.replace('🔊 單字語音｜VOICEVOX / Supertonic</h2>','🔊 單字語音｜VOICEVOX / Supertonic 3 / AivisSpeech</h2>',1)
h=h.replace('正在檢查 Supertonic…','正在檢查 VOICEVOX / Supertonic 3 / AivisSpeech…',1)
h=h.replace('<script src="./wordlist-audio.js?v=3"></script><script src="./wordlist-voicevox.js?v=1"></script><script src="./wordlist.js?v=3"></script>','<script src="./wordlist-audio.js?v=4"></script><script src="./wordaudio-multivoice.js?v=20260815v2"></script><script src="./wordlist.js?v=4"></script>',1)

j=j.replace("function engine(){var e=document.getElementById('audioEngine');return e?e.value:'supertonic';}","function engine(){var e=document.getElementById('audioEngine');return e?e.value:'supertonic3';}")

old="""function setBusy(v){audioBusy=v;document.querySelectorAll('.play-btn').forEach(function(b){b.disabled=v;});var s=document.getElementById('sampleVoice');if(s)s.disabled=v;var vv=document.getElementById('voicevoxVoice');if(vv)vv.disabled=v||engine()!=='voicevox'||!(W.voicevoxAvailable&&W.voicevoxAvailable());}
async function speakWord(w){if(audioBusy)return;setBusy(true);var status=document.getElementById('audioStatus'),name=w.kanji||w.displayWord||w.reading;status.textContent='🔊 正在播放：'+name+'（'+w.reading+'）';try{if(engine()==='voicevox'){if(!W.speakVoicevox||!W.voicevoxAvailable||!W.voicevoxAvailable()){status.textContent='⏳ 43 聲線 VOICEVOX 單字資料庫仍在生成；暫時請選 Supertonic。';return;}var sel=document.getElementById('voicevoxVoice'),used=await W.speakVoicevox(w,sel&&sel.value);status.textContent=used?'✅ 已播放：'+name+'｜VOICEVOX '+used.speaker+'（'+used.style+'）':'⚠️ 此單字暫時沒有 VOICEVOX 預錄音。';}else{if(!W.speak){status.textContent='⚠️ Supertonic 模組尚未載入。';return;}var ai=await W.speak(w.reading);status.textContent=ai?'✅ 已播放：'+name+'｜Supertonic '+ai:'⚠️ Supertonic 尚未準備完成；可按「修復／重新安裝」再試。';}}catch(e){status.textContent='⚠️ 播放失敗：'+(e&&e.message?e.message:String(e));}finally{setBusy(false);}}"""
new="""function setBusy(v){audioBusy=v;document.querySelectorAll('.play-btn').forEach(function(b){b.disabled=v;});var s=document.getElementById('sampleVoice');if(s)s.disabled=v;var voice=document.getElementById('voice');if(voice)voice.disabled=v;var eng=document.getElementById('audioEngine');if(eng)eng.disabled=v;}
function engineLabel(e){return e==='voicevox'?'VOICEVOX':e==='aivis'?'AivisSpeech / Style-Bert-VITS':e==='device'?'裝置 Japanese voice':'Supertonic 3';}
async function speakWord(w){if(audioBusy)return;setBusy(true);var status=document.getElementById('audioStatus'),name=w.kanji||w.displayWord||w.reading;status.textContent='🔊 正在播放：'+name+'（'+w.reading+'）';try{if(!W.speak){status.textContent='⚠️ 多聲線模組尚未載入。';return;}var used=await W.speak(w.reading,w);status.textContent=used?'✅ 已播放：'+name+'｜'+engineLabel(engine()):'⚠️ 語音暫時無法播放。';}catch(e){status.textContent='⚠️ 播放失敗：'+(e&&e.message?e.message:String(e));}finally{setBusy(false);}}"""
if new not in j:
    if old not in j:raise SystemExit('speakWord anchor not found')
    j=j.replace(old,new,1)

start=j.find("document.getElementById('sampleVoice').onclick=async function()")
end=j.find("document.querySelectorAll('.level input')",start)
if start<0 or end<0:raise SystemExit('sample handler anchor not found')
sample="""document.getElementById('sampleVoice').onclick=async function(){if(audioBusy)return;setBusy(true);var st=document.getElementById('voiceStatus');try{var sample=(W.words||[]).find(function(w){return w.reading==='ありがとう';})||(W.words||[])[0];if(!sample)throw new Error('單字資料尚未載入');st.textContent='正在準備 '+engineLabel(engine())+' 試聽…';var used=await W.speak(sample.reading,sample);st.textContent=used?'✅ 試聽完成：'+engineLabel(engine())+'｜'+sample.reading:'⚠️ 試聽暫時無法播放。';}catch(e){st.textContent='⚠️ 試聽失敗：'+(e&&e.message?e.message:String(e));}finally{setBusy(false);}};
"""
j=j[:start]+sample+j[end:]

# Do not auto-force VOICEVOX merely because its catalog loaded; preserve the learner's selected engine.
j=j.replace("window.addEventListener('word-voicevox-ready',function(){var e=document.getElementById('audioEngine');if(e)e.value='voicevox';setBusy(false);});","")

hp.write_text(h,encoding='utf-8');jp.write_text(j,encoding='utf-8')
print('Word List now shares Word Audio multi-engine layer.')
