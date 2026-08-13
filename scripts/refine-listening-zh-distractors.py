from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

# Keep the established close-distractor refinements idempotent.
start=s.index('const GROUPS=[')
end=s.index('\nfunction mutations',start)
new_groups=r'''const GROUPS=[
["今日","昨日","明日","今朝"],["今週","先週","来週","再来週"],["今月","先月","来月","再来月"],["今年","去年","来年","再来年"],["さっき","先ほど","あとで","昨日"],
["朝","昼","夕方","夜"],["午前","午後"],["右","左","前","後"],["上","下"],
["ここ","そこ","あそこ","どこ"],["これ","それ","あれ","どれ"],["この","その","あの","どの"],
["まだ","もう"],["いつも","よく","時々","たまに"],["必ず","たぶん","きっと","おそらく"],
["好き","嫌い"],["高い","安い"],["大きい","小さい"],["多い","少ない"],["早い","遅い"],
["行きます","来ます","帰ります","戻ります"],["行く","来る","帰る","戻る"],["買います","売ります"],["買う","売る"],
["始まります","終わります"],["始まる","終わる"],["増えます","減ります"],["増える","減る"]
]'''
s=s[:start]+new_groups+s[end:]

old_mut='function mutations(s){const out=[];for(const g of GROUPS){for(const x of g){if(!s.includes(x))continue;for(const y of g){if(y!==x){const z=s.replace(x,y);if(z!==s&&!out.includes(z))out.push(z)}}}}const m=s.match(/\\d+/);if(m){const n=+m[0];for(const d of [-1,1,2]){const v=Math.max(1,n+d);const z=s.replace(m[0],String(v));if(z!==s&&!out.includes(z))out.push(z)}}return out}'
new_mut=r'''function tokenShadowed(s,x){for(const g of GROUPS)for(const longer of g){if(longer!==x&&longer.length>x.length&&longer.includes(x)&&s.includes(longer))return true}return false}
function mutations(s){const out=[];for(const g of GROUPS){for(const x of g){if(!s.includes(x)||tokenShadowed(s,x))continue;for(const y of g){if(y!==x){const z=s.replace(x,y);if(z!==s&&!out.includes(z))out.push(z)}}}}const m=s.match(/\d+/);if(m){const n=+m[0];for(const d of [-1,1,2]){const v=Math.max(1,n+d);const z=s.replace(m[0],String(v));if(z!==s&&!out.includes(z))out.push(z)}}return out}'''
if old_mut in s:s=s.replace(old_mut,new_mut,1)
elif 'function tokenShadowed(s,x)' not in s:raise SystemExit('mutations function not found')

# Required marker retained for the existing workflow checks.
old_note='四個答案只使用同一句子並改一個關鍵細節，例如時間、方向、肯定／否定、數字、程度或常見動詞。無法產生 3 個足夠相似選項的句子會直接跳過，不使用不相關句子湊答案。'
new_note='四個答案只使用同一句子並改一個關鍵細節，例如時間、方向、數字、程度或常見動詞；繁體中文翻譯也必須保持相似。任何一層不夠接近就會跳過該句，不使用不相關答案湊數。'
if old_note in s:s=s.replace(old_note,new_note,1)

# --- v8: use the data already stored in this GitHub repository. ---
s=s.replace('<title>日本語聽解挑戰 v1.9｜JLPT N1–N5</title>','<title>日本語聽解挑戰 v8.0｜JLPT N1–N5</title>')
s=s.replace('Web 例句 → 日語發音 → 4 個相似答案','GitHub 10,000 題 → 日語發音 → 4 個相似答案')
s=s.replace('正在載入 Web 聽解題庫…','正在載入 GitHub 聽解題庫…')
s=s.replace('<h2>Web 題庫</h2>','<h2>GitHub 聽解題庫</h2>')
s=s.replace('<strong>🌐 Hanabira N1–N5 例句</strong>','<strong>📦 GitHub JLPT N1–N5 合併聽解題庫</strong>')
s=s.replace('重新載入 Web','重新載入題庫')
s=s.replace('先聽清楚，再找出你聽到的句子','先聽清楚，再選出最符合內容的繁體中文答案')
s=s.replace('<div class="label">文法</div><div id="aGrammar"></div>','<div class="label">題型／解析</div><div id="aGrammar"></div>')
s=s.replace('<div class="label">來源</div><div>Hanabira Web 例句</div>','<div class="label">來源</div><div id="aSource">GitHub 聽解題庫</div>')
s=s.replace('Web 句子來源：Hanabira。','題目資料：GitHub 原創 JLPT 風格題 6,690 題 + GitHub Hanabira 基礎例句 3,310 題，共 10,000 筆；遊戲內按日文內容去重。')
s=s.replace('完整聲線庫完成後，每個可選 VOICEVOX 聲線都有相同 3,310 題。','43 個 VOICEVOX 聲線各有相同 3,310 題預錄；其餘題目會自動使用 Supertonic 或裝置日語語音備援。')

