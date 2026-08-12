from pathlib import Path
import re

p=Path('mocktest.js')
s=p.read_text(encoding='utf-8')

helper='''\nfunction contentKey(q){const core=q?.audioText||q?.passage||q?.question||q?.id||"",ans=q?.choices?.[q.answer]||"";return `${q?.type||""}|${String(core).replace(/\\s+/g,"").replace(/[。、，,.!?！？「」『』【】（）()]/g,"")}|${String(ans).replace(/\\s+/g,"")}`}\nfunction semanticUnique(a){const seen=new Set;return a.filter(q=>{const k=contentKey(q);if(seen.has(k))return false;seen.add(k);return true})}\nfunction takeDiverse(a,n){const groups=new Map;semanticUnique(a).forEach(q=>{if(!groups.has(q.type))groups.set(q.type,[]);groups.get(q.type).push(q)});for(const v of groups.values())shuffle(v);const keys=shuffle([...groups.keys()]),out=[];while(out.length<n&&keys.some(k=>groups.get(k).length)){for(const k of keys){const g=groups.get(k);if(g.length&&out.length<n)out.push(g.pop())}}return out}\n'''
needle='function unique(a){const seen=new Set;return a.filter(x=>{const k=(x&&typeof x==="object")?(x.id||JSON.stringify(x)):String(x);if(seen.has(k))return false;seen.add(k);return true})}\n'
if 'function semanticUnique' not in s:
    if needle not in s: raise SystemExit('unique helper location not found')
    s=s.replace(needle,needle+helper,1)

def replace_block(start,next_start,new):
    global s
    a=s.find(start)
    if a<0: raise SystemExit(f'missing {start}')
    b=s.find(next_start,a)
    if b<0: raise SystemExit(f'missing boundary {next_start}')
    s=s[:a]+new+'\n'+s[b:]

new_read='''function buildReadingContent(level,n){const p=shuffle(grammar[level].filter(x=>x.jp.length>=12&&x.jp.length<=105&&mutate(x.jp).length>=3)),out=[],types=readingTypes(level),used=new Set;for(let i=0;i<n*4&&out.length<n;i++){const type=types[out.length%types.length],count=type==="短文理解"?2:type==="中文理解"?3:4,rows=p.filter(x=>!used.has(x.id)).slice(0,count);if(rows.length<count)break;rows.forEach(x=>used.add(x.id));const target=rows.find(x=>mutate(x.jp).length>=3)||rows[0],alts=sample(mutate(target.jp),3);if(alts.length<3)continue;let passage;if(type==="統合理解")passage=`【文章A】\\n${rows.slice(0,2).map(x=>x.jp).join("\\n")}\\n\\n【文章B】\\n${rows.slice(2).map(x=>x.jp).join("\\n")}`;else passage=rows.map(x=>x.jp).join("\\n");const cs=shuffle([target.jp,...alts]);let instruction="次の文章を読んで、文章の内容と合っているものを一つ選んでください。";if(type==="統合理解")instruction="文章Aと文章Bを読んで、両方の内容から考えて最も適切なものを一つ選んでください。";if(type==="主題理解")instruction="次の文章を読んで、筆者の考えに最も近いものを一つ選んでください。";out.push(qObj({id:`rd-${type}-${rows.map(x=>x.id).join("-")}`,type,score:"reading",instruction,passage,question:"",choices:cs,answer:cs.indexOf(target.jp),explain:`本文に書かれている重要な内容：${target.jp}`}))}return out}'''
replace_block('function buildReadingContent','function buildInfo',new_read)

