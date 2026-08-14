from pathlib import Path

html=Path('conversation.html')
s=html.read_text(encoding='utf-8')
s=s.replace('<option value="voicevox">🎭 VOICEVOX｜最多 43 位標準角色</option>','<option value="voicevox">🎭 VOICEVOX｜43 聲線伺服器錄音</option>')
s=s.replace('<option value="aivis">💠 AivisSpeech｜VOICEVOX 相容 API</option>','<option value="aivis">💠 AivisSpeech｜伺服器音訊 / 自動備援</option>')
start=s.find('<details class="advanced"><summary>VOICEVOX / AivisSpeech 連線設定</summary>')
if start!=-1:
    end=s.find('</details>',start)
    if end==-1: raise SystemExit('connection details end not found')
    s=s[:start]+s[end+10:]
s=s.replace('Supertonic 會在第一次播放時載入。若 AI 語音不可用，仍可切換到裝置日語語音。','VOICEVOX 直接使用本站 GitHub Releases / Hugging Face 公開錄音，不需要本機 IP。AivisSpeech 沒有伺服器錄音時會自動使用 Supertonic 備援。')
s=s.replace('日本語・場面別會話 v1｜繁體中文解釋｜Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。VOICEVOX / AivisSpeech 本機 API 需在使用者裝置啟動相應引擎；Supertonic 與裝置語音可直接在支援的瀏覽器使用。','日本語・場面別會話 v1.1｜繁體中文解釋｜Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。VOICEVOX 使用本站伺服器錄音（GitHub Releases 主來源、Hugging Face 備援），不需要本機 VOICEVOX 或 IP；AivisSpeech 若無本站錄音會自動切換 Supertonic。')
s=s.replace('<script src="./conversation.js?v=20260814v1"></script>','<script src="./conversation-hosted-audio.js?v=20260814v1"></script>\n<script src="./conversation.js?v=20260814v2"></script>')
html.write_text(s,encoding='utf-8')

js=Path('conversation.js')
s=js.read_text(encoding='utf-8')
s=s.replace(" if('speechSynthesis'in window) speechSynthesis.cancel();\n}"," if('speechSynthesis'in window) speechSynthesis.cancel();\n if(window.ConversationHostedAudio?.stop)window.ConversationHostedAudio.stop();\n}",1)
s=s.replace(" }catch(e){vst('⚠️ Supertonic 無法載入，可切換到裝置日語或本機 VOICEVOX。','bad');return false}"," }catch(e){vst('⚠️ Supertonic 無法載入，可切換到裝置日語。','bad');return false}",1)
s=s.replace("async function speakSuper(text,role,token){\n if(!await ensureSuper())throw Error('Supertonic unavailable');if(token!==S.stopToken)return;\n const voice=selectedVoice(role)||'F3',speed=Number($('#speed').value);", "async function speakSuper(text,role,token,voiceOverride=null){\n if(!await ensureSuper())throw Error('Supertonic unavailable');if(token!==S.stopToken)return;\n const voice=voiceOverride||selectedVoice(role)||'F3',speed=Number($('#speed').value);",1)
old="""async function speak(text,role,token){
 const eng=$('#engine').value;
 if(eng==='supertonic')return speakSuper(text,role,token);
 if(eng==='voicevox'||eng==='aivis')return speakApi(text,role,token,eng);
 return speakDevice(text,role,token);
}"""
new="""async function speak(text,role,token){
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
if old not in s: raise SystemExit('speak block not found')
s=s.replace(old,new,1)
old="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic')populateSupertonic();
 else if(e==='device')populateDevice();
 else await connectApi(e);
}"""
new="""async function engineChanged(){
 stop();const e=$('#engine').value;S.apiVoices=[];
 if(e==='supertonic')populateSupertonic();
 else if(e==='device')populateDevice();
 else if(window.ConversationHostedAudio?.configure)await window.ConversationHostedAudio.configure(e,$('#voiceA'),$('#voiceB'),vst);
}"""
if old not in s: raise SystemExit('engineChanged block not found')
s=s.replace(old,new,1)
s=s.replace(" $('#engine').onchange=engineChanged;$('#connectVoices').onclick=()=>engineChanged();"," $('#engine').onchange=engineChanged;",1)
js.write_text(s,encoding='utf-8')
