from pathlib import Path

p = Path('listening.html')
s = p.read_text(encoding='utf-8')

old_html = '''<div class="source"><strong>🔊 日語語音</strong><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div><div class="field" style="margin-top:8px"><select id="voice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">自動選擇日語語音</option></select></div></div>'''
new_html = '''<div class="source"><strong>🔊 日語語音</strong><div id="voiceStatus" class="muted">正在檢查瀏覽器日語語音…</div><div class="field" style="margin-top:8px"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">聲線風格（模擬）</label><select id="voiceStyle" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="auto">🎛️ 自動</option><option value="standard">👩 標準女聲</option><option value="cute">🌸 可愛女聲</option><option value="mature">💋 成熟性感女聲</option><option value="soft">🌙 柔和低聲</option><option value="male">👨 男聲</option><option value="random">🎲 每題隨機</option></select></div><div class="field" style="margin-top:8px"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">裝置日語語音</label><select id="voice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="">自動選擇日語語音</option></select></div><div class="muted" style="margin-top:7px">聲線風格會調整瀏覽器日語語音的速度、音高與音量；不是模仿任何特定真人。</div></div>'''
if old_html not in s:
    raise SystemExit('voice HTML block not found')
s = s.replace(old_html, new_html, 1)

old_js = '''function chosenVoice(){const n=$("#voice").value;return voices.find(v=>v.name===n)||voices.find(v=>/^ja-JP$/i.test(v.lang))||voices.find(v=>/^ja/i.test(v.lang))||null}\nfunction speak(rate=1){if(!game?.current)return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(game.current.jp);u.lang="ja-JP";u.rate=rate;const v=chosenVoice();if(v)u.voice=v;speechSynthesis.speak(u);game.plays++;$("#playCount").textContent=`已播放 ${game.plays} 次`;if(game.locked){game.locked=false;$$(".choice").forEach(b=>{b.disabled=false;b.classList.remove("locked")})}}'''
new_js = '''const VOICE_STYLES={auto:{label:"自動",rate:1,pitch:1,volume:1},standard:{label:"標準女聲",rate:1,pitch:1.05,volume:1},cute:{label:"可愛女聲",rate:1.04,pitch:1.28,volume:1},mature:{label:"成熟性感女聲",rate:.90,pitch:.82,volume:.96},soft:{label:"柔和低聲",rate:.84,pitch:.92,volume:.82},male:{label:"男聲",rate:.93,pitch:.72,volume:1}};\nfunction voiceStyle(){let key=$("#voiceStyle")?.value||"auto";if(key==="random"){const ks=["standard","cute","mature","soft","male"];key=ks[Math.floor(Math.random()*ks.length)]}return{key,...(VOICE_STYLES[key]||VOICE_STYLES.auto)}}\nfunction chosenVoice(randomize=false){const n=$("#voice").value;if(n)return voices.find(v=>v.name===n)||null;const jp=voices.filter(v=>/^ja/i.test(v.lang));if(randomize&&jp.length)return jp[Math.floor(Math.random()*jp.length)];return jp.find(v=>/^ja-JP$/i.test(v.lang))||jp[0]||null}\nfunction speak(rate=1){if(!game?.current)return;speechSynthesis.cancel();const st=voiceStyle();const u=new SpeechSynthesisUtterance(game.current.jp);u.lang="ja-JP";u.rate=Math.max(.5,Math.min(2,rate*st.rate));u.pitch=st.pitch;u.volume=st.volume;const randomize=$("#voiceStyle")?.value==="random";const v=chosenVoice(randomize);if(v)u.voice=v;speechSynthesis.speak(u);game.plays++;$("#playCount").textContent=`已播放 ${game.plays} 次 · ${st.label}${v?` · ${v.name}`:""}`;if(game.locked){game.locked=false;$$(".choice").forEach(b=>{b.disabled=false;b.classList.remove("locked")})}}'''
if old_js not in s:
    raise SystemExit('voice JS block not found')
s = s.replace(old_js, new_js, 1)

# Give the page a visible revision marker in title only.
s = s.replace('<title>日本語聽解挑戰｜JLPT N1–N5</title>', '<title>日本語聽解挑戰 v1.1｜JLPT N1–N5</title>', 1)

p.write_text(s, encoding='utf-8')
print('patched listening voice styles')