new_info='''function buildInfo(level,n){const out=[],families=[
(i)=>{const d=["月曜日","火曜日","水曜日"][i%3],t=15+(i%2);return{p:`市民図書館\\n平日：9時～18時\\n休館日：毎週${d}\\n土曜日：9時～${t}時`,c:`土曜日は${t}時まで利用できる。`,w:["土曜日は18時まで利用できる。",`毎週${["木曜日","金曜日","日曜日"][i%3]}が休館日だ。`,`毎日8時から利用できる。`] ,e:`土曜日は${t}時までと書かれています。`}},
(i)=>{const t=19+(i%2);return{p:`スポーツセンター利用案内\\nプール：10時～${t}時\\nトレーニング室：9時～21時\\n木曜日はプール清掃のため利用できません。`,c:"木曜日はプールを利用できない。",w:["木曜日は全施設が休みだ。",`プールは毎日21時まで使える。`,`トレーニング室は10時から開く。`],e:"木曜日はプール清掃のため利用不可です。"}},
(i)=>{const fee=800+i*100;return{p:`市立美術館\\n開館：10時～17時\\n入館料：${fee}円\\n金曜日は20時まで延長\\n高校生以下は無料`,c:"金曜日は20時まで入館できる。",w:["毎日20時まで開いている。",`入館料は全員${fee}円だ。`,`高校生も入館料が必要だ。`],e:"金曜日だけ20時まで延長されます。"}},
(i)=>{const dep=8+i,arr=dep+1;return{p:`駅前バス時刻表\\nA線 ${dep}:10発 → 市役所 ${dep}:35着\\nB線 ${dep}:30発 → 病院 ${arr}:00着\\n日曜日はB線運休`,c:"日曜日はB線に乗れない。",w:["日曜日はA線も運休する。",`B線は${dep}:10に出発する。`,`A線は病院へ行く。`],e:"日曜日はB線運休と書かれています。"}},
(i)=>{const deadline=12+i;return{p:`日本語セミナー\\n日時：6月20日 14時～16時\\n申込締切：6月${deadline}日\\n定員：30名\\n参加費：無料`,c:`6月${deadline}日までに申し込む必要がある。`,w:["参加費は3000円だ。","定員は20名だ。","セミナーは午前中に行われる。"],e:`申込締切は6月${deadline}日です。`}},
(i)=>{const last=20+i;return{p:`レストラン予約案内\\nランチ：11時30分～14時\\nディナー：17時30分～${last}時\\n予約変更は前日まで\\n当日キャンセルは料金がかかります。`,c:"予約変更は前日までにする。",w:["当日でも無料でキャンセルできる。",`ディナーは14時から始まる。`,`ランチは17時30分までだ。`],e:"予約変更は前日までと書かれています。"}}
];for(let i=0;i<n;i++){const x=families[i%families.length](i);const cs=shuffle([x.c,...x.w]);out.push(qObj({id:`info-${level}-${i}-${i%families.length}`,type:"情報検索",score:"reading",instruction:"次の案内を読んで、正しいものを一つ選んでください。",passage:x.p,question:"",choices:cs,answer:cs.indexOf(x.c),explain:x.e}))}return out}'''
replace_block('function buildInfo','function buildReading',new_info)

new_build_read='''function buildReading(level,n){const info=Math.max(2,Math.round(n*.22)),content=n-info;let candidates=[...buildReadingContent(level,content+4),...buildInfo(level,info+4)];return takeDiverse(candidates,n)}'''
replace_block('function buildReading','const ORIGINAL_SCENE_DATA',new_build_read)

new_scene='''function buildOriginalScenes(level,n){const d=ORIGINAL_SCENE_DATA[level],out=[];if(!d)return out;const combos=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of d.actions)combos.push({person,place,time,action});shuffle(combos).slice(0,n*3).forEach((x,i)=>{const {person,place,time,action}=x,place2=d.places.find(v=>v!==place)||place,time2=d.times.find(v=>v!==time)||time,action2=d.actions.find(v=>v!==action)||action,act=action.replace(/。$/,""),act2=action2.replace(/。$/,""),v=i%4;let audio,correct,wrongs,type,instruction;if(v===0){audio=`${person}は${time}に${place}へ行って、${act}。`;correct=`${time}に${place}で${act}`;wrongs=[`${time2}に${place}で${act}`,`${time}に${place2}で${act}`,`${time}に${place}で${act2}`];type="ポイント理解";instruction="話を聞いて、時間・場所・行動が正しいものを一つ選んでください。"}else if(v===1){audio=`${person}は最初${time}に${place}へ行く予定でしたが、予定が変わり、${time2}に${place2}へ行って${act}。`;correct=`変更後は${time2}に${place2}へ行く`;wrongs=[`変更後も${time}に${place}へ行く`,`変更後は${time}に${place2}へ行く`,`変更後は${time2}に${place}へ行く`];type="課題理解";instruction="予定が変わった後、どうすることになりましたか。"}else if(v===2){audio=`${person}はまず${place}で${act}。そのあと${place2}へ行って${act2}。`;correct=`最初に${place}で${act}`;wrongs=[`最初に${place2}で${act2}`,`最初に${place}で${act2}`,`最初に${place2}で${act}`];type="課題理解";instruction="最初に何をしますか。"}else{audio=`${person}は${time}に${place}で${act}予定です。その前に${place2}で${act2}必要があります。`;correct=`先に${place2}で${act2}`;wrongs=[`先に${place}で${act}`,`先に${place2}で${act}`,`先に${place}で${act2}`];type="概要理解";instruction="この人が先にしなければならないことは何ですか。"}const choices=shuffle([correct,...wrongs]);out.push(qObj({id:`osc-${level}-${v}-${person}-${place}-${time}-${action}`,type,score:"listening",instruction,choices,answer:choices.indexOf(correct),explain:`音声：${audio}`,audioText:audio}))});return semanticUnique(out).slice(0,n)}'''
replace_block('function buildOriginalScenes','function listeningTypes',new_scene)

