// Correct 38/39/40-column normalization for the JLPT core CSV.
(function(){"use strict";const H=window.JPVocabLarge;if(!H)return;
function parse(t){const h=(t.split(/\r?\n/,1)[0]||"").trim().toLowerCase(),d=h==="#separator:comma"?",":h==="#separator:semicolon"?";":"\t",z=[];let r=[],f="",q=false;for(let i=0;i<t.length;i++){const c=t[i];if(q){if(c==='"'){if(t[i+1]==='"'){f+='"';i++}else q=false}else f+=c}else if(c==='"')q=true;else if(c===d){r.push(f);f=""}else if(c==='\n'){r.push(f);z.push(r);r=[];f=""}else if(c!=='\r')f+=c}if(f||r.length){r.push(f);z.push(r)}return z}
function rd(x,w){let s=H.clean(x||w).replace(/\s+/g,"").replace(/[\u3400-\u9fff々〆ヵヶ]+\[([^\]]+)\]/g,"$1").replace(/\[([^\]]+)\]/g,"$1");return H.K.test(s)?s:H.K.test(w||"")?w:""}
H.coreKeys=function(t){const s=new Set;for(let r of parse(t)){if(!r.length||String(r[0]||"").trim().startsWith("#"))continue;if(r.length===40)r=r.slice(1);if(r.length===38)r=["",...r];if(r.length!==39)continue;const w=H.clean(r[3]).replace(/\s/g,""),reading=rd(r[6],w);if(w&&reading)s.add(`${reading}|${w}`)}return s};
})();
