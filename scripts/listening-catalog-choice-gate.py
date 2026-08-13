from pathlib import Path
import re

p = Path('listening.html')
s = p.read_text(encoding='utf-8')


def sub1(pattern, replacement, label):
    global s
    s2, n = re.subn(pattern, lambda m: replacement, s, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'{label}: expected one match, got {n}')
    s = s2


# v8.1: a selected VOICEVOX engine must really stay VOICEVOX, and answers must
# be plausible but unambiguous rather than four near-synonymous paraphrases.
s = s.replace('日本語聽解挑戰 v8.0｜JLPT N1–N5', '日本語聽解挑戰 v8.1｜JLPT N1–N5')
s = s.replace('GitHub 10,000 題 → 日語發音 → 4 個相似答案', 'GitHub 10,000 題 → 日語發音 → 4 個清楚關鍵差異答案')
s = s.replace('🎭 VOICEVOX<br>自動備援', '🎭 VOICEVOX<br>不換引擎')
s = s.replace(
    '43 個 VOICEVOX 聲線各有相同 3,310 題預錄；其餘題目會自動使用 Supertonic 或裝置日語語音備援。可整次練習固定一個聲線，或每題隨機；GitHub Releases 為主來源，Hugging Face 自動備援。完整庫驗證完成前會保留現有音訊。',
    '選擇 VOICEVOX 時，只會抽出目前已有 VOICEVOX 預錄的題目，確保不會偷偷改用 Supertonic 或裝置聲音。選定單一聲線後，整次練習都保持該聲線；選擇「隨機」才會每題換 VOICEVOX 聲線。切換 Supertonic／裝置語音可使用完整 10,000 題庫。'
)
s = s.replace(
    '先聽清楚，再選出最符合內容的繁體中文答案',
    '先聽清楚，再選出唯一符合內容的繁體中文答案。四個選項保持同一情境，但只改時間、人物、地點、動作、方向、數量等關鍵資訊；底線只標示差異，不代表正確答案'
)

# Make the differing part easy to scan. The underline is neutral: every choice
# receives it, so it does not reveal the correct answer.
if '.choice-key{' not in s:
    s = s.replace(
        '.choice.correct{border-color:var(--ok);background:var(--okbg);color:var(--ok)}.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}',
        '.choice.correct{border-color:var(--ok);background:var(--okbg);color:var(--ok)}.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}.choice-key{text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900}'
    )

