// Cached large-vocabulary loader invoked by advanced_words.js before the game initializes.
(function(){"use strict";
const V="large-vocab-20260813-v5",M=`jpquiz_${V}_meta`,P=`jpquiz_${V}_chunk_`;
function obj(t,i){return{id:`large-${i}`,level:t[0],reading:t[1],kanji:t[2]||"",displayWord:t[2]||t[1],meaning:t[3],pos:t[4]||"other",estimated:true,source:"進階補充詞（推定等級）"}}
function cache(){try{const m=JSON.parse(localStorage.getItem(M)||"null");if(!m||m.version!==V||m.count<9000||!m.chunks)return null;let s="";for(let i=0;i<m.chunks;i++){const c=localStorage.getItem(P+i);if(c==null)return null;s+=c}const a=JSON.parse(s);return Array.isArray(a)&&a.length===m.count?{m,a}:null}catch{return null}}
const c=cache();if(c){window.ADVANCED_WORDS.push(...c.a.map(obj));window.ADVANCED_WORDS_META=c.m;return}
function load(src){return new Promise((ok,no)=>{const s=document.createElement("script");s.src=src;s.onload=ok;s.onerror=()=>no(Error(`無法載入 ${src}`));document.head.appendChild(s)})}
setTimeout(async()=>{try{for(const f of["large_vocab_sources.js","large_vocab_corefix.js","large_vocab_matchers.js","large_vocab_build.js"])await load(`./${f}?v=20260813v5`);await window.JPVocabLarge.build()}catch(e){console.error(e);const x=document.getElementById("advStatus");if(x)x.textContent=`⚠️ 大型詞庫載入失敗：${e.message}`}},0);
})();
