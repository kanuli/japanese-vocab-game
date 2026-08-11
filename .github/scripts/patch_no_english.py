from pathlib import Path
import re

p = Path('grammar.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語文法挑戰 v2.2｜JLPT N1–N5', '日本語文法挑戰 v2.3｜JLPT N1–N5')
s = s.replace('<h1>📝 日本語文法挑戰 v2.2</h1>', '<h1>📝 日本語文法挑戰 v2.3</h1>')

new_formation = r'''function zhFormation(s){
 s=String(s||"");
 const reps=[
  [/Statement A/gi,"前句"],[/Sentence A/gi,"前句"],[/Clause A/gi,"前句"],
  [/Statement B/gi,"後句"],[/Sentence B/gi,"後句"],[/Clause B/gi,"後句"],
  [/Verb dictionary form/gi,"動詞辞書形"],[/Verb plain form/gi,"動詞普通形"],[/Verb-ます form/gi,"動詞ます形"],
  [/Verb ます form/gi,"動詞ます形"],[/Verb negative form/gi,"動詞否定形"],[/Verb past form/gi,"動詞過去形"],
  [/Verb/gi,"動詞"],[/Noun/gi,"名詞"],[/い-adjective/gi,"い形容詞"],[/i-adjective/gi,"い形容詞"],
  [/な-adjective/gi,"な形容詞"],[/na-adjective/gi,"な形容詞"],[/Adjective/gi,"形容詞"],
  [/Plain form/gi,"普通形"],[/Dictionary form/gi,"辞書形"],[/negative/gi,"否定形"],[/past/gi,"過去形"],
  [/present/gi,"現在形"],[/stem/gi,"語幹"],[/Statement/gi,"句子"],[/Sentence/gi,"句子"],[/Clause/gi,"句子"],
  [/polite form/gi,"禮貌形"],[/casual form/gi,"普通形"]
 ];
 for(const [r,v] of reps)s=s.replace(r,v);
 s=s.replace(/\bA\b/g,"前項").replace(/\bB\b/g,"後項");
 s=s.replace(/\s+/g," ").trim();
 return /[A-Za-z]/.test(s)?"":s;
}
function containsLatin(s){return /[A-Za-z]/.test(String(s||""));}
'''

s = re.sub(r'function zhFormation\(s\)\{.*?\n\}\nfunction zhFallback\(q\)\{', new_formation + '\nfunction zhFallback(q){', s, count=1, flags=re.S)

new_translate = r'''async function translateZh(text){
 text=String(text||"").trim();
 if(!text)return "";
 if(zhCache.has(text)){
  const cached=String(zhCache.get(text)||"").trim();
  if(cached && !containsLatin(cached))return cached;
  zhCache.delete(text);
  save("jpgrammar_zh_cache",Object.fromEntries(zhCache.entries()));
 }
 try{
  const u="https://api.mymemory.translated.net/get?q="+encodeURIComponent(text.slice(0,480))+"&langpair=en%7Czh-TW";
  const r=await fetch(u,{cache:"force-cache"});
  if(!r.ok)throw Error("HTTP "+r.status);
  const d=await r.json();
  let z=String(d?.responseData?.translatedText||"").trim();
  if(!z || z.toLowerCase()===text.toLowerCase() || containsLatin(z))throw Error("translation contains English");
  zhCache.set(text,z);
  const obj=Object.fromEntries([...zhCache.entries()].slice(-500));
  save("jpgrammar_zh_cache",obj);
  return z;
 }catch(e){
  console.warn("Traditional Chinese translation unavailable or mixed-language",e);
  return "";
 }
}
'''
s = re.sub(r'async function translateZh\(text\)\{.*?\n\}\nasync function fillWebChinese', new_translate + '\nasync function fillWebChinese', s, count=1, flags=re.S)

s = s.replace('const formation=q.formation?`接續：${zhFormation(q.formation)}`:"";', 'const f=zhFormation(q.formation||""); const formation=f?`接續：${f}`:"";')
s = s.replace("Hanabira + MyMemory 繁中翻譯", "Web 文法庫（繁中轉換）")

# Defensive final filter: never put a mixed-language Web explanation/translation on screen.
s = s.replace('$("#aExp").textContent=(ex||zhFallback(q))+(formation?` ｜ ${formation}`:"");', 'const safeEx=ex&&!containsLatin(ex)?ex:zhFallback(q); $("#aExp").textContent=safeEx+(formation?` ｜ ${formation}`:"");')
s = s.replace('$("#aZh").textContent=zh||"此 Web 例句暫時未取得可靠的繁體中文翻譯。";', '$("#aZh").textContent=(zh&&!containsLatin(zh))?zh:"此 Web 例句暫時未取得可靠的繁體中文翻譯。";')

p.write_text(s, encoding='utf-8')
