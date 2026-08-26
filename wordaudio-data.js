(()=>{"use strict";
const W=window.WA=window.WA||{},URLS=["https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv","https://cdn.jsdelivr.net/gh/5mdld/anki-jlpt-decks@main/deck-source/notes.csv"],F=["Notetype","Deck","NoteID","VocabKanji","VocabPitch","VocabPoS","VocabFurigana","VocabDefSC","VocabDefTC","VocabPlus","VocabAudio","SentType1","SentKanji1","SentFurigana1","SentDefSC1","SentDefTC1","SentAudio1","SentType2","SentKanji2","SentFurigana2","SentDefSC2","SentDefTC2","SentAudio2","SentType3","SentKanji3","SentFurigana3","SentDefSC3","SentDefTC3","SentAudio3","SentType4","SentKanji4","SentFurigana4","SentDefSC4","SentDefTC4","SentAudio4","Sort","Alt1","Alt2","Tags"];
W.$=s=>document.querySelector(s);W.$$=s=>[...document.querySelectorAll(s)];W.load=(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch{return d}};W.save=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch{}};W.key=w=>`${w.reading}|${w.kanji||w.displayWord||w.reading}`;
const strip=s=>{const d=document.createElement("div");d.innerHTML=String(s??"").replace(/\[sound:[^\]]+\]/gi," ").replace(/<br\s*\/?>/gi,"；");return(d.textContent||"").replace(/\s+/g," ").trim()},kanji=s=>/[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]/.test(s||""),kana=s=>!!s&&/^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$/.test(String(s).replace(/\s+/g,"")),reading=(f,w)=>{let s=String(f||w||"").replace(/[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]+\[([^\]]+)\]/g,"$1").replace(/\[([^\]]+)\]/g,"$1");s=strip(s).replace(/\s+/g,"");return kana(s)?s:(kana(w)?w:"")};
function norm(x,n){
  if(!x)return null;
  let r=String(x.reading||"").trim(),k=String(x.kanji||"").trim(),d=String(x.displayWord||"").trim();
  if(kanji(r)&&kana(k)){const z=r;r=k;k=z;d=z}
  else if(!kana(r)&&kana(k)){const z=d||r;r=k;k=kanji(z)?z:"";d=z||r}
  else if(!r&&kana(d))r=d;
  if(!kana(r)||!String(x.meaning||"").trim())return null;
  return {...x,id:x.id||`a-${n}`,level:/^N[1-5]$/.test(x.level)?x.level:"N3",reading:r,kanji:kanji(k)?k:"",displayWord:d||k||r,meaning:String(x.meaning).trim(),estimated:x.estimated!==false};
}
function parse(t){const h=String(t).split(/\r?\n/,1)[0].trim().toLowerCase(),d=h==="#separator:comma"?",":h==="#separator:semicolon"?";":"\t",rows=[];let row=[],f="",q=false;for(let p=0;p<t.length;p++){const c=t[p];if(q){if(c==='"'){if(t[p+1]==='"'){f+='"';p++}else q=false}else f+=c}else if(c==='"')q=true;else if(c===d){row.push(f);f=""}else if(c==='\n'){row.push(f);rows.push(row);row=[];f=""}else if(c!=='\r')f+=c}if(f||row.length){row.push(f);rows.push(row)}return rows}
function core(rows){const out=[];for(let r of rows){if(!r.length||String(r[0]).startsWith("#"))continue;if(r.length===F.length+1)r=r.slice(1);if(r.length!==F.length)continue;const f=Object.fromEntries(F.map((n,j)=>[n,r[j]||""])),w=strip(f.VocabKanji).replace(/\s+/g,""),m=strip(f.VocabDefTC),lv=`${f.Deck} ${f.Tags}`.match(/(?:^|[^A-Za-z0-9])N([1-5])(?=$|[^0-9])/i),rd=reading(f.VocabFurigana,w);if(w&&m&&lv&&rd)out.push({id:`c-${f.NoteID||out.length}`,level:`N${lv[1]}`,reading:rd,kanji:kanji(w)?w:"",displayWord:w,meaning:m,estimated:false,teacherGrade:"core",teacherBasis:"external-core-fetch"})}return out}
function uniq(a){const s=new Set;return a.filter(w=>{const k=W.key(w);if(s.has(k))return false;s.add(k);return true})}
W.loadData=async()=>{
  const adv=(window.ADVANCED_WORDS||[]).map(norm).filter(Boolean);let c=[];
  for(const u of URLS){try{const r=await fetch(u);if(!r.ok)throw 0;c=core(parse(await r.text()));if(c.length<1000)throw 0;break}catch{c=[]}}
  const merged=uniq([...c,...adv]);
  W.words=window.applyVocabCommonFixups?window.applyVocabCommonFixups(merged):merged;
  const n={N1:0,N2:0,N3:0,N4:0,N5:0};W.words.forEach(w=>n[w.level]++);
  W.$("#total").textContent=`📚 ${W.words.length.toLocaleString()} 個單字`;
  W.$("#counts").innerHTML=Object.entries(n).map(([k,v])=>`<span class=count>${k}: ${v.toLocaleString()}</span>`).join("");
  W.$("#dataStatus").textContent=c.length?`✅ 核心 ${c.length.toLocaleString()} + 進階詞，去重後 ${W.words.length.toLocaleString()} 個。`:`⚠️ 核心詞暫時無法載入；仍可使用 ${W.words.length.toLocaleString()} 個進階詞。`;
  W.available();
};
})();
