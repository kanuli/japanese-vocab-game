from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

old='''<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Supertonic 3 AI 聲線</label><select id="aiVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="F1">👩 F1</option><option value="F2">👩 F2</option><option value="F3">👩 F3</option><option value="F4">👩 F4</option><option value="F5">👩 F5</option><option value="M1">👨 M1</option><option value="M2">👨 M2</option><option value="M3">👨 M3</option><option value="M4">👨 M4</option><option value="M5">👨 M5</option><option value="random">🎲 每題隨機</option></select></div>'''
new='''<div class="field"><label style="display:block;font-size:12px;color:var(--muted);font-weight:700;margin-bottom:4px">Supertonic 3 AI 聲線</label><select id="aiVoice" style="width:100%;padding:9px;border:1px solid var(--line);border-radius:9px"><option value="F1">🌙 沉穩低柔女聲（F1）</option><option value="F2">🌸 明亮活潑女聲（F2）</option><option value="F3">🎙️ 專業播音女聲（F3）</option><option value="F4">✨ 清晰自信女聲（F4）</option><option value="F5">💕 溫柔療癒女聲（F5）</option><option value="M1">⚡ 活力自信男聲（M1）</option><option value="M2">🌑 低沉穩重男聲（M2）</option><option value="M3">🧭 權威專業男聲（M3）</option><option value="M4">🙂 柔和親切男聲（M4）</option><option value="M5">📖 溫暖舒緩男聲（M5）</option><option value="random">🎲 每題隨機聲線</option></select><div id="aiVoiceDesc" class="notice" style="margin-top:7px">F1：沉穩、略低音、平靜而穩定。適合想聽較成熟、低柔的女聲。</div></div>'''
if old not in s:
    raise SystemExit('AI voice selector block not found')
s=s.replace(old,new,1)

anchor='''function selectedAiVoice(){const requested=$("#aiVoice")?.value||"F1";if(requested!=="random")return requested;if(game?.aiVoiceForQuestion)return game.aiVoiceForQuestion;const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];return a[Math.floor(Math.random()*a.length)]}'''
insert='''const AI_VOICE_DESCRIPTIONS={
F1:"F1：沉穩、略低音、平靜而穩定。適合想聽較成熟、低柔的女聲。",
F2:"F2：明亮、愉快、活潑而年輕。適合可愛、角色感較強的女聲。",
F3:"F3：清晰、專業、播音員風格。適合正式或新聞式發音。",
F4:"F4：清脆、自信、表達力強。適合有力而清楚的女聲。",
F5:"F5：親切、溫柔、輕聲而舒緩。適合柔和、陪伴感較強的女聲。",
M1:"M1：活潑、正面、自信而清晰。適合一般及有活力的男聲。",
M2:"M2：低沉、厚實、冷靜而嚴肅。適合成熟、穩重的男聲。",
M3:"M3：精緻、權威、自信可信。適合專業演說或正式旁白。",
M4:"M4：柔和、中性、年輕而親切。適合教育及輕鬆內容。",
M5:"M5：溫暖、輕聲、平靜而舒緩。適合故事及放鬆內容。",
random:"每題隨機使用 F1–F5／M1–M5，避免習慣單一聲線。"
};
function updateAiVoiceDescription(){const id=$("#aiVoice")?.value||"F1";const el=$("#aiVoiceDesc");if(el)el.textContent=AI_VOICE_DESCRIPTIONS[id]||AI_VOICE_DESCRIPTIONS.F1}
function selectedAiVoice(){const requested=$("#aiVoice")?.value||"F1";if(requested!=="random")return requested;if(game?.aiVoiceForQuestion)return game.aiVoiceForQuestion;const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];return a[Math.floor(Math.random()*a.length)]}'''
if anchor not in s:
    raise SystemExit('selectedAiVoice anchor not found')
s=s.replace(anchor,insert,1)

# Add selector change binding without relying on global functions.
needle='''$("#enableAI").onclick=enableAI;'''
if needle in s:
    s=s.replace(needle, needle+'$("#aiVoice").onchange=updateAiVoiceDescription;',1)
else:
    # Fall back to inserting before initial voice load near the end of the script.
    marker='''loadVoices();'''
    if marker not in s:
        raise SystemExit('event binding insertion point not found')
    s=s.replace(marker,'$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();'+marker,1)

# Ensure description is initialized even if event binding was inserted in the first path.
if '$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;' in s:
    s=s.replace('$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;','$("#enableAI").onclick=enableAI;$("#aiVoice").onchange=updateAiVoiceDescription;updateAiVoiceDescription();',1)

p.write_text(s,encoding='utf-8')
print('labelled Supertonic voices with documented tonal descriptions')
