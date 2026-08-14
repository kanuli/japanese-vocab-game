from pathlib import Path

p = Path('conversation.js')
s = p.read_text(encoding='utf-8')
old = '''function loadSystemVoices(){
 if(!('speechSynthesis'in window))return;
 S.systemVoices=speechSynthesis.getVoices().filter(v=>/^ja([-_]|$)/i.test(v.lang));
 if($('#engine').value==='device')populateDevice();
}
function populateDevice(){
 loadSystemVoices();const a=S.systemVoices;
 const opts='<option value="random">🎲 每次隨機</option>'+a.map((v,i)=>`<option value="${i}">${esc(v.name)}｜${esc(v.lang)}</option>`).join('');
 $('#voiceA').innerHTML=opts;$('#voiceB').innerHTML=opts;
 if(a.length){$('#voiceA').value='0';$('#voiceB').value=String(Math.min(1,a.length-1));vst(`✅ 此裝置找到 ${a.length} 個日語系統聲線。`,'ok')}else vst('⚠️ 此裝置沒有找到日語 Speech Synthesis 聲線。','bad');
}'''
new = '''function refreshSystemVoices(){
 if(!('speechSynthesis'in window))return [];
 S.systemVoices=speechSynthesis.getVoices().filter(v=>/^ja([-_]|$)/i.test(v.lang));
 return S.systemVoices;
}
function renderDeviceVoices(){
 const a=S.systemVoices;
 const opts='<option value="random">🎲 每次隨機</option>'+a.map((v,i)=>`<option value="${i}">${esc(v.name)}｜${esc(v.lang)}</option>`).join('');
 $('#voiceA').innerHTML=opts;$('#voiceB').innerHTML=opts;
 if(a.length){$('#voiceA').value='0';$('#voiceB').value=String(Math.min(1,a.length-1));vst(`✅ 此裝置找到 ${a.length} 個日語系統聲線。`,'ok')}else vst('⚠️ 此裝置沒有找到日語 Speech Synthesis 聲線。','bad');
}
function loadSystemVoices(){
 refreshSystemVoices();
 if($('#engine').value==='device')renderDeviceVoices();
}
function populateDevice(){
 refreshSystemVoices();renderDeviceVoices();
}'''
if old in s:
    p.write_text(s.replace(old, new, 1), encoding='utf-8')
elif 'function refreshSystemVoices(){' not in s:
    raise SystemExit('Expected device voice block not found')
print('Device voice refresh fix present')