old_pool='function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=audioEngine]:checked")?.value==="voicevox"&&!voicevoxFullIndex){const speaker=selectedVoicevoxSpeaker();if(speaker!=="random")p=p.filter(x=>voicevoxIndex?.items?.[x.id]?.speaker===speaker)}if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'
new_pool='function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}\nfunction pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'
if old_pool not in s:raise SystemExit('current pool function not found')
s=s.replace(old_pool,new_pool,1)

old_load='async function loadWeb(){$("#reload").disabled=true;$("#webStatus").textContent="正在載入 N1–N5…";const rs=await Promise.allSettled(["N5","N4","N3","N2","N1"].map(async l=>[l,await fetchLevel(l)]));items=[];const c={N1:0,N2:0,N3:0,N4:0,N5:0};for(const r of rs){if(r.status!=="fulfilled")continue;const [level,pts]=r.value;pts.forEach((p,pi)=>(p.examples||[]).forEach((e,ei)=>{const jp=String(e.jp||"").trim();if(jp.length<5||jp.length>95)return;items.push({id:`${level}-${pi}-${ei}`,level,jp,en:e.en||"",grammar:cleanTitle(p.title),category:cat((p.short_explanation||"")+" "+(p.long_explanation||""))});c[level]++}))}$("#webStatus").textContent=items.length?`✅ 已載入 ${items.length.toLocaleString()} 個 Web 聽解句子。`:"⚠️ Web 題庫暫時無法載入。";$("#counts").innerHTML=Object.entries(c).map(([k,v])=>`<span class=count>${k}: ${v.toLocaleString()}</span>`).join("");$("#reload").disabled=false;render()}'
new_load=r'''async function loadWeb(){$("#reload").disabled=true;$("#webStatus").textContent="正在合併 GitHub 6,690 原創題 + 3,310 基礎題…";const c={N1:0,N2:0,N3:0,N4:0,N5:0};let base=[],original=[];const rs=await Promise.allSettled(["N5","N4","N3","N2","N1"].map(async l=>[l,await fetchLevel(l)]));for(const r of rs){if(r.status!=="fulfilled")continue;const [level,pts]=r.value;pts.forEach((p,pi)=>(p.examples||[]).forEach((e,ei)=>{const jp=String(e.jp||"").trim();if(jp.length<5||jp.length>95)return;base.push({id:`${level}-${pi}-${ei}`,level,jp,en:e.en||"",grammar:cleanTitle(p.title),category:cat((p.short_explanation||"")+" "+(p.long_explanation||"")),typeZh:"基礎例句",explanationZh:"",choicesZh:[],correctZh:"",source:"GitHub Hanabira 基礎例句"})}))}try{const r=await fetch("./listening-original-catalog.json",{cache:"no-cache"});if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();original=(d.items||[]).map(x=>({id:String(x.id||""),level:String(x.level||"").toUpperCase(),jp:String(x.jp||"").trim(),en:"",grammar:[String(x.typeZh||x.type||"聽解"),String(x.explanationZh||"")].filter(Boolean).join("｜"),category:String(x.typeZh||x.type||"聽解"),typeZh:String(x.typeZh||x.type||"聽解"),explanationZh:String(x.explanationZh||""),choicesZh:Array.isArray(x.choicesZh)?x.choicesZh.map(v=>String(v||"").trim()):[],correctZh:String(x.correctZh||"").trim(),source:String(x.source||"GitHub 原創 JLPT 風格題")})).filter(x=>x.id&&/^N[1-5]$/.test(x.level)&&x.jp)}catch(e){console.warn("original catalog unavailable",e)}items=[...base,...original];items.forEach(x=>{if(c[x.level]!==undefined)c[x.level]++});const complete=items.length===10000&&Object.values(c).every(v=>v===2000);$("#webStatus").textContent=complete?"✅ GitHub 合併題庫完成：10,000 筆（N1–N5 每級 2,000）。遊戲會自動去除重複日文句子。":items.length?`⚠️ 目前只載入 ${items.length.toLocaleString()} 筆；仍可先練習已成功載入的題目。`:"❌ GitHub 聽解題庫暫時無法載入。";$("#counts").innerHTML=Object.entries(c).map(([k,v])=>`<span class=count>${k}: ${v.toLocaleString()}</span>`).join("");$("#reload").disabled=false;render()}'''
if old_load not in s:raise SystemExit('loadWeb function not found')
s=s.replace(old_load,new_load,1)

