// Apply the audited core vocabulary overlay to the upstream JLPT CSV before any page parses it.
// Exact key only: reading + written form. Unresolved rows are deliberately left unchanged.
(()=>{"use strict";
const MAP=window.VOCAB_CORE_VERIFIED;
if(!(MAP instanceof Map)||!MAP.size||typeof window.fetch!=="function")return;
const ORIGINAL_FETCH=window.fetch.bind(window);
const TARGETS=new Set([
  "https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv",
  "https://cdn.jsdelivr.net/gh/5mdld/anki-jlpt-decks@main/deck-source/notes.csv"
]);
const KANA=/^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$/;
function urlOf(input){try{return typeof input==="string"?input:input&&input.url?input.url:String(input||"")}catch{return""}}
function strip(s){
  const d=document.createElement("div");
  d.innerHTML=String(s??"").replace(/\[sound:[^\]]+\]/gi," ").replace(/<br\s*\/?>/gi,"；");
  return(d.textContent||"").replace(/\s+/g," ").trim();
}
function cleanWord(s){return strip(s).replace(/\s+/g,"").trim()}
function reading(furi,word){
  let s=String(furi||word||"").trim()
    .replace(/<rt[^>]*>(.*?)<\/rt>/gi,"$1")
    .replace(/<rp[^>]*>.*?<\/rp>/gi,"")
    .replace(/<ruby[^>]*>|<\/ruby>/gi,"");
  s=s.replace(/[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]+\[([^\]]+)\]/g,"$1").replace(/\[([^\]]+)\]/g,"$1");
  s=strip(s).replace(/\s+/g,"");
  if(KANA.test(s))return s;
  const w=cleanWord(word);
  return KANA.test(w)?w:"";
}
function delimiter(text){
  const h=(String(text||"").split(/\r?\n/,1)[0]||"").trim().toLowerCase();
  return h==="#separator:comma"?",":h==="#separator:semicolon"?";":"\t";
}
function parse(text,del){
  const rows=[];let row=[],field="",quoted=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(quoted){
      if(c==='"'){if(text[i+1]==='"'){field+='"';i++}else quoted=false}else field+=c;
    }else if(c==='"')quoted=true;
    else if(c===del){row.push(field);field=""}
    else if(c==='\n'){row.push(field);rows.push(row);row=[];field=""}
    else if(c!=='\r')field+=c;
  }
  if(field||row.length){row.push(field);rows.push(row)}
  return rows;
}
function encodeField(value,del){
  const s=String(value??"");
  return s.includes('"')||s.includes("\n")||s.includes("\r")||s.includes(del)?'"'+s.replace(/"/g,'""')+'"':s;
}
function serialize(rows,del){return rows.map(r=>r.map(v=>encodeField(v,del)).join(del)).join("\n")}
function patchCsv(text){
  const del=delimiter(text),rows=parse(text,del);let patched=0,eligible=0;
  for(let i=0;i<rows.length;i++){
    let r=rows[i];
    if(!r.length||String(r[0]||"").trim().startsWith("#"))continue;
    if(r.length===40)r=r.slice(1);
    else if(r.length===38)r=["",...r];
    if(r.length!==39)continue;
    const display=cleanWord(r[3]),rd=reading(r[6],display);
    if(!display||!rd)continue;
    eligible++;
    const fix=MAP.get(`${rd}|${display}`);
    if(!fix)continue;
    if(fix.meaning)r[8]=String(fix.meaning);
    if(/^N[1-5]$/.test(String(fix.level||"")))r[1]=String(fix.level);
    rows[i]=r;patched++;
  }
  window.VOCAB_CORE_RUNTIME_PATCH_META={eligibleRows:eligible,patchedRows:patched,verifiedRows:MAP.size};
  return serialize(rows,del);
}
window.fetch=async function(input,init){
  const response=await ORIGINAL_FETCH(input,init);
  if(!TARGETS.has(urlOf(input))||!response.ok)return response;
  try{
    const text=await response.clone().text();
    const patched=patchCsv(text);
    const headers=new Headers(response.headers);
    headers.delete("content-length");headers.delete("content-encoding");
    headers.set("content-type","text/plain; charset=utf-8");
    return new Response(patched,{status:response.status,statusText:response.statusText,headers});
  }catch(err){
    console.error("Verified core vocabulary overlay failed; using original response.",err);
    return response;
  }
};
})();
