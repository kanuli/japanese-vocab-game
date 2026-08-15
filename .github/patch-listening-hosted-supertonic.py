#!/usr/bin/env python3
from pathlib import Path
p=Path('listening.html');s=p.read_text(encoding='utf-8')

def once(old,new,label):
 global s
 if new in s:return
 if old not in s:raise SystemExit(label+' anchor not found')
 s=s.replace(old,new,1)

# Add hosted status above the existing local-model status.
once('<div id="aiStatus" class="notice" style="margin:0 0 8px">','<div id="aiHostedStatus" class="notice" style="margin:0 0 8px">正在檢查 Supertonic 3 伺服器預錄庫…</div>\n<div id="aiStatus" class="notice" style="margin:0 0 8px">','AI hosted status')
# Load both hosted helpers.
once('<script src="./listening-aivis-hosted.js?v=20260815v1"></script>','<script src="./listening-supertonic-hosted.js?v=20260815v1"></script>\n<script src="./listening-aivis-hosted.js?v=20260815v2"></script>','hosted scripts')
# Stop both hosted engines.
once('function stopAllAudio(){try{speechSynthesis.cancel()}catch{}try{clearVoicevoxStop()}catch{}try{window.ListeningAivisHosted?.stop?.()}catch{}if(activeAiAudio)','function stopAllAudio(){try{speechSynthesis.cancel()}catch{}try{clearVoicevoxStop()}catch{}try{window.ListeningAivisHosted?.stop?.()}catch{}try{window.ListeningSupertonicHosted?.stop?.()}catch{}if(activeAiAudio)','stop hosted')
# Setup sample: prefer server Supertonic 3 if ready.
old='const sample="こんにちは。日本語の聴解練習を始めましょう。";if(mode==="ai"||mode==="aivis"){'
new='if(mode==="ai"){const hosted=await window.ListeningSupertonicHosted?.sample?.($("#aiVoice")?.value||"F1");if(hosted){status.textContent=`✅ 試聽：Supertonic 3 伺服器預錄 · ${hosted.label||hosted.key}`;return}}const sample="こんにちは。日本語の聴解練習を始めましょう。";if(mode==="ai"||mode==="aivis"){'
once(old,new,'setup sample')
# Main playback: prefer hosted before browser synthesis for AI mode.
old='if(mode==="aivis"){try{const out=await window.ListeningAivisHosted?.speak?.(game.current.id,game.current.jp,rate,$("#aivisVoice")?.value||"random");if(out){unlockAfterPlay(`AivisSpeech / Style-Bert-VITS · ${out.label||out.key||"伺服器錄音"}`);return}}catch(e){console.warn(e)}$("#aivisStatus").textContent="⚠️ 此題暫無 AivisSpeech 伺服器錄音，已改用 Supertonic 3 備援。";}if(mode==="ai"||mode==="aivis"){'
new='if(mode==="aivis"){try{const out=await window.ListeningAivisHosted?.speak?.(game.current.id,game.current.jp,rate,$("#aivisVoice")?.value||"random");if(out){unlockAfterPlay(`AivisSpeech / Style-Bert-VITS · ${out.label||out.key||"伺服器錄音"}`);return}}catch(e){console.warn(e)}$("#aivisStatus").textContent="⚠️ 此題暫無 AivisSpeech 伺服器錄音，已改用 Supertonic 3 備援。";}if(mode==="ai"){try{const hosted=await window.ListeningSupertonicHosted?.speak?.(game.current.id,rate,selectedAiVoice());if(hosted){unlockAfterPlay(`Supertonic 3 · 伺服器預錄 · ${hosted.label||hosted.key}`);return}}catch(e){console.warn(e)}}if(mode==="ai"||mode==="aivis"){'
once(old,new,'main hosted AI')
# Initialize hosted Supertonic together with other resources.
old='window.ListeningAivisHosted?.init?.($("#aivisVoice"),$("#aivisStatus"))'
new='window.ListeningAivisHosted?.init?.($("#aivisVoice"),$("#aivisStatus")),window.ListeningSupertonicHosted?.init?.($("#aiHostedStatus"))'
once(old,new,'hosted init')

p.write_text(s,encoding='utf-8');print('Listening hosted Supertonic patch applied.')
