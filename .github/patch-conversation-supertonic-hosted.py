from pathlib import Path
import re

p=Path('conversation.js')
s=p.read_text(encoding='utf-8')

s=s.replace("vst('Supertonic AI：10 種 AI 聲線；完整會話可讓 A / B 使用不同聲線。');","vst('Supertonic AI：10 種聲線；優先使用伺服器預錄，未就緒時才用瀏覽器即時生成。');",1)

# Remove the obsolete local VOICEVOX/Aivis API helper code completely.
s,n=re.subn(r"function canonicalSpeakers\(raw,limit\)\{.*?\n\}\nasync function connectApi\(engine\)\{.*?\n\}\n(?=async function ensureSuper)","",s,count=1,flags=re.S)
if n!=1:
    raise SystemExit('obsolete local connectApi block not found')

s=s.replace("vst(`✨ Supertonic 正在產生 ${role}｜${voice}…`,'loading');","vst(`✨ Supertonic 瀏覽器備援正在產生 ${role}｜${voice}…`,'loading');",1)
s=s.replace("await playAudioObject(out.url,token);vst(`✅ Supertonic ${voice} 播放完成。`,'ok');","await playAudioObject(out.url,token);vst(`✅ Supertonic ${voice}｜瀏覽器即時備援播放完成。`,'ok');",1)

s,n=re.subn(r"async function speakApi\(text,role,token,engine\)\{.*?\n\}\n(?=async function speakDevice)","",s,count=1,flags=re.S)
if n!=1:
    raise SystemExit('obsolete speakApi block not found')

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
  if(token!==S.stopToken)return;
  if(used)return;
  vst('Supertonic 此句的伺服器預錄暫不可用，已自動使用瀏覽器即時備援。','loading');
  return speakSuper(text,role,token);
 }
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
if old not in s:
    raise SystemExit('speak block not found')
s=s.replace(old,new,1)

old="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic')populateSupertonic();
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}"""
new="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic'){
  populateSupertonic();
  if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
 }
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}"""
if old not in s:
    raise SystemExit('engineChanged block not found')
s=s.replace(old,new,1)

old="populateSupertonic();loadSystemVoices();if('speechSynthesis'in window)speechSynthesis.onvoiceschanged=loadSystemVoices;"
new="populateSupertonic();if(window.ConversationHostedAudio?.configure)void window.ConversationHostedAudio.configure('supertonic',$('#voiceA'),$('#voiceB'),vst);loadSystemVoices();if('speechSynthesis'in window)speechSynthesis.onvoiceschanged=loadSystemVoices;"
if old not in s:
    raise SystemExit('init voice bootstrap not found')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')

h=Path('conversation.html')
s=h.read_text(encoding='utf-8')
s=s.replace('✨ Supertonic AI｜瀏覽器即時生成','✨ Supertonic AI｜10 聲線伺服器預錄 + 瀏覽器備援')
s=s.replace('VOICEVOX 直接使用本站 GitHub Releases / Hugging Face 公開錄音，不需要本機 IP。AivisSpeech 沒有伺服器錄音時會自動使用 Supertonic 備援。','Supertonic 10 聲線與 VOICEVOX 43 聲線都使用本站伺服器預錄（GitHub Releases 主來源、Hugging Face 備援），不需要本機 IP。AivisSpeech 伺服器庫準備中，未有錄音時自動使用 Supertonic。')
s=s.replace('日本語・場面別會話 v1.1｜繁體中文解釋｜Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。VOICEVOX 使用本站伺服器錄音（GitHub Releases 主來源、Hugging Face 備援），不需要本機 VOICEVOX 或 IP；AivisSpeech 若無本站錄音會自動切換 Supertonic。','日本語・場面別會話 v1.2｜繁體中文解釋｜Supertonic 10 聲線與 VOICEVOX 43 聲線使用伺服器預錄（GitHub Releases 主來源、Hugging Face 備援）；Supertonic 保留瀏覽器即時生成作備援；AivisSpeech 伺服器錄音庫準備中。所有模式都不需要連接本機 TTS IP。')
s=s.replace('./conversation-hosted-audio.js?v=20260814v1','./conversation-hosted-audio.js?v=20260815v2')
s=s.replace('./conversation.js?v=20260814v2','./conversation.js?v=20260815v3')
h.write_text(s,encoding='utf-8')