new_quick='''function buildQuickResponse(level,n,type="即時応答"){return sample(QUICK_RESPONSE[level]||[],n).map((x)=>qObj({id:`${type==="発話表現"?"ve":"qr"}-${level}-${x[0]}`,type,score:"listening",instruction:type==="発話表現"?"場面の説明を聞いて、その場面で最も自然な表現を一つ選んでください。":"話を聞いて、最もよい応答を一つ選んでください。",question:"",choices:x[1],answer:x[2],explain:`音声：${x[0]}　正答：${x[1][x[2]]}`,audioText:x[0]}))}'''
replace_block('function buildQuickResponse','function buildListeningContent',new_quick)

new_lc='''function buildListeningContent(level,n){const pool=shuffle(grammar[level].filter(x=>x.jp.length>=8&&x.jp.length<=75&&mutate(x.jp).length>=3)),out=[],types=listeningTypes(level),used=new Set;for(let i=0;i<n*4&&out.length<n;i++){const type=types[out.length%types.length];if(type==="統合理解"){const rows=pool.filter(x=>!used.has(x.id)).slice(0,2);if(rows.length<2)break;rows.forEach(x=>used.add(x.id));const target=rows[1],alts=sample(mutate(target.jp),3);if(alts.length<3)continue;const cs=shuffle([target.jp,...alts]);out.push(qObj({id:`lsi-${rows[0].id}-${rows[1].id}`,type,score:"listening",instruction:"二つの内容を続けて聞いて、全体の内容として最もよいものを一つ選んでください。",choices:cs,answer:cs.indexOf(target.jp),explain:`音声：${rows[0].jp} ${rows[1].jp}`,audioText:`${rows[0].jp} ${rows[1].jp}`}));continue}const c=pool.find(x=>!used.has(x.id));if(!c)break;used.add(c.id);const alts=sample(mutate(c.jp),3);if(alts.length<3)continue;const cs=shuffle([c.jp,...alts]);const instruction=type==="課題理解"?"話を聞いて、次にすることとして最も近いものを一つ選んでください。":type==="概要理解"?"話を聞いて、全体の内容として最もよいものを一つ選んでください。":"音声を聞いて、重要なポイントと合っているものを一つ選んでください。";out.push(qObj({id:`ls-${type}-${c.id}`,type,score:"listening",instruction,choices:cs,answer:cs.indexOf(c.jp),explain:`音声の内容：${c.jp}`,audioText:c.jp,audioId:c.id.replace(/^g-/,"")}))}return out}'''
replace_block('function buildListeningContent','function buildListening',new_lc)

new_bl='''function buildListening(level,n){const qr=Math.min(3,(QUICK_RESPONSE[level]||[]).length),needsVerbal=["N3","N4","N5"].includes(level),verbal=needsVerbal?Math.min(2,(QUICK_RESPONSE[level]||[]).length):0,scene=Math.max(4,Math.round(n*.28));let candidates=[...buildQuickResponse(level,qr),...(verbal?buildQuickResponse(level,verbal,"発話表現"):[]),...buildOriginalScenes(level,scene+5),...buildListeningContent(level,n+8)];let out=takeDiverse(candidates,n);if(out.length<n)out=takeDiverse([...out,...buildOriginalScenes(level,n*2),...buildListeningContent(level,n*2)],n);return out}'''
replace_block('function buildListening','function qFingerprint',new_bl)

s=s.replace('function qFingerprint(q){return `${q.type}|${q.question||q.passage||q.audioText||q.id}`.slice(0,300)}','function qFingerprint(q){return contentKey(q).slice(0,500)}')
s=s.replace('function diversifyQuestions(level,qs){const key=', 'function diversifyQuestions(level,qs){qs=semanticUnique(qs);const key=',1)

p.write_text(s,encoding='utf-8')

h=Path('mocktest.html')
ht=h.read_text(encoding='utf-8')
ht=re.sub(r'mocktest\\.js\\?v=[^"\\s<]+','mocktest.js?v=20260813-diversity1',ht)
h.write_text(ht,encoding='utf-8')
print('Improved JLPT reading/listening diversity and duplicate control')
