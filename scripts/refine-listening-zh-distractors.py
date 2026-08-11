from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

# Use lexical/detail substitutions that translate reliably. Avoid ambiguous standalone 今,
# which can otherwise match inside 今日/今週/今月/今年.
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
if old_mut in s:
    s=s.replace(old_mut,new_mut,1)
elif 'function tokenShadowed(s,x)' not in s:
    raise SystemExit('mutations function not found')

# Only count questions that can actually produce three controlled alternatives.
old_pool='function pool(){let p=items.filter(x=>selectedLevels().includes(x.level));if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return p}'
new_pool='function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return p}'
if old_pool in s:
    s=s.replace(old_pool,new_pool,1)
elif new_pool not in s:
    raise SystemExit('pool function not found')

old_prepare='async function prepareChineseChoices(q,m){const rows=await Promise.all(m.choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==rows.length)return null;return rows}'
new_prepare=r'''function zhChoiceSim(a,b){a=normChoice(a);b=normChoice(b);if(!a||!b)return 0;const A=bigrams(a),B=bigrams(b);let inter=0;A.forEach(x=>{if(B.has(x))inter++});return inter/Math.max(1,A.size+B.size-inter)}
async function prepareChineseChoices(q,m){const rows=await Promise.all(m.choices.map(async jp=>{let zh="";if(jp===q.jp&&q.en)zh=await translateZh(q.en);if(!validTraditionalChoice(jp,zh))zh=await translateJaZh(jp);return{jp,zh}}));if(rows.some(x=>!validTraditionalChoice(x.jp,x.zh)))return null;const keys=rows.map(x=>normChoice(x.zh));if(new Set(keys).size!==rows.length)return null;const correct=rows.find(x=>x.jp===q.jp);if(!correct)return null;for(const x of rows){if(x===correct)continue;const len=Math.min(normChoice(x.zh).length,normChoice(correct.zh).length)/Math.max(1,Math.max(normChoice(x.zh).length,normChoice(correct.zh).length));if(len<.6||zhChoiceSim(x.zh,correct.zh)<.18)return null}return rows}'''
if old_prepare in s:
    s=s.replace(old_prepare,new_prepare,1)
elif 'function zhChoiceSim(a,b)' not in s:
    raise SystemExit('prepareChineseChoices function not found')

old='四個答案只使用同一句子並改一個關鍵細節，例如時間、方向、肯定／否定、數字、程度或常見動詞。無法產生 3 個足夠相似選項的句子會直接跳過，不使用不相關句子湊答案。'
new='四個答案只使用同一句子並改一個關鍵細節，例如時間、方向、數字、程度或常見動詞；繁體中文翻譯也必須保持相似。任何一層不夠接近就會跳過該句，不使用不相關答案湊數。'
if old in s:
    s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('refined Traditional-Chinese distractor quality with safe Japanese token matching')
