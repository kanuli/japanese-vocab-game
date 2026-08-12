from pathlib import Path

js_path=Path('mocktest.js')
html_path=Path('mocktest.html')
js=js_path.read_text(encoding='utf-8')
html=html_path.read_text(encoding='utf-8')

# 1) Add a large combinatorial original listening scene generator.
needle='function listeningTypes(level){return level==="N1"||level==="N2"?["課題理解","ポイント理解","概要理解","統合理解"]:level==="N3"?["課題理解","ポイント理解","概要理解"]:["課題理解","ポイント理解"]}'
insert=r'''const ORIGINAL_SCENE_DATA={
N5:{people:["男の人","女の人","学生"],places:["駅","学校","店","図書館"],times:["九時","十時","十一時","二時"],actions:["行きます","待ちます","買います","勉強します"]},
N4:{people:["会社員","学生","店員"],places:["駅前","会議室","図書館","病院"],times:["午前九時","午前十時半","午後二時","午後四時"],actions:["資料を持って行きます","電話します","予約します","先に帰ります"]},
N3:{people:["男の人","女の人","社員"],places:["会社","受付","駅","レストラン"],times:["今日の夕方","明日の朝","午後三時","会議の前"],actions:["担当者に連絡します","資料を確認します","予定を変更します","予約を取り直します"]},
N2:{people:["社員","担当者","利用者"],places:["事務所","会議室","受付","研修会場"],times:["本日の午後","明日の午前中","会議終了後","締切の前"],actions:["責任者に確認します","資料を修正します","参加者へ連絡します","日程を調整します"]},
N1:{people:["担当者","研究員","責任者"],places:["事務局","研究室","会議会場","受付窓口"],times:["本日中","翌日の午前中","会議終了後","最終締切まで"],actions:["関係者と調整します","資料の内容を再確認します","責任者へ報告します","予定を見直します"]}
};
function buildOriginalScenes(level,n){const d=ORIGINAL_SCENE_DATA[level],out=[];if(!d)return out;for(let i=0;i<n*10&&out.length<n;i++){const person=d.people[Math.floor(Math.random()*d.people.length)],place=d.places[Math.floor(Math.random()*d.places.length)],time=d.times[Math.floor(Math.random()*d.times.length)],action=d.actions[Math.floor(Math.random()*d.actions.length)];const audio=`${person}は${time}に${place}へ行って、${action}。`;const correct=`${time}に${place}で${action.replace(/ます。?$/,'る')}`;const wrongTimes=d.times.filter(x=>x!==time),wrongPlaces=d.places.filter(x=>x!==place),wrongActions=d.actions.filter(x=>x!==action);const choices=shuffle([correct,`${wrongTimes[Math.floor(Math.random()*wrongTimes.length)]}に${place}で${action.replace(/ます。?$/,'る')}`,`${time}に${wrongPlaces[Math.floor(Math.random()*wrongPlaces.length)]}で${action.replace(/ます。?$/,'る')}`,`${time}に${place}で${wrongActions[Math.floor(Math.random()*wrongActions.length)].replace(/ます。?$/,'る')}`]);out.push(qObj({id:`osc-${level}-${person}-${place}-${time}-${action}`,type:level==="N1"||level==="N2"?"ポイント理解":"課題理解",score:"listening",instruction:"話を聞いて、内容と合っているものを一つ選んでください。",choices,answer:choices.indexOf(correct),explain:`音声：${audio}`,audioText:audio}))}return out}
'''+needle
if needle not in js:
    raise SystemExit('listeningTypes insertion target not found')
js=js.replace(needle,insert,1)

old='function buildListening(level,n){const qr=Math.min(4,Math.max(3,Math.round(n*.18))),needsVerbal=["N3","N4","N5"].includes(level),verbal=needsVerbal?Math.min(3,Math.max(2,Math.round(n*.12))):0;let out=[...buildQuickResponse(level,qr),...(verbal?buildQuickResponse(level,verbal,"発話表現"):[]),...buildListeningContent(level,n-qr-verbal)];if(out.length<n)out.push(...buildQuickResponse(level,n-out.length));return sample(unique(out),n)}'
new='function buildListening(level,n){const qr=Math.min(4,Math.max(3,Math.round(n*.18))),needsVerbal=["N3","N4","N5"].includes(level),verbal=needsVerbal?Math.min(3,Math.max(2,Math.round(n*.12))):0,scene=Math.max(3,Math.round(n*.22));let out=[...buildQuickResponse(level,qr),...(verbal?buildQuickResponse(level,verbal,"発話表現"):[]),...buildOriginalScenes(level,scene),...buildListeningContent(level,Math.max(0,n-qr-verbal-scene))];if(out.length<n)out.push(...buildOriginalScenes(level,n-out.length));if(out.length<n)out.push(...buildQuickResponse(level,n-out.length));return sample(unique(out),n)}'
if old not in js:
    raise SystemExit('buildListening target not found')
