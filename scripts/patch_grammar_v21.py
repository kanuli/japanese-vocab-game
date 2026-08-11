from pathlib import Path

p = Path('grammar.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語文法挑戰 v2｜JLPT N1–N5', '日本語文法挑戰 v2.1｜JLPT N1–N5')
s = s.replace('<h1>📝 日本語文法挑戰 v2</h1>', '<h1>📝 日本語文法挑戰 v2.1</h1>')
s = s.replace('dictPath:"https://cdn.jsdelivr.net/npm/kuromoji@0.1.2/dict/"', 'dictPath:"./dict/"')

old = 'let kuro=null, kuroReady=false, furiganaCache=new Map(), renderToken=0;'
new = old + '\nlet zhCache=new Map(Object.entries(load("jpgrammar_zh_cache",{})));'
if old in s and 'jpgrammar_zh_cache' not in s:
    s = s.replace(old, new, 1)

marker = 'function allQ(){'
helpers = r'''
function zhFormation(s){
 s=String(s||"");
 const reps=[
  [/Verb dictionary form/gi,"動詞辞書形"],[/Verb plain form/gi,"動詞普通形"],[/Verb-ます form/gi,"動詞ます形"],
  [/Verb ます form/gi,"動詞ます形"],[/Verb negative form/gi,"動詞否定形"],[/Verb past form/gi,"動詞過去形"],
  [/Verb/gi,"動詞"],[/Noun/gi,"名詞"],[/い-adjective/gi,"い形容詞"],[/i-adjective/gi,"い形容詞"],
  [/な-adjective/gi,"な形容詞"],[/na-adjective/gi,"な形容詞"],[/Adjective/gi,"形容詞"],
  [/Plain form/gi,"普通形"],[/Dictionary form/gi,"辞書形"],[/negative/gi,"否定形"],[/past/gi,"過去形"],
  [/present/gi,"現在形"],[/stem/gi,"語幹"],[/Statement/gi,"句子"],[/Sentence/gi,"句子"],
  [/polite form/gi,"禮貌形"],[/casual form/gi,"普通形"]
 ];
 for(const [r,v] of reps)s=s.replace(r,v);
 return s;
}
function zhFallback(q){
 const cat=q.meaning||"一般文法用法";
 const form=q.formation?` 接續：${zhFormation(q.formation)}。`:"";
 return `此題考查「${q.grammar||q.a}」，屬於「${cat}」類文法。請根據前後文的語意及接續判斷正確形式。${form}`;
}
async function translateZh(text){
 text=String(text||"").trim();
 if(!text)return "";
 if(zhCache.has(text))return zhCache.get(text);
 try{
  const u="https://api.mymemory.translated.net/get?q="+encodeURIComponent(text.slice(0,480))+"&langpair=en%7Czh-TW";
  const r=await fetch(u,{cache:"force-cache"});
  if(!r.ok)throw Error("HTTP "+r.status);
  const d=await r.json();
  let z=String(d?.responseData?.translatedText||"").trim();
  if(!z || z.toLowerCase()===text.toLowerCase())throw Error("no translation");
  zhCache.set(text,z);
  const obj=Object.fromEntries([...zhCache.entries()].slice(-500));
  save("jpgrammar_zh_cache",obj);
  return z;
 }catch(e){
  console.warn("Traditional Chinese translation unavailable",e);
  return "";
 }
}
async function fillWebChinese(q,token){
 const formation=q.formation?`接續：${zhFormation(q.formation)}`:"";
 $("#aExp").textContent="正在載入繁體中文說明…";
 $("#aZh").textContent="正在載入繁體中文翻譯…";
 const [ex,zh]=await Promise.all([translateZh(q.exp||""),translateZh(q.zh||"")]);
 if(token!==renderToken)return;
 $("#aExp").textContent=(ex||zhFallback(q))+(formation?` ｜ ${formation}`:"");
 $("#aZh").textContent=zh||"此 Web 例句暫時未取得可靠的繁體中文翻譯。";
}
'''
if marker in s and 'function translateZh(text)' not in s:
    s = s.replace(marker, helpers + '\n' + marker, 1)

old_block = ''' if(q.source==="web"){
   $("#aExp").textContent=(q.exp?`來源說明（英）：${q.exp}`:"")+(q.formation?` ｜ Formation: ${q.formation}`:"");
   $("#aZh").textContent=q.zh?`來源例句意思（英）：${q.zh}`:"—";
   $("#aSource").innerHTML='<span class=webBadge>WEB</span> Hanabira';
 }else{'''
new_block = ''' if(q.source==="web"){
   $("#aExp").textContent=zhFallback(q);
   $("#aZh").textContent="繁體中文翻譯載入中…";
   $("#aSource").innerHTML='<span class=webBadge>WEB</span> Hanabira + MyMemory 繁中翻譯';
   fillWebChinese(q,token);
 }else{'''
if old_block in s:
    s = s.replace(old_block, new_block, 1)

s = s.replace(
    'Web 題由程式從來源例句自動產生，因此少數題目可能存在其他自然答案；60 題內置題庫則為人工設定。ふりがな由 Kuroshiro + Kuromoji 在瀏覽器內產生。',
    'Web 題由程式從來源例句自動產生，因此少數題目可能存在其他自然答案；60 題內置題庫則為人工設定。Web 題的英文來源說明不直接顯示，會轉為繁體中文並在瀏覽器快取。ふりがな由 Kuroshiro + Kuromoji 在瀏覽器內產生。'
)

p.write_text(s, encoding='utf-8')
print('Patched grammar.html')