old_make='function makeChoices(q){const d=shuffle(mutations(q.jp));if(d.length<3)return null;return{choices:shuffle([q.jp,...d.slice(0,3)]),quality:"同一句只改一個關鍵細節"}}'
new_make='function makeChoices(q){if(hasCatalogOptions(q))return{choicesZh:[...q.choicesZh],correctZh:q.correctZh,quality:"GitHub 原創題庫：四個相近語意選項"};const d=shuffle(mutations(q.jp));if(d.length<3)return null;return{choices:shuffle([q.jp,...d.slice(0,3)]),quality:"GitHub 基礎題：同一句只改一個關鍵細節"}}'
if old_make not in s:raise SystemExit('makeChoices function not found')
s=s.replace(old_make,new_make,1)
s=s.replace('$("#total").textContent=`🎧 ${items.length.toLocaleString()} 句`','$("#total").textContent=`🎧 ${items.length.toLocaleString()} 筆`')
s=s.replace('個不重複句子。','個不重複題目。')

old_prepare='async function prepareChineseChoices(q,m){const rows=await Promise.all(m.choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==rows.length)return null;const correct=rows.find(x=>x.jp===q.jp);if(!correct)return null;for(const x of rows){if(x===correct)continue;const len=Math.min(normChoice(x.zh).length,normChoice(correct.zh).length)/Math.max(1,Math.max(normChoice(x.zh).length,normChoice(correct.zh).length));if(len<.6||zhChoiceSim(x.zh,correct.zh)<.18)return null}return rows}'
new_prepare=r'''function catalogZhFix(z){z=String(z||"").trim();const m=[["会議","會議"],["駅","車站"],["国","國"],["学","學"],["気","氣"],["体","體"],["発","發"],["実","實"],["験","驗"],["対","對"],["応","應"],["変","變"],["関","關"],["広","廣"],["図","圖"],["号","號"],["楽","樂"],["明日的","明天的"],["今日的","今天的"]];for(const [a,b] of m)z=z.split(a).join(b);return z}
function catalogZhOK(z){return !!String(z||"").trim()&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(String(z))}
async function prepareChineseChoices(q,m){if(Array.isArray(m.choicesZh)&&m.choicesZh.length===4){const raw=m.choicesZh.map(v=>String(v||"").trim()),target=normChoice(m.correctZh),ci=raw.findIndex(v=>normChoice(v)===target);if(ci<0)return null;const rows=[];for(let i=0;i<raw.length;i++){let zh=catalogZhFix(raw[i]);if(!catalogZhOK(zh))zh=catalogZhFix(await translateJaZh(raw[i]));if(!catalogZhOK(zh))return null;rows.push({jp:i===ci?q.jp:q.jp+"\u2060".repeat(i+1),zh})}const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==4)return null;return shuffle(rows)}const rows=await Promise.all(m.choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==rows.length)return null;const correct=rows.find(x=>x.jp===q.jp);if(!correct)return null;for(const x of rows){if(x===correct)continue;const len=Math.min(normChoice(x.zh).length,normChoice(correct.zh).length)/Math.max(1,Math.max(normChoice(x.zh).length,normChoice(correct.zh).length));if(len<.6||zhChoiceSim(x.zh,correct.zh)<.18)return null}return rows}'''
if old_prepare not in s:raise SystemExit('prepareChineseChoices function not found')
s=s.replace(old_prepare,new_prepare,1)