js=js.replace(old,new,1)

# 2) Remember recent questions and prefer unseen combinations on later mock tests.
old_section='function buildSection(level,section,mode){const scale=mode==="quick"?.42:1,plan=Object.fromEntries(Object.entries(section.plan).map(([k,v])=>[k,Math.max(3,Math.round(v*scale))]));let qs=[];if(plan.vocab)qs.push(...buildVocab(level,plan.vocab));if(plan.grammar)qs.push(...buildGrammar(level,plan.grammar));if(plan.reading)qs.push(...buildReading(level,plan.reading));if(plan.listening)qs.push(...buildListening(level,plan.listening));return shuffle(qs)}'
new_section=r'''function qFingerprint(q){return `${q.type}|${q.question||q.passage||q.audioText||q.id}`.slice(0,300)}
function diversifyQuestions(level,qs){const key=`jlptmock_recent_${level}`;let recent=[];try{recent=JSON.parse(localStorage.getItem(key)||"[]")}catch{}const seen=new Set(recent),fresh=[],old=[];shuffle(qs).forEach(q=>(seen.has(qFingerprint(q))?old:fresh).push(q));const ordered=[...fresh,...old];const add=ordered.map(q=>qFingerprint(q));try{localStorage.setItem(key,JSON.stringify([...recent,...add].slice(-2000)))}catch{}return ordered}
function buildSection(level,section,mode){const scale=mode==="quick"?.42:1,plan=Object.fromEntries(Object.entries(section.plan).map(([k,v])=>[k,Math.max(3,Math.round(v*scale))]));let qs=[];if(plan.vocab)qs.push(...buildVocab(level,plan.vocab));if(plan.grammar)qs.push(...buildGrammar(level,plan.grammar));if(plan.reading)qs.push(...buildReading(level,plan.reading));if(plan.listening)qs.push(...buildListening(level,plan.listening));return diversifyQuestions(level,qs)}'''
if old_section not in js:
    raise SystemExit('buildSection target not found')
js=js.replace(old_section,new_section,1)

old_av='$("#availability").textContent=`${l} 可用題源：${vc.toLocaleString()} 個詞彙、${gc.toLocaleString()} 個文法／例句。開始後題目會隨機重新組合。`;'
new_av='$("#availability").textContent=`${l} 可用題源：${vc.toLocaleString()} 個詞彙、${gc.toLocaleString()} 個文法／例句，加上原創情境聽解組合。每次開始會重新組題，並優先避開最近做過的題目。`;'
if old_av not in js:
    raise SystemExit('availability target not found')
js=js.replace(old_av,new_av,1)

# 3) Add official-practice links without copying official content into the repository.
html_needle='<div class="source"><strong>📊 成績</strong><div class="muted" style="margin-top:5px">完成後顯示 180 分制的模擬推定分數、各 scoring section、合格判定與錯題檢討。官方 JLPT 使用 scaled score，因此本站分數只作學習參考。</div></div>'
html_new=html_needle+'''\n<div class="source"><strong>📘 JLPT 官方練習題</strong><div class="muted" style="margin-top:5px">想做真正官方題目時，可直接使用 JLPT 官方網站；本站不複製官方試題或聽解檔案。</div><div style="display:grid;gap:7px;margin-top:9px"><a class="btn" style="text-decoration:none;text-align:center" href="https://www.jlpt.jp/e/samples/forlearners.html?mode=pc" target="_blank" rel="noopener">官方 Sample Questions N1–N5 ↗</a><a class="btn" style="text-decoration:none;text-align:center" href="https://pop.jlpt.jp/e/samples/sampleindex.html" target="_blank" rel="noopener">Official Practice Workbook ↗</a></div></div>'''
if html_needle not in html:
    raise SystemExit('HTML official resources target not found')
html=html.replace(html_needle,html_new,1)

html=html.replace('題目由本站 Web 題庫、學習資料與程式產生，並非官方歷屆試題。','題目由本站 Web 題庫、原創情境模板、學習資料與程式產生，並非官方歷屆試題；系統會優先避開最近做過的題目。',1)

js_path.write_text(js,encoding='utf-8')
html_path.write_text(html,encoding='utf-8')
print('Expanded original JLPT mock bank, repeat avoidance, and official resource links.')
