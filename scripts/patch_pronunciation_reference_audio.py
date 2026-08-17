from pathlib import Path
import re

p=Path('pronunciation.html')
s=p.read_text(encoding='utf-8')
orig=s

# Basic select styling.
s=s.replace('button,input{font:inherit}', 'button,input,select{font:inherit}', 1)

# Load the dedicated hosted reference controller after the mobile audio guard.
marker='<script src="./mobile-supertonic-guard.js?v=20260817v4"></script>'
script=marker+'\n<script src="./pronunciation-reference-audio.js?v=20260817v1"></script>'
if 'pronunciation-reference-audio.js' not in s:
    assert marker in s, 'mobile guard script marker missing'
    s=s.replace(marker,script,1)

# Add visible reference engine / voice selectors.
old='<div class="source"><strong>♾️ 無每月時數限制</strong>'
new='''<div class="source"><strong>🔊 參考語音</strong>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:9px">
<label class="muted">語音來源<select id="referenceEngine" style="display:block;width:100%;margin-top:5px;padding:9px;border:1px solid var(--line);border-radius:9px;background:#fff"><option value="supertonic" selected>✨ Supertonic 3｜伺服器預錄</option><option value="voicevox">🎭 VOICEVOX｜伺服器預錄</option><option value="device">🔊 裝置 Japanese voice｜備援</option></select></label>
<label class="muted">聲線<select id="referenceVoice" style="display:block;width:100%;margin-top:5px;padding:9px;border:1px solid var(--line);border-radius:9px;background:#fff"><option>聲線載入中…</option></select></label>
</div><div id="referenceVoiceStatus" class="muted" style="margin-top:8px;line-height:1.5">正在載入 Supertonic / VOICEVOX hosted 聲線…</div></div>
<div class="source"><strong>💻 Desktop 本機 Supertonic 備援</strong>'''
if 'id="referenceEngine"' not in s:
    assert old in s, 'old unlimited block marker missing'
    s=s.replace(old,new,1)
else:
    print('Reference selector already present')

# Update explanatory text in the renamed block.
s=s.replace('優先使用現有 Supertonic 預錄作參考音；如該句沒有預錄，可一次安裝本機 Supertonic 模型後在瀏覽器生成參考音。沒有 Azure 5 小時/月限制。',
'''Mobile 直接使用 hosted Supertonic / VOICEVOX，不載入大型 AI 模型；Desktop 如 hosted 沒有該句，可一次安裝本機 Supertonic 後即時生成。沒有 Azure 5 小時/月限制。''',1)

# After the 10k sentence pool is ready, initialize the reference selector instead of the legacy hidden-only loader.
s=s.replace("$('#start').disabled=!items.length;loadHosted()}", "$('#start').disabled=!items.length;window.PronunciationReferenceAudio?.init?.()}",1)

# Use selected Supertonic voice for desktop local synthesis instead of hard-coded F3.
old_local="async function localReference(q){if(!localSuperAllowed()||!localReady)return null;let a=await waitAI(),o=await a.synthesize(q.jp,{voice:'F3',speed:1,totalSteps:8}),r=await fetch(o.url);return r.arrayBuffer()}"
new_local="async function localReference(q){if(!localSuperAllowed()||!localReady)return null;let a=await waitAI(),voice=window.PronunciationReferenceAudio?.selectedSupertonicVoice?.()||'F3',o=await a.synthesize(q.jp,{voice:voice,speed:1,totalSteps:8}),r=await fetch(o.url);return r.arrayBuffer()}"
assert old_local in s, 'localReference block missing'
s=s.replace(old_local,new_local,1)

# Replace the old hidden hard-coded F3 reference playback with the selected hosted engine.
pat=re.compile(r"async function prepareRef\(play=true\)\{.*?\}function stopAudio\(\)\{try\{speechSynthesis\.cancel\(\)\}catch\(e\)\{\}if\(refUrl\)\{URL\.revokeObjectURL\(refUrl\);refUrl=''\}\}", re.S)
new_prepare=r'''async function prepareRef(play=true){
 stopAudio();$('#status').textContent='正在準備參考音…';
 let out=null;try{out=await window.PronunciationReferenceAudio?.prepare?.(game.current,{play:play})}catch(e){console.warn('Hosted pronunciation reference failed',e)}
 if(out&&!out.device){refBuf=out.scoreBytes?out.scoreBytes.slice(0):(out.bytes?out.bytes.slice(0):null);let extra=refBuf?'；已取得可分析的聲學參考。':'；此聲線可播放，但本題沒有可分析的聲學參考。';$('#status').textContent='✅ '+out.label+' · '+(out.provider||'Hosted')+' 已播放'+extra;return !!refBuf}
 if(out?.device){refBuf=null;return playDeviceReference(game.current.jp)}
 let ab=null;if(localSuperAllowed())try{ab=await localReference(game.current)}catch(e){console.warn('Local Supertonic reference failed',e)}
 if(ab){refBuf=ab.slice(0);let blob=new Blob([ab],{type:'audio/mpeg'});refUrl=URL.createObjectURL(blob);if(play)await new Audio(refUrl).play();$('#status').textContent='✅ Hosted 未命中，已使用 Desktop 本機 Supertonic 參考音；現在請說一次。';return true}
 refBuf=null;return playDeviceReference(game.current.jp)
}
function playDeviceReference(text){let vs=[];try{vs=speechSynthesis.getVoices().filter(v=>/^ja([-_]|$)/i.test(v.lang||''))}catch(e){}let u=new SpeechSynthesisUtterance(text);u.lang='ja-JP';u.rate=.95;if($('#referenceEngine')?.value==='device'){let i=Number($('#referenceVoice')?.value);if(Number.isFinite(i)&&vs[i])u.voice=vs[i]}else if(vs[0])u.voice=vs[0];speechSynthesis.cancel();speechSynthesis.speak(u);$('#status').textContent='ℹ️ 此句沒有所選 hosted 錄音，暫用裝置 Japanese voice；聲學評分會清楚標示為文字／時間估算。';return false}
function stopAudio(){try{window.PronunciationReferenceAudio?.stop?.()}catch(e){}try{speechSynthesis.cancel()}catch(e){}if(refUrl){URL.revokeObjectURL(refUrl);refUrl=''}}'''
s,n=pat.subn(new_prepare,s,count=1)
assert n==1, f'prepareRef/stopAudio patch count {n}'

# Mobile copy should no longer imply only a generic server reference.
s=s.replace("$('#enableLocal').textContent='📱 手機使用伺服器參考音';$('#modelStatus').textContent='手機不載入本機 Supertonic；有伺服器參考音時照常使用，缺漏時改用裝置日語。'",
"$('#enableLocal').textContent='📱 Mobile 使用 Hosted AI 聲線';$('#modelStatus').textContent='手機不載入本機 Supertonic；上方可選 Supertonic 10 聲線或 VOICEVOX 43 聲線，只有未收錄句子才改用裝置日語。'",1)

assert s!=orig, 'no changes made'
assert s.count('id="referenceEngine"')==1
assert s.count('id="referenceVoice"')==1
assert s.count('pronunciation-reference-audio.js')==1
assert 'selectedSupertonicVoice' in s
assert 'PronunciationReferenceAudio?.prepare' in s
p.write_text(s,encoding='utf-8')
print('Patched pronunciation.html with visible Supertonic / VOICEVOX reference controls')