old_fill='async function fillZh(q,rt){const z=await translateZh(q.en);if(rt!==renderToken)return;$("#aZh").textContent=z||"此 Web 例句暫時未取得可靠的繁體中文翻譯。"}'
new_fill='async function fillZh(q,rt){if(q.correctZh){let z=catalogZhFix(q.correctZh);if(!catalogZhOK(z))z=catalogZhFix(await translateJaZh(q.correctZh));if(rt!==renderToken)return;$("#aZh").textContent=z||"此題暫時未取得可靠的繁體中文翻譯。";return}const z=await translateZh(q.en);if(rt!==renderToken)return;$("#aZh").textContent=z||"此基礎例句暫時未取得可靠的繁體中文翻譯。"}'
if old_fill not in s:raise SystemExit('fillZh function not found')
s=s.replace(old_fill,new_fill,1)

# Record answers for an end-of-game review.
s=s.replace('cycle:1};','cycle:1,review:[]};',1)
old_save='save("jplistening_wrong",[...wrong]);$$(".choice")'
new_save='save("jplistening_wrong",[...wrong]);if(game.review)game.review.push({id:q.id,level:q.level,jp:q.jp,correctZh:game.currentZh||q.correctZh||"",explanationZh:q.explanationZh||"",typeZh:q.typeZh||q.grammar||"聽解",ok});$$(".choice")'
if old_save not in s:raise SystemExit('answer save point not found')
s=s.replace(old_save,new_save,1)
s=s.replace('$("#aVoiceSource").textContent=game.lastAudioLabel||"尚未播放";if(game.currentZh)', '$("#aVoiceSource").textContent=game.lastAudioLabel||"尚未播放";if($("#aSource"))$("#aSource").textContent=q.source||"GitHub 聽解題庫";if(game.currentZh)',1)
old_finish='function finish(){stopAllAudio();hideSheet();$("#choices").style.display="none";$("#end").style.display="block";$("#final").textContent=`${game.score} / ${game.limit}`;$("#finalText").textContent=`正確率 ${Math.round(game.score/game.limit*100)}% · 錯題已保存。`}'
new_finish=r'''function finish(){stopAllAudio();hideSheet();$("#choices").style.display="none";$("#end").style.display="block";const total=Math.max(1,game.limit||game.index),pct=Math.round(game.score/total*100),missed=(game.review||[]).filter(x=>!x.ok);$("#final").textContent=`${game.score} / ${game.limit||game.index}`;if(!missed.length){$("#finalText").innerHTML=`正確率 ${pct}% · 🎉 全部正確，沒有錯題需要複習。`;return}const cards=missed.map((r,i)=>`<span style="display:block;text-align:left;border:1px solid var(--line);border-radius:12px;padding:11px;margin:9px 0;background:#fff"><strong>${i+1}. ${esc(r.level)} · ${esc(r.typeZh||"聽解")}</strong><br><span style="font-size:17px;font-weight:800">${esc(r.jp)}</span><br><span style="color:var(--ok);font-weight:800">✓ ${esc(r.correctZh||"")}</span>${r.explanationZh?`<br><span class="muted">${esc(r.explanationZh)}</span>`:""}</span>`).join("");$("#finalText").innerHTML=`正確率 ${pct}% · 錯題 ${missed.length} 題，已保存到「只練錯題」。<span style="display:block;margin-top:14px;font-weight:900;text-align:left">錯題複習</span>${cards}`}'''
if old_finish not in s:raise SystemExit('finish function not found')
s=s.replace(old_finish,new_finish,1)

# Keep the existing browser/static test phrase and make loading-error copy current.
s=s.replace('請按重新載入 Web 後再試。','請按重新載入題庫後再試。')

p.write_text(s,encoding='utf-8')
print('integrated GitHub listening catalog: 6,690 original + 3,310 base, with review and audio fallback')