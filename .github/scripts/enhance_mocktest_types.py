from pathlib import Path
import re

p = Path("mocktest.js")
s = p.read_text(encoding="utf-8")

reading = r'''function readingTypes(level){return level==="N1"?["短文理解","中文理解","長文理解","統合理解","主題理解"]:level==="N2"?["短文理解","中文理解","統合理解","主題理解"]:level==="N3"?["短文理解","中文理解","長文理解"]:["短文理解","中文理解"]}
function buildReadingContent(level,n){const p=grammar[level].filter(x=>x.jp.length>=12&&x.jp.length<=105&&mutate(x.jp).length>=3),out=[],types=readingTypes(level);for(let i=0;i<n*8&&p.length>5&&out.length<n;i++){const type=types[out.length%types.length],count=type==="短文理解"?2:type==="中文理解"?3:4,rows=sample(p,count);if(rows.length<count)continue;const target=rows[Math.floor(Math.random()*rows.length)],alts=sample(mutate(target.jp),3);if(alts.length<3)continue;let passage;if(type==="統合理解")passage=`【文章A】\n${rows.slice(0,2).map(x=>x.jp).join("\n")}\n\n【文章B】\n${rows.slice(2).map(x=>x.jp).join("\n")}`;else passage=rows.map(x=>x.jp).join("\n");const cs=shuffle([target.jp,...alts]);let instruction="次の文章を読んで、文章の内容と合っているものを一つ選んでください。";if(type==="統合理解")instruction="文章Aと文章Bを読んで、両方の内容から考えて最も適切なものを一つ選んでください。";if(type==="主題理解")instruction="次の文章を読んで、筆者の考えに最も近いものを一つ選んでください。";out.push(qObj({id:`rd-${type}-${rows.map(x=>x.id).join("-")}`,type,score:"reading",instruction,passage,question:"",choices:cs,answer:cs.indexOf(target.jp),explain:`本文に書かれている重要な内容：${target.jp}`}))}return out}
function buildInfo'''

s, n1 = re.subn(
    r'function buildReadingContent\(level,n\)\{.*?\}\nfunction buildInfo',
    lambda _m: reading,
    s,
    count=1,
    flags=re.S,
)
if n1 != 1:
    raise SystemExit("reading patch target not found")

listening = r'''function listeningTypes(level){return level==="N1"||level==="N2"?["課題理解","ポイント理解","概要理解","統合理解"]:level==="N3"?["課題理解","ポイント理解","概要理解"]:["課題理解","ポイント理解"]}
function buildQuickResponse(level,n,type="即時応答"){return sample(QUICK_RESPONSE[level]||[],n).map((x,i)=>qObj({id:`${type==="発話表現"?"ve":"qr"}-${level}-${i}-${Math.random().toString(36).slice(2,5)}`,type,score:"listening",instruction:type==="発話表現"?"場面の説明を聞いて、その場面で最も自然な表現を一つ選んでください。":"話を聞いて、最もよい応答を一つ選んでください。",question:"",choices:x[1],answer:x[2],explain:`音声：${x[0]}　正答：${x[1][x[2]]}`,audioText:x[0]}))}
function buildListeningContent(level,n){const p=grammar[level].filter(x=>x.jp.length>=8&&x.jp.length<=75&&mutate(x.jp).length>=3),out=[],types=listeningTypes(level);for(let i=0;i<n*7&&p.length>5&&out.length<n;i++){const type=types[out.length%types.length];if(type==="統合理解"){const rows=sample(p,2);if(rows.length<2)continue;const target=rows[1],alts=sample(mutate(target.jp),3);if(alts.length<3)continue;const cs=shuffle([target.jp,...alts]);out.push(qObj({id:`lsi-${rows[0].id}-${rows[1].id}`,type,score:"listening",instruction:"二つの内容を続けて聞いて、全体の内容として最もよいものを一つ選んでください。",question:"",choices:cs,answer:cs.indexOf(target.jp),explain:`音声：${rows[0].jp} ${rows[1].jp}`,audioText:`${rows[0].jp} ${rows[1].jp}`}));continue}const c=sample(p,1)[0];if(!c)continue;const alts=sample(mutate(c.jp),3);if(alts.length<3)continue;const cs=shuffle([c.jp,...alts]);const instruction=type==="課題理解"?"話を聞いて、聞き手が次にすることとして最も近いものを一つ選んでください。":type==="概要理解"?"話を聞いて、話の内容として最もよいものを一つ選んでください。":"音声を聞いて、重要なポイントと合っているものを一つ選んでください。";out.push(qObj({id:`ls-${type}-${c.id}`,type,score:"listening",instruction,question:"",choices:cs,answer:cs.indexOf(c.jp),explain:`音声の内容：${c.jp}`,audioText:c.jp,audioId:c.id.replace(/^g-/,"")}))}return out}
function buildListening(level,n){const qr=Math.min(4,Math.max(3,Math.round(n*.18))),needsVerbal=["N3","N4","N5"].includes(level),verbal=needsVerbal?Math.min(3,Math.max(2,Math.round(n*.12))):0;let out=[...buildQuickResponse(level,qr),...(verbal?buildQuickResponse(level,verbal,"発話表現"):[]),...buildListeningContent(level,n-qr-verbal)];if(out.length<n)out.push(...buildQuickResponse(level,n-out.length));return sample(unique(out),n)}
function buildSection'''

s, n2 = re.subn(
    r'function buildQuickResponse\(level,n\).*?\nfunction buildSection',
    lambda _m: listening,
    s,
    count=1,
    flags=re.S,
)
if n2 != 1:
    raise SystemExit("listening patch target not found")

p.write_text(s, encoding="utf-8")
print("Aligned mock-test reading/listening types by JLPT level")
