// Match Chinese meanings using GitHub-hosted sources only (no Kaikki/CORS dependency).
(function(){"use strict";const H=window.JPVocabLarge;if(!H)return;
function addMeaning(key,raw,wanted,meanings,convert){key=String(key||"").trim();if(!key||!wanted.has(key)||meanings.has(key))return false;const value=H.meaning(String(raw||""),convert);if(!value)return false;meanings.set(key,value);return true}
H.readChineseDictionary=async function(wanted,meanings,convert){let thesaurus=0,wikidata=0,errors=[];
try{const dict=await H.first(H.U.thes,"json");for(const [jp,zh] of Object.entries(dict||{}))if(addMeaning(jp,zh,wanted,meanings,convert))thesaurus++}catch(e){errors.push(`日中詞典：${e.message}`)}
try{const text=await H.first(H.U.wiki);for(const line of String(text||"").split(/\r?\n/)){if(!line||line[0]==="#")continue;const tab=line.indexOf("\t");if(tab<=0)continue;const jp=line.slice(0,tab).trim(),zh=line.slice(tab+1).trim();if(addMeaning(jp,zh,wanted,meanings,convert)){wikidata++;continue}const p=jp.match(/^(.+?)\s*[（(][^）)]{1,40}[）)]$/);if(p&&wanted.has(p[1].trim())&&!meanings.has(p[1].trim())){const z=zh.replace(/\s*[（(][^）)]{1,40}[）)]\s*$/," ").trim();if(addMeaning(p[1].trim(),z,wanted,meanings,convert))wikidata++}}}catch(e){errors.push(`Wikidata：${e.message}`)}
const total=meanings.size;if(!total)throw Error(errors.length?errors.join("；"):"GitHub 日中詞義來源沒有可用配對");H.status(`⏳ 已配對 ${total.toLocaleString()} 個中文詞義（日中詞典 ${thesaurus.toLocaleString()}；Wikidata ${wikidata.toLocaleString()}）…`);return{total,thesaurus,wikidata,errors};};
})();