# In VOICEVOX mode, only questions that really exist in the VOICEVOX index are
# eligible. This makes a fixed selected voice truthful instead of silently
# falling back to another engine on the 6,690 catalog-only questions.
new_pool = r'''function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}
function voicevoxQuestionAvailable(q){if(!q?.id)return false;if(voicevoxFullIndex?.questions?.[q.id])return true;return !!voicevoxIndex?.items?.[q.id]}
function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));const audioMode=$("input[name=audioEngine]:checked")?.value||"voicevox";if(audioMode==="voicevox")p=p.filter(voicevoxQuestionAvailable);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
sub1(r'function hasCatalogOptions\(x\)\{.*?\}\nfunction pool\(\)\{.*?\}', new_pool, 'VOICEVOX-aware pool')

new_availability = r'''function availability(){const p=pool(),audioMode=$("input[name=audioEngine]:checked")?.value||"voicevox";let t=audioMode==="voicevox"?`VOICEVOX 固定聲線模式：目前可用 ${p.length.toLocaleString()} 個不重複題目；只抽有 VOICEVOX 預錄的題目，不會改用其他語音。`:`目前選擇：${p.length.toLocaleString()} 個不重複題目（可使用完整合併題庫）。`;if(!selectedLevels().length)t="請至少選一個 JLPT 等級。";else if(audioMode==="voicevox"&&!voicevoxFullIndex&&!Object.keys(voicevoxIndex?.items||{}).length)t="正在確認 VOICEVOX 題目覆蓋範圍…";else if($("input[name=mode]:checked").value==="wrong"&&!p.length)t="目前沒有符合條件的錯題。";$("#availability").textContent=t;$("#start").disabled=!p.length}'''
sub1(r'function availability\(\)\{.*?\}\nfunction loadVoices', new_availability+'\nfunction loadVoices', 'availability')

# Catalog choices remain useful when they describe one situation with different
# facts. Reject synonym-only paraphrases, and when possible fall back to a
# controlled Japanese mutation (one audible detail changed) instead.
new_make = r'''function makeChoices(q){const d=shuffle(mutations(q.jp));if(hasCatalogOptions(q))return{choicesZh:[...q.choicesZh],correctZh:q.correctZh,fallbackChoices:d.length>=3?shuffle([q.jp,...d.slice(0,3)]):null,quality:"同一情境，只改一個可聽出的關鍵資訊"};if(d.length<3)return null;return{choices:shuffle([q.jp,...d.slice(0,3)]),quality:"同一情境，只改一個可聽出的關鍵資訊"}}'''
sub1(r'function makeChoices\(q\)\{.*?\}\nfunction render', new_make+'\nfunction render', 'makeChoices')

new_prepare = r'''function catalogZhFix(z){z=String(z||"").trim();const m=[["会議","會議"],["駅","車站"],["国","國"],["学","學"],["気","氣"],["体","體"],["発","發"],["実","實"],["験","驗"],["対","對"],["応","應"],["変","變"],["関","關"],["広","廣"],["図","圖"],["号","號"],["楽","樂"],["明日的","明天的"],["今日的","今天的"]];for(const [a,b] of m)z=z.split(a).join(b);return z}
function catalogZhOK(z){return !!String(z||"").trim()&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(String(z))}
function answerMeaningKey(z){z=normChoice(catalogZhFix(z));const pairs=[["客戶服務人員","客服人員"],["客戶服務","客服"],["客服專員","客服人員"],["致電","聯絡"],["打電話給","聯絡"],["打電話","聯絡"],["電話聯絡","聯絡"],["撥電話給","聯絡"],["聯繫","聯絡"],["購買","買"],["購入","買"],["前往","去"],["前去","去"],["返回","回去"],["回到","回去"],["開始進行","開始"],["開始舉行","開始"],["完結","結束"],["終了","結束"],["遞交","提交"],["交出","提交"],["今日","今天"],["明日","明天"],["昨日","昨天"],["稍後","之後"],["一會兒後","之後"]];for(const [a,b] of pairs)z=z.split(a).join(b);return z}
function catalogRowsBalanced(rows){if(rows.length!==4)return false;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==4)return false;const meanings=rows.map(x=>answerMeaningKey(x.zh));if(new Set(meanings).size!==4)return false;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return false}return true}
async function controlledChineseRows(q,choices){if(!Array.isArray(choices)||choices.length!==4)return null;const rows=await Promise.all(choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh:catalogZhFix(zh)}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==4)return null;const correct=rows.find(x=>x.jp===q.jp);if(!correct)return null;for(const x of rows){if(x===correct)continue;const len=Math.min(normChoice(x.zh).length,normChoice(correct.zh).length)/Math.max(1,Math.max(normChoice(x.zh).length,normChoice(correct.zh).length));if(len<.55)return null}return rows}
async function prepareChineseChoices(q,m){if(Array.isArray(m.choicesZh)&&m.choicesZh.length===4){const raw=m.choicesZh.map(v=>String(v||"").trim()),target=normChoice(m.correctZh),ci=raw.findIndex(v=>normChoice(v)===target);if(ci<0)return null;const rows=[];for(let i=0;i<raw.length;i++){let zh=catalogZhFix(raw[i]);if(!catalogZhOK(zh))zh=catalogZhFix(await translateJaZh(raw[i]));if(!catalogZhOK(zh))return null;rows.push({jp:i===ci?q.jp:q.jp+"\u2060".repeat(i+1),zh})}if(catalogRowsBalanced(rows))return shuffle(rows);const fallback=await controlledChineseRows(q,m.fallbackChoices);return fallback?shuffle(fallback):null}const rows=await controlledChineseRows(q,m.choices);return rows?shuffle(rows):null}
function commonChoicePrefix(values){if(!values.length)return"";let p=values[0];for(const v of values.slice(1)){let i=0;while(i<p.length&&i<v.length&&p[i]===v[i])i++;p=p.slice(0,i);if(!p)break}return p}
function commonChoiceSuffix(values,prefixLen){if(!values.length)return"";let s=values[0];for(const v of values.slice(1)){let i=0;while(i<s.length-prefixLen&&i<v.length-prefixLen&&s[s.length-1-i]===v[v.length-1-i])i++;s=s.slice(s.length-i);if(!s)break}const shortest=Math.min(...values.map(v=>v.length));if(prefixLen+s.length>=shortest)s=s.slice(Math.max(0,prefixLen+s.length-shortest+1));return s}
function choiceDiffHTML(rows,value){const vals=rows.map(x=>String(x.zh||"")),v=String(value||"");const pre=commonChoicePrefix(vals),suf=commonChoiceSuffix(vals,pre.length),end=suf.length?v.length-suf.length:v.length,mid=v.slice(pre.length,Math.max(pre.length,end));if(!mid)return esc(v);return esc(v.slice(0,pre.length))+`<span class="choice-key">${esc(mid)}</span>`+esc(v.slice(end))}'''
sub1(r'function catalogZhFix\(z\)\{.*?\}\nasync function fillZh', new_prepare+'\nasync function fillZh', 'balanced answer choices')

# Use the neutral underline renderer on all four options.
s = s.replace('${esc(x.zh)}</button>`).join("")', '${choiceDiffHTML(prepared,x.zh)}</button>`).join("")')
if 'choiceDiffHTML(prepared,x.zh)' not in s:
    raise SystemExit('choice-difference renderer was not installed')

# A VOICEVOX failure must not change engine/voice behind the learner's back.
s = s.replace(
    '$("#voicevoxStatus").textContent="⚠️ GitHub 與 Hugging Face 的 VOICEVOX 音訊暫時都無法播放；已改用其他語音備援。";return false',
    '$("#voicevoxStatus").textContent="⚠️ 此題的 VOICEVOX 音訊暫時無法播放；為保持你選擇的聲線，不會改用其他語音。請重試。";return false'
)
new_voicevox_branch = r'''if(mode==="voicevox"){if(await speakVoicevox(rate))return;$("#playCount").textContent="⚠️ VOICEVOX 本題暫時無法播放；已保持所選聲線，沒有切換到其他引擎。請重試播放。";return}if(mode==="ai"){'''
sub1(r'if\(mode==="voicevox"\)\{.*?\}if\(mode==="ai"\)\{', new_voicevox_branch, 'no silent VOICEVOX fallback')

# Final assertions make failures obvious in GitHub Actions.
required = [
    'voicevoxQuestionAvailable',
    'VOICEVOX 固定聲線模式',
    'answerMeaningKey',
    'catalogRowsBalanced',
    'choiceDiffHTML',
    '沒有切換到其他引擎',
    '同一情境，只改一個可聽出的關鍵資訊',
]
for marker in required:
    if marker not in s:
        raise SystemExit(f'missing v8.1 marker: {marker}')

p.write_text(s, encoding='utf-8')
print('installed v8.1 VOICEVOX consistency + balanced listening-answer design')
