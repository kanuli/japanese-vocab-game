from pathlib import Path

p = Path('grammar.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語文法挑戰 v2.4｜JLPT N1–N5', '日本語文法挑戰 v2.5｜JLPT N1–N5')
s = s.replace('<h1>📝 日本語文法挑戰 v2.4</h1>', '<h1>📝 日本語文法挑戰 v2.5</h1>')

css_old = '.sheet-actions{display:flex;gap:8px;margin-top:13px;position:sticky;bottom:0;background:#fff;padding-top:8px}.sheet-actions .next{flex:1;min-height:49px}.end{display:none;text-align:center;padding:28px}.end .big{font-size:42px;font-weight:900}\n.footer{font-size:11px;color:var(--muted);line-height:1.65;margin:16px 2px}'
css_new = '''.sheet-actions{display:flex;gap:8px;margin-top:13px;position:sticky;bottom:0;background:#fff;padding-top:8px}.sheet-actions .next{flex:1;min-height:49px}.end{display:none;text-align:center;padding:28px 8px}.end .big{font-size:42px;font-weight:900}
.review-summary{margin:18px auto 14px;max-width:760px;text-align:left}.review-title{font-size:19px;font-weight:900;margin:18px 0 9px}.review-breakdown{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.review-stat{border:1px solid var(--line);border-radius:12px;padding:10px;background:#fafbfe;text-align:center}.review-stat b{display:block;font-size:18px;margin-top:3px}.review-list{display:grid;gap:10px;margin-top:10px;text-align:left}.review-item{border:1px solid var(--line);border-radius:14px;padding:13px;background:#fff}.review-item.bad{border-color:#efb6b1;background:#fffafa}.review-q{font-size:18px;font-weight:800;line-height:1.8;margin-bottom:8px;font-family:"Yu Mincho","Hiragino Mincho ProN","Noto Serif JP",serif}.review-meta{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.review-row{display:grid;grid-template-columns:88px 1fr;gap:5px 8px;line-height:1.55;font-size:14px}.review-label{color:var(--muted);font-weight:700}.review-correct{color:var(--ok);font-weight:800}.review-wrong{color:var(--bad);font-weight:800}.review-good{border:1px solid #b9dfca;background:var(--okbg);border-radius:12px;padding:12px;text-align:center;color:var(--ok);font-weight:800}.review-actions{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:18px}
.footer{font-size:11px;color:var(--muted);line-height:1.65;margin:16px 2px}'''
if css_old not in s:
    raise SystemExit('CSS anchor not found')
s = s.replace(css_old, css_new, 1)

s = s.replace('@media(max-width:720px){.wrap{padding:12px}', '@media(max-width:720px){.review-breakdown{grid-template-columns:1fr 1fr}.review-row{grid-template-columns:76px 1fr}.wrap{padding:12px}', 1)

html_old = '<div id="end" class="end"><div id="final" class="big"></div><p id="finalText"></p><button id="again" class="btn primary">再玩一次</button></div>'
html_new = '''<div id="end" class="end"><div id="final" class="big"></div><p id="finalText"></p><div id="reviewSummary" class="review-summary"><div class="review-title">📊 本次學習分析</div><div id="reviewBreakdown" class="review-breakdown"></div><div class="review-title">📝 錯題複習</div><div id="reviewList" class="review-list"></div></div><div class="review-actions"><button id="again" class="btn primary">再玩一次</button><button id="reviewWrongBtn" class="btn">只練錯題</button></div></div>'''
if html_old not in s:
    raise SystemExit('End HTML anchor not found')
s = s.replace(html_old, html_new, 1)

start_old = 'game={pool:p,order:shuffle(p),limit:n,infinite:n===0,index:0,score:0,streak:0,current:null,answered:false};'
start_new = 'game={pool:p,order:shuffle(p),limit:n,infinite:n===0,index:0,score:0,streak:0,current:null,answered:false,history:[]};'
if start_old not in s:
    raise SystemExit('Start game anchor not found')
