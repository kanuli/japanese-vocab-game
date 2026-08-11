from pathlib import Path
import re

p = Path('grammar.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語文法挑戰 v2.1｜JLPT N1–N5', '日本語文法挑戰 v2.2｜JLPT N1–N5')
s = s.replace('<h1>📝 日本語文法挑戰 v2.1</h1>', '<h1>📝 日本語文法挑戰 v2.2</h1>')

s = s.replace('<script src="https://cdn.jsdelivr.net/npm/kuroshiro@1.2.0/dist/kuroshiro.min.js"></script>\n<script src="https://cdn.jsdelivr.net/npm/kuroshiro-analyzer-kuromoji@1.1.0/dist/kuroshiro-analyzer-kuromoji.min.js"></script>', '<script src="./vendor/kuromoji.js"></script>')

s = s.replace('let kuro=null, kuroReady=false, furiganaCache=new Map(), renderToken=0;', 'let tokenizer=null, kuroReady=false, furiganaCache=new Map(), renderToken=0;')

init_pat = re.compile(r'async function initFurigana\(\)\{.*?\n\}', re.S)
new_init = r'''async function initFurigana(){
 try{
   if(typeof kuromoji==="undefined")throw Error("Kuromoji browser library unavailable");
   tokenizer=await new Promise((resolve,reject)=>{
     kuromoji.builder({dicPath:"./dict/"}).build((err,t)=>err?reject(err):resolve(t));
   });
   kuroReady=true;
   $("#furiganaStatus").textContent="✅ ふりがな已準備：漢字上方會顯示平假名。";
 }catch(e){
   console.warn("Furigana init failed",e);
   kuroReady=false;
   $("#furiganaStatus").textContent="⚠️ ふりがな引擎暫時無法載入："+(e?.message||e)+"。遊戲仍可使用。";
 }
}'''
s, n = init_pat.subn(new_init, s, count=1)
if n != 1:
    raise SystemExit('initFurigana block not found')

ruby_pat = re.compile(r'async function rubyHTML\(text\)\{.*?\n\}', re.S)
new_ruby = r'''function kataToHira(text){
 return String(text||"").replace(/[ァ-ヶ]/g,ch=>String.fromCharCode(ch.charCodeAt(0)-0x60));
}
function isKana(ch){return /[ぁ-ゖァ-ヶー]/.test(ch||"")}
function tokenRuby(tok){
 const surface=String(tok?.surface_form||"");
 const reading=kataToHira(tok?.reading||"");
 if(!surface)return "";
 if(!reading || !/[一-龯々]/.test(surface))return esc(surface);
 let si=0,ri=0,se=surface.length,re=reading.length;
 while(si<se && ri<re && isKana(surface[si]) && kataToHira(surface[si])===reading[ri]){si++;ri++;}
 while(se>si && re>ri && isKana(surface[se-1]) && kataToHira(surface[se-1])===reading[re-1]){se--;re--;}
 const prefix=surface.slice(0,si), base=surface.slice(si,se), suffix=surface.slice(se), ruby=reading.slice(ri,re);
 if(!base || !ruby || !/[一-龯々]/.test(base))return esc(surface);
 return esc(prefix)+`<ruby>${esc(base)}<rt>${esc(ruby)}</rt></ruby>`+esc(suffix);
}
async function rubyHTML(text){
 text=String(text??"");
 if(!kuroReady||!tokenizer)return esc(text);
 if(furiganaCache.has(text))return furiganaCache.get(text);
 try{
   const tokens=tokenizer.tokenize(text);
   const html=tokens.map(tokenRuby).join("");
   furiganaCache.set(text,html);
   return html;
 }catch(e){
   console.warn("Furigana render failed",e);
   return esc(text);
 }
}'''
s, n = ruby_pat.subn(new_ruby, s, count=1)
if n != 1:
    raise SystemExit('rubyHTML block not found')

s = s.replace('ふりがな由 Kuroshiro + Kuromoji 在瀏覽器內產生。', 'ふりがな由本地 Kuromoji 在瀏覽器內產生。')
s = s.replace('正在準備 Kuroshiro / Kuromoji…', '正在準備本地 Kuromoji…')

p.write_text(s, encoding='utf-8')
