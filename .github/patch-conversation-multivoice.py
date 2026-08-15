#!/usr/bin/env python3
from pathlib import Path
import re

hp=Path('conversation.html'); jp=Path('conversation.js'); ap=Path('conversation-hosted-audio.js')
h=hp.read_text(encoding='utf-8'); j=jp.read_text(encoding='utf-8'); a=ap.read_text(encoding='utf-8')

# Furigana regression: keep exactly one switch.
fur='<label class="switch"><input id="showFurigana" type="checkbox" checked> 漢字顯示ふりがな</label>\n'
while h.count(fur)>1:
    pos=h.find(fur,h.find(fur)+len(fur))
    h=h[:pos]+h[pos+len(fur):]

h=h.replace('✨ Supertonic AI｜瀏覽器即時生成','✨ Supertonic 3｜伺服器預錄 / 瀏覽器備援')
h=h.replace('💠 AivisSpeech｜伺服器音訊 / 自動備援','💠 AivisSpeech / Style-Bert-VITS｜伺服器預錄')
h=h.replace('AivisSpeech 沒有伺服器錄音時會自動使用 Supertonic 備援。','AivisSpeech / Style-Bert-VITS 或其他伺服器錄音未命中時會自動使用 Supertonic 3 備援。')
h=h.replace('Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。','Supertonic 3、VOICEVOX、AivisSpeech / Style-Bert-VITS、裝置日語語音。')
h=h.replace('AivisSpeech 若無本站錄音會自動切換 Supertonic。','AivisSpeech / Style-Bert-VITS 若無本站錄音會自動切換 Supertonic 3。')

# Remove unreachable legacy local-API code completely.
if 'function canonicalSpeakers(raw,limit){' in j:
    start=j.index('function canonicalSpeakers(raw,limit){')
    end=j.index('async function ensureSuper(){',start)
    j=j[:start]+j[end:]
if 'async function speakApi(text,role,token,engine){' in j:
    start=j.index('async function speakApi(text,role,token,engine){')
    end=j.index('async function speakDevice(text,role,token){',start)
    j=j[:start]+j[end:]

j=j.replace("vst('Supertonic AI：10 種 AI 聲線；完整會話可讓 A / B 使用不同聲線。');","vst('Supertonic 3：10 種 F1–F5 / M1–M5 聲線；優先使用本站伺服器預錄，缺漏時瀏覽器即時生成。');")
j=j.replace("vst('✅ Supertonic AI 日語語音已準備。','ok')","vst('✅ Supertonic 3 日語語音已準備。','ok')")
j=j.replace("vst('⚠️ Supertonic 無法載入，可切換到裝置日語。','bad')","vst('⚠️ Supertonic 3 無法載入，可切換到裝置日語。','bad')")
j=j.replace('totalSteps:5','totalSteps:8')

old="""async function speak(text,role,token){
 const eng=$('#engine').value;
 if(eng==='supertonic')return speakSuper(text,role,token);
 if(eng==='voicevox'||eng==='aivis'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;
  if(used)return;
  vst(`${eng==='voicevox'?'VOICEVOX':'AivisSpeech'} 此句沒有本站預錄音，已自動使用 Supertonic 備援。`,'loading');
  return speakSuper(text,role,token,role==='B'?'M3':'F3');
 }
 return speakDevice(text,role,token);
}"""
new="""async function speak(text,role,token){
 const eng=$('#engine').value;
 if(eng==='supertonic'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;if(used)return;
  vst('Supertonic 3 此句暫無本站預錄音，改用瀏覽器即時生成。','loading');
  return speakSuper(text,role,token);
 }
 if(eng==='voicevox'||eng==='aivis'){
  let used=false;
  try{used=await window.ConversationHostedAudio?.speak?.(text,role,Number($('#speed').value))||false}catch(e){console.warn(e)}
  if(token!==S.stopToken)return;
  if(used)return;
  vst(`${eng==='voicevox'?'VOICEVOX':'AivisSpeech / Style-Bert-VITS'} 此句沒有本站預錄音，已自動使用 Supertonic 3 備援。`,'loading');
  return speakSuper(text,role,token,role==='B'?'M3':'F3');
 }
 return speakDevice(text,role,token);
}"""
if new not in j:
    if old not in j: raise SystemExit('speak block anchor not found')
    j=j.replace(old,new,1)

old2="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic')populateSupertonic();
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}"""
new2="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic'){populateSupertonic();if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);}
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}"""
if new2 not in j:
    if old2 not in j: raise SystemExit('engineChanged anchor not found')
    j=j.replace(old2,new2,1)

# Hosted layer naming and Style-Bert-VITS label.
a=a.replace('Supertonic hosted index incomplete','Supertonic 3 hosted index incomplete')
a=a.replace('Hosted Supertonic unavailable','Hosted Supertonic 3 unavailable')
a=a.replace('Supertonic 10 聲線伺服器錄音庫','Supertonic 3 10 聲線伺服器錄音庫')
a=a.replace('✅ Supertonic：','✅ Supertonic 3：')
a=a.replace('Supertonic 伺服器錄音庫正在建立；目前會自動使用瀏覽器即時 Supertonic。','Supertonic 3 伺服器錄音庫正在建立；目前會自動使用瀏覽器即時 Supertonic 3。')
a=a.replace('網站的 AivisSpeech 錄音庫','網站的 AivisSpeech / Style-Bert-VITS 錄音庫')
a=a.replace('每句隨機 AivisSpeech 聲線','每句隨機 AivisSpeech / Style-Bert-VITS 聲線')
a=a.replace('✅ AivisSpeech：','✅ AivisSpeech / Style-Bert-VITS：')
a=a.replace('AivisSpeech 伺服器錄音庫正在準備','AivisSpeech / Style-Bert-VITS 伺服器錄音庫正在準備')
a=a.replace('自動使用 Supertonic 備援','自動使用 Supertonic 3 備援')
a=a.replace('播放時自動使用 Supertonic。','播放時自動使用 Supertonic 3。')
a=a.replace('✅ Supertonic ${voice.label||key}','✅ Supertonic 3 ${voice.label||key}')
a=a.replace('✅ AivisSpeech ${d.speakers[key]?.speaker||key}','✅ AivisSpeech / Style-Bert-VITS ${d.speakers[key]?.speaker||key}')

hp.write_text(h,encoding='utf-8'); jp.write_text(j,encoding='utf-8'); ap.write_text(a,encoding='utf-8')
print('Conversation voice cleanup applied; furigana switch count:',h.count('id="showFurigana"'))
