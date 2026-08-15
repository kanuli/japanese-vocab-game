#!/usr/bin/env python3
from pathlib import Path
p=Path('listening.html')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'{label} anchor not found')
    s=s.replace(old,new,1)

# Four engine controls.
old='<div class="radios three" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked><label for="engineVoicevox">🎭 VOICEVOX<br>錄音題庫</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai"><label for="engineAI">✨ Supertonic<br>AI</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>語音</label></div></div>'
new='<div class="radios four" style="margin-bottom:9px"><div class="radio"><input id="engineVoicevox" name="audioEngine" type="radio" value="voicevox" checked><label for="engineVoicevox">🎭 VOICEVOX<br>伺服器錄音</label></div><div class="radio"><input id="engineAI" name="audioEngine" type="radio" value="ai"><label for="engineAI">✨ Supertonic 3<br>AI</label></div><div class="radio"><input id="engineAivis" name="audioEngine" type="radio" value="aivis"><label for="engineAivis">💠 AivisSpeech<br>Style-Bert-VITS</label></div><div class="radio"><input id="engineDevice" name="audioEngine" type="radio" value="device"><label for="engineDevice">🖥️ 裝置<br>備援</label></div></div>'
once(old,new,'engine radios')

# CSS for 4 engines.
once('.radios.three{grid-template-columns:repeat(3,1fr)}','.radios.three{grid-template-columns:repeat(3,1fr)}.radios.four{grid-template-columns:repeat(4,1fr)}','desktop four grid')
once('.radios.three{grid-template-columns:1fr}.answer-grid','.radios.three{grid-template-columns:1fr}.radios.four{grid-template-columns:1fr 1fr}.answer-grid','mobile four grid')

# Voice intro copy.
s=s.replace('VOICEVOX 以 GitHub Releases 為主來源，Hugging Face Dataset 為自動備援；兩者都不需學習者登入。Supertonic 與裝置語音作第二層備援。','VOICEVOX、Supertonic 3、AivisSpeech / Style-Bert-VITS 統一為三個主要日語引擎；伺服器錄音使用 GitHub Releases 主來源與 Hugging Face 備援，裝置日語只作最後備援。',1)

# Aivis panel between Supertonic and device.
anchor='''</div>\n<div id="devicePanel" style="display:none;margin-top:8px"><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div>'''
panel='''</div>\n<div id="aivisPanel" style="display:none">\n<div id="aivisStatus" class="notice" style="margin:0 0 8px">正在檢查 AivisSpeech / Style-Bert-VITS 伺服器聲線包…</div>\n<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">AivisSpeech / Style-Bert-VITS 聲線</label><select id="aivisVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">伺服器聲線包檢查中…</option></select></div>\n<div class="muted" style="margin-top:7px">音訊由伺服器預先生成；學習者不需安裝 AivisSpeech、不需本機 IP。未命中時自動改用 Supertonic 3。</div>\n</div>\n<div id="devicePanel" style="display:none;margin-top:8px"><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div>'''
once(anchor,panel,'aivis panel')

# Load hosted Aivis helper before the page IIFE.
once('<script>\n(()=>{"use strict";','<script src="./listening-aivis-hosted.js?v=20260815v1"></script>\n<script>\n(()=>{"use strict";','aivis helper script')

# Panel switcher.
old='async function syncAudioPanels(){const mode=$("input[name=audioEngine]:checked")?.value||"ai";$("#voicevoxPanel").style.display=mode==="voicevox"?"block":"none";$("#aiPanel").style.display=mode==="ai"?"block":"none";$("#devicePanel").style.display=mode==="device"?"block":"none";if(mode==="ai"&&!window.SupertonicAI?.isReady?.()){const info=await supertonicCacheInfo();if(info.ready)void enableAI(false)}}'
new='async function syncAudioPanels(){const mode=$("input[name=audioEngine]:checked")?.value||"ai";$("#voicevoxPanel").style.display=mode==="voicevox"?"block":"none";$("#aiPanel").style.display=mode==="ai"?"block":"none";$("#aivisPanel").style.display=mode==="aivis"?"block":"none";$("#devicePanel").style.display=mode==="device"?"block":"none";if(mode==="ai"&&!window.SupertonicAI?.isReady?.()){const info=await supertonicCacheInfo();if(info.ready)void enableAI(false)}}'
once(old,new,'syncAudioPanels')

# Stop external hosted player too.
once('function stopAllAudio(){try{speechSynthesis.cancel()}catch{}try{clearVoicevoxStop()}catch{}if(activeAiAudio){try{activeAiAudio.pause();activeAiAudio.currentTime=0}catch{}activeAiAudio=null}}','function stopAllAudio(){try{speechSynthesis.cancel()}catch{}try{clearVoicevoxStop()}catch{}try{window.ListeningAivisHosted?.stop?.()}catch{}if(activeAiAudio){try{activeAiAudio.pause();activeAiAudio.currentTime=0}catch{}activeAiAudio=null}}','stopAllAudio')

# Sample Aivis.
old='const sample="こんにちは。日本語の聴解練習を始めましょう。";if(mode==="ai")'
new='if(mode==="aivis"){const ok=await window.ListeningAivisHosted?.sample?.($("#aivisVoice")?.value||"random");if(ok){status.textContent="✅ AivisSpeech / Style-Bert-VITS 伺服器錄音試聽完成。";return}status.textContent="AivisSpeech 聲線包尚未完成，改用 Supertonic 3 試聽。"}const sample="こんにちは。日本語の聴解練習を始めましょう。";if(mode==="ai"||mode==="aivis")'
once(old,new,'sample aivis')

# Main Aivis playback before Supertonic branch.
old='if(mode==="ai"){const api=window.SupertonicAI;'
new='if(mode==="aivis"){try{const out=await window.ListeningAivisHosted?.speak?.(game.current.id,game.current.jp,rate,$("#aivisVoice")?.value||"random");if(out){unlockAfterPlay(`AivisSpeech / Style-Bert-VITS · ${out.label||out.key||"伺服器錄音"}`);return}}catch(e){console.warn(e)}$("#aivisStatus").textContent="⚠️ 此題暫無 AivisSpeech 伺服器錄音，已改用 Supertonic 3 備援。";}if(mode==="ai"||mode==="aivis"){const api=window.SupertonicAI;'
once(old,new,'main aivis')

# Standardize Supertonic 3 quality to 8 steps.
s=s.replace('totalSteps:5','totalSteps:8')

# Initialize Aivis catalog with other resources.
old='Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex(),initializeSupertonicPersistence()]).then(render);'
new='Promise.allSettled([loadWeb(),initFurigana(),loadVoicevoxIndex(),initializeSupertonicPersistence(),window.ListeningAivisHosted?.init?.($("#aivisVoice"),$("#aivisStatus"))]).then(render);'
once(old,new,'init aivis')

# Footer and copy.
s=s.replace('Supertonic 3 與裝置日語語音作第二層備援。','Supertonic 3、AivisSpeech / Style-Bert-VITS 與裝置日語備援共同組成多聲線播放系統。',1)
p.write_text(s,encoding='utf-8')
print('Listening multi-engine voice patch applied.')
