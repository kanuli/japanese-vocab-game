#!/usr/bin/env python3
from pathlib import Path
p=Path('translator.html'); s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    if new in s:return
    if old not in s:raise SystemExit(label+' anchor not found')
    s=s.replace(old,new,1)

s=s.replace('.settings{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px', '.settings{display:grid;grid-template-columns:1.05fr 1.2fr 1fr 1fr;gap:10px',1)
s=s.replace('<button id="ai" class="btn good">✨ AI 日語發音</button>','<button id="ai" class="btn good">▶ 日語發音</button>',1)
old='<div class="settings"><div class="field"><label>Supertonic AI 聲線</label><select id="voice">'
new='<div class="settings"><div class="field"><label>日語語音來源</label><select id="engine"><option value="supertonic3" selected>✨ Supertonic 3｜即時生成</option><option value="voicevox">🎭 VOICEVOX｜本站預錄</option><option value="aivis">💠 AivisSpeech / Style-Bert-VITS｜本站預錄</option></select></div><div class="field"><label id="voiceLabel">Supertonic 3 聲線</label><select id="voice">'
once(old,new,'settings engine')
s=s.replace('<div class="field"><label>AI / 裝置播放速度</label>','<div class="field"><label>日語播放速度</label>',1)
s=s.replace('不需要私人 API key。日語優先使用本站現有的 Supertonic AI 即時語音；裝置 Speech Synthesis 作備援。','不需要私人 API key。日語可選 VOICEVOX、Supertonic 3、AivisSpeech / Style-Bert-VITS；已收錄句子優先使用本站伺服器預錄，任意新句由 Supertonic 3 即時生成，裝置 Speech Synthesis 作最後備援。',1)

once("</div><div class=\"footer\">Japanese Learning｜語音・翻譯練習工具</div></div>\n<script>","</div><div class=\"footer\">Japanese Learning｜語音・翻譯練習工具</div></div>\n<script src=\"./translator-hosted-voice.js?v=20260815v1\"></script>\n<script>",'helper script')

# Capture original Supertonic voice options.
once("(()=>{'use strict';const $=s=>document.querySelector(s),jp=$('#jp'),zh=$('#zh'),en=$('#en'),status=$('#status');let voices=[],audio=null;","(()=>{'use strict';const $=s=>document.querySelector(s),jp=$('#jp'),zh=$('#zh'),en=$('#en'),status=$('#status');let voices=[],audio=null;const st3VoiceOptions=$('#voice').innerHTML;",'capture voices')

s=s.replace('Supertonic AI 暫時無法載入，可使用裝置日語語音。','Supertonic 3 暫時無法載入，可使用裝置日語語音。')
s=s.replace('totalSteps:5','totalSteps:8')

old="""async function speakAI(){let t=jp.value.trim();if(!t){st('請先輸入日文句子。','bad');return}stop();if(!await ensureAI())return;try{let v=$('#voice').value;if(v==='random'){let a=['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];v=a[Math.floor(Math.random()*a.length)]}let rate=Number($('#rate').value);st(`✨ 正在產生 AI 日語語音（${v}）…`,'loading');let out=await window.SupertonicAI.synthesize(t,{voice:v,speed:rate,totalSteps:8});audio=new Audio(out.url);audio.onended=()=>{audio=null;st('✅ AI 日語發音完成。','ok')};await audio.play();st(`✨ 正在播放 AI 日語（${v}）。`)}catch(e){console.error(e);st('AI 語音產生失敗，可改用裝置日語語音。','bad')}}
function stop(){if(audio){try{audio.pause();audio.currentTime=0}catch(e){}audio=null}if('speechSynthesis'in window)speechSynthesis.cancel()}"""
new="""async function speakSupertonic3(t,rate){if(!await ensureAI())return false;try{let v=$('#voice').value;if(!/^([FM][1-5]|random)$/.test(v))v='F3';if(v==='random'){let a=['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];v=a[Math.floor(Math.random()*a.length)]}st(`✨ Supertonic 3 正在產生日語語音（${v}）…`,'loading');let out=await window.SupertonicAI.synthesize(t,{voice:v,speed:rate,totalSteps:8});audio=new Audio(out.url);audio.onended=()=>{audio=null;st('✅ Supertonic 3 日語發音完成。','ok')};await audio.play();st(`✨ 正在播放 Supertonic 3（${v}）。`);return true}catch(e){console.error(e);st('Supertonic 3 語音產生失敗，可改用裝置日語語音。','bad');return false}}
async function speakAI(){let t=jp.value.trim();if(!t){st('請先輸入日文句子。','bad');return}stop();let rate=Number($('#rate').value),eng=$('#engine').value;if(eng==='voicevox'||eng==='aivis'){try{let out=await window.TranslatorHostedVoice?.speak?.(eng,t,rate,$('#voice').value);if(out){st('✅ '+out.label+' 已播放。','ok');return}}catch(e){console.warn(e)}st((eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS')+' 沒有這個任意新句的本站預錄，改用 Supertonic 3 即時生成。','loading')}await speakSupertonic3(t,rate)}
function stop(){if(audio){try{audio.pause();audio.currentTime=0}catch(e){}audio=null}try{window.TranslatorHostedVoice?.stop?.()}catch(e){}if('speechSynthesis'in window)speechSynthesis.cancel()}
async function syncEngine(){let eng=$('#engine').value,v=$('#voice'),lab=$('#voiceLabel');stop();if(eng==='supertonic3'){v.disabled=false;v.innerHTML=st3VoiceOptions;v.value='F3';lab.textContent='Supertonic 3 聲線';st('Supertonic 3：可即時產生任何輸入的日語句子。');return}lab.textContent=eng==='voicevox'?'VOICEVOX 聲線':'AivisSpeech / Style-Bert-VITS 聲線';await window.TranslatorHostedVoice?.configure?.(eng,v,t=>st(t));}"""
if new not in s:
    if old not in s:raise SystemExit('speak block anchor not found')
    s=s.replace(old,new,1)

# Add engine change + initial sync at end.
old_end="$('#rate').oninput=e=>$('#ratev').textContent=Number(e.target.value).toFixed(2)+'×';jp.oninput=()=>$('#counter').textContent=jp.value.length+' 字';jp.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();translate()}};if('speechSynthesis'in window){loadvoices();speechSynthesis.onvoiceschanged=loadvoices}"
new_end="$('#rate').oninput=e=>$('#ratev').textContent=Number(e.target.value).toFixed(2)+'×';$('#engine').onchange=syncEngine;jp.oninput=()=>$('#counter').textContent=jp.value.length+' 字';jp.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();translate()}};if('speechSynthesis'in window){loadvoices();speechSynthesis.onvoiceschanged=loadvoices}syncEngine();"
once(old_end,new_end,'end handlers')

p.write_text(s,encoding='utf-8');print('Translator multi-engine patch applied.')