s = s.replace(start_old, start_new, 1)

answer_old = '$("#aLevel").textContent=q.level;$("#aType").textContent=q.type;game.index++;stats();showSheet();'
answer_new = '$("#aLevel").textContent=q.level;$("#aType").textContent=q.type;game.history.push({q,selected:v,ok});game.index++;stats();showSheet();'
if answer_old not in s:
    raise SystemExit('Answer anchor not found')
s = s.replace(answer_old, answer_new, 1)

finish_old = 'function finish(){hideSheet();$("#question").style.display="none";$("#questionType").style.display="none";$("#choices").style.display="none";$("#end").style.display="block";$("#final").textContent=`${game.score} / ${game.limit}`;$("#finalText").textContent=`正確率 ${Math.round(game.score/game.limit*100)}% · 錯題已保存。`}'
finish_new = r'''function buildReview(){
 const h=game?.history||[], total=h.length||1, mistakes=h.filter(x=>!x.ok), types=["助詞","副詞","接続詞","文法"];
 const labels={"助詞":"助詞","副詞":"副詞","接続詞":"接続詞","文法":"文法表現"};
 $("#reviewBreakdown").innerHTML=types.map(t=>{const rows=h.filter(x=>x.q.type===t),good=rows.filter(x=>x.ok).length;return `<div class="review-stat"><span>${labels[t]}</span><b>${good} / ${rows.length}</b><span class="muted">${rows.length?Math.round(good/rows.length*100):0}%</span></div>`}).join("");
 if(!mistakes.length){$("#reviewList").innerHTML='<div class="review-good">🎉 本次沒有錯題。全部答對！</div>';$("#reviewWrongBtn").style.display="none";return}
 $("#reviewWrongBtn").style.display="inline-block";
 $("#reviewList").innerHTML=mistakes.map((r,i)=>{const q=r.q,ex=q.source==="web"?zhFallback(q):(q.exp||""),full=q.q.replace("＿＿",q.a);return `<div class="review-item bad"><div class="review-meta"><span class="pill">${esc(q.level)}</span><span class="pill">${esc(labels[q.type]||q.type)}</span><span class="pill">${i+1} / ${mistakes.length}</span></div><div class="review-q" data-jp="${encodeURIComponent(full)}">${esc(full)}</div><div class="review-row"><div class="review-label">你的答案</div><div class="review-wrong">${esc(r.selected)}</div><div class="review-label">正確答案</div><div class="review-correct">${esc(q.a)}</div><div class="review-label">文法</div><div>${esc(q.grammar||q.a)}</div><div class="review-label">說明</div><div>${esc(ex||q.meaning||"請根據句子語意及接續判斷。")}</div></div></div>`}).join("");
 const token=++renderToken;$$(".review-q").forEach(el=>setRuby(el,decodeURIComponent(el.dataset.jp),token));
}
function finish(){hideSheet();$("#question").style.display="none";$("#questionType").style.display="none";$("#choices").style.display="none";$("#end").style.display="block";const total=game.history.length||game.limit||1;$("#final").textContent=`${game.score} / ${total}`;$("#finalText").textContent=`正確率 ${Math.round(game.score/total*100)}% · 錯題已保存。`;buildReview() }'''
if finish_old not in s:
    raise SystemExit('Finish function anchor not found')
s = s.replace(finish_old, finish_new, 1)

bind_old = '$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#next").onclick=next;$("#reloadWeb").onclick=loadWeb;'
bind_new = '$("#start").onclick=start;$("#quit").onclick=quit;$("#again").onclick=quit;$("#reviewWrongBtn").onclick=()=>{quit();$("#modeWrong").checked=true;availability();};$("#next").onclick=next;$("#reloadWeb").onclick=loadWeb;'
if bind_old not in s:
    raise SystemExit('Button binding anchor not found')
s = s.replace(bind_old, bind_new, 1)

p.write_text(s, encoding='utf-8')
print('grammar.html patched to v2.5 with end-of-game review')
