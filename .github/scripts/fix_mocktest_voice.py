from pathlib import Path
import re

js = Path('mocktest.js')
html = Path('mocktest.html')
s = js.read_text(encoding='utf-8')
h = html.read_text(encoding='utf-8')

# Mock exam must use one consistent formal Japanese voice only.
# Remove the VOICEVOX index fetch from the mock page; Listening Game remains unchanged.
s = re.sub(r'try\{const r=await fetch\("\./voicevox-release-index\.json",\{cache:"no-cache"\}\);if\(r\.ok\)\{const d=await r\.json\(\);if\(d\?\.items\)voicevoxIndex=d\}\}catch\{\}', '', s, count=1)

start = s.find('function recUrls(rec)')
end = s.find('function rawStats()', start)
if start < 0 or end < 0:
    raise SystemExit('mock audio block not found')

new_audio = r'''let mockExamVoice=null;
function chooseMockExamVoice(){
  if(mockExamVoice)return mockExamVoice;
  if(!("speechSynthesis" in window))return null;
  const vs=speechSynthesis.getVoices().filter(v=>/^ja(?:-|_)/i.test(v.lang)||/Japanese|日本語/i.test(v.name));
  const preferred=[/Kyoko/i,/Nanami/i,/Haruka/i,/Google.*日本語/i,/Google.*Japanese/i,/Microsoft.*Japanese/i,/Japanese/i];
  for(const pat of preferred){const v=vs.find(x=>pat.test(x.name));if(v){mockExamVoice=v;break}}
  mockExamVoice=mockExamVoice||vs.find(v=>/^ja-JP$/i.test(v.lang))||vs[0]||null;
  return mockExamVoice;
}
function prepareMockExamVoice(){
  chooseMockExamVoice();
  if("speechSynthesis" in window&&"onvoiceschanged" in speechSynthesis){
    speechSynthesis.onvoiceschanged=()=>{if(!mockExamVoice)chooseMockExamVoice()};
  }
}
function speakMockExam(text){return new Promise((resolve,reject)=>{
  if(!("speechSynthesis" in window))return reject(Error("no speech"));
  const u=new SpeechSynthesisUtterance(text);
  u.lang="ja-JP";
  u.rate=.91;
  u.pitch=1.0;
  u.volume=1.0;
  const v=chooseMockExamVoice();
  if(v)u.voice=v;
  u.onend=resolve;
  u.onerror=reject;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
})}
async function playAudio(){const q=question();if(q.audioPlayed)return;q.audioPlayed=true;$("#playAudio").disabled=true;$("#listenStatus").textContent="播放中（模擬試驗固定聲線）…";try{await speakMockExam(q.audioText);$("#listenStatus").textContent="播放完畢（本題不能重播）"}catch{$("#listenStatus").textContent="語音播放失敗；此題可再次嘗試";q.audioPlayed=false;$("#playAudio").disabled=false}}
'''
s = s[:start] + new_audio + s[end:]

# Initialize voice once for the entire mock exam session.
if 'prepareMockExamVoice();' not in s:
    marker='loadAll();\n})();'
    if marker not in s:
        raise SystemExit('initialization marker not found')
    s=s.replace(marker,'prepareMockExamVoice();\nloadAll();\n})();',1)

# Update learner-facing copy: fixed formal voice, separate from Listening Game.
h = h.replace('聽解題只播放一次，回答後不能在考試中重播。VOICEVOX 有相符預錄句子時優先使用；否則使用日語裝置語音。','聽解題只播放一次，回答後不能在考試中重播。模擬試驗固定使用同一種中性、正式、清晰的日語聲線與固定語速，不會像聽解學習模式一樣切換角色或聲線。')
h = re.sub(r'mocktest\.js\?v=[^"\s<]+','mocktest.js?v=20260813-fixedvoice1',h)

js.write_text(s,encoding='utf-8')
html.write_text(h,encoding='utf-8')
print('Applied fixed JLPT-style mock exam voice')
