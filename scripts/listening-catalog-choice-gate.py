from pathlib import Path
import re
p=Path('listening.html');s=p.read_text(encoding='utf-8')

# Answers should be related enough to be useful, but never four ways of saying
# the same thing. Canonicalize common Traditional-Chinese paraphrases first.
old='if(new Set(keys).size!==4)return null;return shuffle(rows)'
gate=r'''if(new Set(keys).size!==4)return null;const meaningKey=z=>normChoice(z).replace(/客戶服務人員|客服專員/g,"客服人員").replace(/致電|打電話給|打電話|電話聯絡|聯繫/g,"聯絡").replace(/購買|購入/g,"買").replace(/前往|前去/g,"去").replace(/返回|回到/g,"回去").replace(/開始進行|開始舉行/g,"開始").replace(/完結|終了/g,"結束").replace(/遞交|交出/g,"提交").replace(/今日/g,"今天").replace(/明日/g,"明天").replace(/昨日/g,"昨天");const meanings=rows.map(x=>meaningKey(x.zh));if(new Set(meanings).size!==4)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null}return shuffle(rows)'''
if old in s:s=s.replace(old,gate,1)
elif 'const meanings=rows.map(x=>meaningKey(x.zh))' not in s:raise SystemExit('choice gate anchor not found')

# When VOICEVOX is selected, only draw questions that actually have VOICEVOX
# recordings. The selected voice can therefore be used throughout the game.
pool='''function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}\nfunction voicevoxQuestionAvailable(q){return !!q?.id&&(!!voicevoxFullIndex?.questions?.[q.id]||!!voicevoxIndex?.items?.[q.id])}\nfunction pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));if(($('input[name=audioEngine]:checked')?.value||'voicevox')==='voicevox')p=p.filter(voicevoxQuestionAvailable);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
s,n=re.subn(r'function hasCatalogOptions\(x\)\{.*?\}\nfunction pool\(\)\{.*?\}',pool,s,count=1,flags=re.S)
if n!=1:raise SystemExit('pool patch failed')

# Underline the part that differs across all four choices. Every choice gets the
# same treatment, so this helps comparison without revealing the answer.
if 'function choiceDiffHTML' not in s:
    diff=r'''function choiceDiffHTML(rows,v){const a=rows.map(x=>String(x.zh||"")),z=String(v||"");let p=0;while(p<Math.min(...a.map(x=>x.length))&&a.every(x=>x[p]===a[0][p]))p++;let q=0,m=Math.min(...a.map(x=>x.length))-p;while(q<m&&a.every(x=>x[x.length-1-q]===a[0][a[0].length-1-q]))q++;const e=q?z.length-q:z.length,mid=z.slice(p,e);return mid?esc(z.slice(0,p))+`<span class="choice-key">${esc(mid)}</span>`+esc(z.slice(e)):esc(z)}\n'''
    s=s.replace('async function fillZh',diff+'async function fillZh',1)
if '.choice-key{' not in s:
    s=s.replace('.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}','.choice.wrong{border-color:var(--bad);background:var(--badbg);color:var(--bad)}.choice-key{text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;font-weight:900}',1)
s=s.replace('${esc(x.zh)}</button>`).join("")','${choiceDiffHTML(prepared,x.zh)}</button>`).join("")')

s=s.replace('GitHub 10,000 題 → 日語發音 → 4 個相似答案','GitHub 10,000 題 → 日語發音 → 4 個清楚關鍵差異答案')
s=s.replace('先聽清楚，再選出最符合內容的繁體中文答案','先聽清楚，再選出唯一符合內容的答案；四個選項保持同一情境，但關鍵資訊不同。底線只標示差異，不代表正確答案')
s=s.replace('🎭 VOICEVOX<br>自動備援','🎭 VOICEVOX<br>錄音題庫')
s=s.replace('日本語聽解挑戰 v8.0｜JLPT N1–N5','日本語聽解挑戰 v8.1｜JLPT N1–N5')

for m in ('voicevoxQuestionAvailable','meaningKey','choiceDiffHTML(prepared,x.zh)','4 個清楚關鍵差異答案'):
    if m not in s:raise SystemExit('missing '+m)
p.write_text(s,encoding='utf-8');print('v8.1: recorded VOICEVOX pool + unambiguous key-detail choices')
