from pathlib import Path
import re
p=Path('listening.html');s=p.read_text(encoding='utf-8')
old='if(new Set(keys).size!==4)return null;return shuffle(rows)'
gate=r'''if(new Set(keys).size!==4)return null;const mk=z=>normChoice(z).replace(/客戶服務人員|客服專員/g,"客服人員").replace(/致電|打電話給|打電話|電話聯絡|聯繫/g,"聯絡").replace(/購買|購入/g,"買").replace(/前往|前去/g,"去").replace(/返回|回到/g,"回去").replace(/開始進行|開始舉行/g,"開始").replace(/完結|終了/g,"結束").replace(/遞交|交出/g,"提交").replace(/今日/g,"今天").replace(/明日/g,"明天").replace(/昨日/g,"昨天");if(new Set(rows.map(x=>mk(x.zh))).size!==4)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null}return shuffle(rows)'''
if old in s:s=s.replace(old,gate,1)
elif 'rows.map(x=>mk(x.zh))' not in s:raise SystemExit('gate anchor')
pool='''function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}\nfunction voicevoxQuestionAvailable(q){return !!q?.id&&(!!voicevoxFullIndex?.questions?.[q.id]||!!voicevoxIndex?.items?.[q.id])}\nfunction pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));if(($('input[name=audioEngine]:checked')?.value||'voicevox')==='voicevox')p=p.filter(voicevoxQuestionAvailable);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
s,n=re.subn(r'function hasCatalogOptions\(x\)\{.*?\}\nfunction pool\(\)\{.*?\}',pool,s,count=1,flags=re.S)
if n!=1:raise SystemExit('pool anchor')
if 'function choiceDiffHTML' not in s:
 d='''function choiceDiffHTML(rows,v){const a=rows.map(x=>String(x.zh||"")),z=String(v||"");let p=0;while(p<Math.min(...a.map(x=>x.length))&&a.every(x=>x[p]===a[0][p]))p++;let q=0,m=Math.min(...a.map(x=>x.length))-p;while(q<m&&a.every(x=>x[x.length-1-q]===a[0][a[0].length-1-q]))q++;const e=q?z.length-q:z.length,mid=z.slice(p,e);return mid?esc(z.slice(0,p))+`<span class="choice-key">${esc(mid)}</span>`+esc(z.slice(e)):esc(z)}\n'''.replace('\\n','\n')
 s=s.replace('async function fillZh',d+'async function fillZh',1)
if '.choice-key{' not in s:s=s.replace('.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}','.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}.choice-key{text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900}',1)
s=s.replace('${esc(x.zh)}</button>`).join("")','${choiceDiffHTML(prepared,x.zh)}</button>`).join("")')
R=[('GitHub 10,000 題 → 日語發音 → 4 個相似答案','GitHub 10,000 題 → 日語發音 → 4 個清楚關鍵差異答案'),('先聽清楚，再選出最符合內容的繁體中文答案','先聽清楚，再選出唯一符合內容的答案；四個選項保持同一情境，但關鍵資訊不同。底線只標示差異，不代表正確答案'),('🎭 VOICEVOX<br>自動備援','🎭 VOICEVOX<br>錄音題庫'),('每題使用不同預錄聲線（完整題庫）','每題隨機 VOICEVOX 聲線（3,310 題預錄庫）'),('每題隨機 VOICEVOX 聲線（每個聲線都有完整題庫）','每題隨機 VOICEVOX 聲線（同一套 3,310 題）'),('每個聲線都有完整題庫','每個聲線都有同一套 3,310 題'),('其餘題目會自動使用 Supertonic 或裝置日語語音備援','VOICEVOX 模式只抽已有預錄的題目；完整題庫請選 Supertonic 或裝置語音'),('日本語聽解挑戰 v8.0｜JLPT N1–N5','日本語聽解挑戰 v8.1｜JLPT N1–N5')]
for a,b in R:s=s.replace(a,b)
for m in ('voicevoxQuestionAvailable','rows.map(x=>mk(x.zh))','choiceDiffHTML(prepared,x.zh)','4 個清楚關鍵差異答案'):
 if m not in s:raise SystemExit('missing '+m)
p.write_text(s,encoding='utf-8');print('listening v8.1 finalized')
