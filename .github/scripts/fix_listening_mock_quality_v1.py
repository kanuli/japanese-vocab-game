from pathlib import Path
import re


def replace_once(s, old, new, label):
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{label}: expected 1 match, found {n}')
    return s.replace(old,new,1)

# ---------------- Listening game ----------------
p=Path('listening.html')
s=p.read_text(encoding='utf-8')
if 'listeningCatalogErrors' not in s:
    s=s.replace('日本語聽解挑戰 v8.1','日本語聽解挑戰 v8.2')
    old='function hasCatalogOptions(x){return Array.isArray(x?.choicesZh)&&x.choicesZh.length===4&&!!String(x?.correctZh||"").trim()}'
    new='''function catalogNorm(z){return String(z||"").normalize("NFKC").replace(/[\\s，。！？、,.!?「」『』（）()]/g,"").trim()}
function catalogChoiceOK(z){z=String(z||"").trim();return !!z&&!/[A-Za-zぁ-ゖァ-ヺ]/.test(z)}
function listeningCatalogErrors(x){const e=[],cs=Array.isArray(x?.choicesZh)?x.choicesZh.map(v=>String(v||"").trim()):[],correct=String(x?.correctZh||"").trim();if(cs.length!==4)e.push("choice-count");if(cs.some(v=>!catalogChoiceOK(v)))e.push("non-traditional-choice");const keys=cs.map(catalogNorm);if(new Set(keys).size!==4)e.push("duplicate-choice");const target=catalogNorm(correct);if(!target||keys.filter(k=>k===target).length!==1)e.push("answer-not-unique");if(cs.length===4&&target){const ci=keys.indexOf(target),lens=keys.map(k=>[...k].length),cl=lens[ci]||0,near=lens.filter((_,i)=>i!==ci).map(n=>Math.min(n,cl)/Math.max(1,Math.max(n,cl)));if(near.length&&Math.max(...near)<.52)e.push("answer-length-giveaway")}return e}
function hasCatalogOptions(x){return !listeningCatalogErrors(x).length}'''
    s=replace_once(s,old,new,'listening catalog gate')

    old='''original=(d.items||[]).map(x=>({id:String(x.id||""),level:String(x.level||"").toUpperCase(),jp:String(x.jp||"").trim(),en:"",grammar:[String(x.typeZh||x.type||"聽解"),String(x.explanationZh||"")].filter(Boolean).join("｜"),category:String(x.typeZh||x.type||"聽解"),typeZh:String(x.typeZh||x.type||"聽解"),explanationZh:String(x.explanationZh||""),choicesZh:Array.isArray(x.choicesZh)?x.choicesZh.map(v=>String(v||"").trim()):[],correctZh:String(x.correctZh||"").trim(),source:String(x.source||"GitHub 原創 JLPT 風格題")})).filter(x=>x.id&&/^N[1-5]$/.test(x.level)&&x.jp)'''
    new='''original=(d.items||[]).map(x=>({id:String(x.id||""),level:String(x.level||"").toUpperCase(),jp:String(x.jp||"").trim(),en:"",grammar:[String(x.typeZh||x.type||"聽解"),String(x.explanationZh||"")].filter(Boolean).join("｜"),category:String(x.typeZh||x.type||"聽解"),typeZh:String(x.typeZh||x.type||"聽解"),explanationZh:String(x.explanationZh||""),choicesZh:Array.isArray(x.choicesZh)?x.choicesZh.map(v=>String(v||"").trim()):[],correctZh:String(x.correctZh||"").trim(),source:String(x.source||"GitHub 原創 JLPT 風格題")})).filter(x=>x.id&&/^N[1-5]$/.test(x.level)&&x.jp).filter(x=>{const errs=listeningCatalogErrors(x);if(errs.length)console.warn("[listening QA] dropped",x.id,errs);return !errs.length})'''
    s=replace_once(s,old,new,'listening original filter')

    old='''if(new Set(rows.map(x=>mk(x.zh))).size!==4)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null}return shuffle(rows)'''
    new='''if(new Set(rows.map(x=>mk(x.zh))).size!==4)return null;const correctRow=rows.find(x=>x.jp===q.jp);if(!correctRow)return null;for(const r of rows){const peers=rows.filter(x=>x!==r).map(x=>zhChoiceSim(r.zh,x.zh));if(Math.max(...peers)<.18)return null;if(r!==correctRow){const a=normChoice(correctRow.zh),b=normChoice(r.zh),len=Math.min(a.length,b.length)/Math.max(1,Math.max(a.length,b.length));if(len<.58||zhChoiceSim(correctRow.zh,r.zh)<.14)return null}}return shuffle(rows)'''
    s=replace_once(s,old,new,'listening semantic gate')
    p.write_text(s,encoding='utf-8')
else:
    print('listening.html already has quality v1')

# ---------------- Mock exam ----------------
p=Path('mocktest.js')
s=p.read_text(encoding='utf-8')
if 'function questionQualityErrors(q)' not in s:
    old='''function qObj(o){return{id:o.id||`q-${Math.random().toString(36).slice(2)}`,type:o.type||"",score:o.score||"language",instruction:o.instruction||"",question:o.question||"",passage:o.passage||"",choices:o.choices||[],answer:o.answer??0,explain:o.explain||"",audioText:o.audioText||"",audioId:o.audioId||"",user:null,flag:false,audioPlayed:false}}'''
    new='''function qObj(o){return{id:o.id||`q-${Math.random().toString(36).slice(2)}`,type:o.type||"",score:o.score||"language",instruction:o.instruction||"",question:o.question||"",passage:o.passage||"",choices:o.choices||[],answer:o.answer??0,explain:o.explain||"",audioText:o.audioText||"",audioId:o.audioId||"",qa:o.qa||null,user:null,flag:false,audioPlayed:false}}
function qaNorm(s){return String(s||"").normalize("NFKC").replace(/[\\s　。、，,.！？!?「」『』【】（）()]/g,"")}
function questionQualityErrors(q){const e=[],cs=Array.isArray(q?.choices)?q.choices.map(x=>String(x||"").trim()):[];if(!q||!String(q.type||"").trim())e.push("missing-type");if(cs.length<3||cs.length>4)e.push("choice-count");if(cs.some(x=>!x))e.push("empty-choice");if(new Set(cs.map(qaNorm)).size!==cs.length)e.push("duplicate-choice");if(!Number.isInteger(q?.answer)||q.answer<0||q.answer>=cs.length)e.push("bad-answer-index");if(!String(q?.question||q?.passage||q?.audioText||"").trim())e.push("missing-content");if(q?.score==="listening"&&!String(q.audioText||"").trim())e.push("missing-listening-audio");if(q?.score==="reading"&&!String(q.passage||"").trim())e.push("missing-reading-passage");if(q?.type==="用法"){const m=String(q.question||"").match(/『([^』]+)』/),target=m?.[1]||"";if(target){const hits=cs.filter(x=>x.includes(target)).length;if(hits===1)e.push("usage-singleton-target-leak");if(hits>0&&hits<cs.length)e.push("usage-inconsistent-target")}}return e}
function qualityGate(arr,label="questions"){const ok=[],bad=[];for(const q of arr||[]){const errors=questionQualityErrors(q);if(errors.length)bad.push({id:q?.id||"?",errors});else ok.push(q)}if(bad.length)console.warn(`[mock QA] ${label}: dropped ${bad.length}/${(arr||[]).length}`,bad.slice(0,12));return ok}
function posBucket(s){s=String(s||"").toLowerCase();if(/noun|名詞/.test(s))return"noun";if(/verb|動詞/.test(s))return"verb";if(/adverb|副詞/.test(s))return"adverb";if(/adjective|形容/.test(s))return"adjective";if(/particle|助詞/.test(s))return"particle";return s.split(/[;,/|]/)[0].trim()||"other"}
function grammarFamily(e){e=String(e||"").replace(/[～〜]/g,"").trim();const tail=(e.match(/(こと|もの|わけ|よう|ため|ところ|ばかり|はず|ない|たい|そう|らしい)$/)||[])[1]||e.slice(-1),head=(e.match(/^(から|まで|より|ても|でも|には|では|とは|に|で|を|が|は|と|へ|も)/)||[])[1]||"";return{tail,head}}
function grammarChoiceCompatible(a,b){const A=grammarFamily(a),B=grammarFamily(b);return Math.abs([...String(a)].length-[...String(b)].length)<=5&&(A.tail===B.tail||A.head&&A.head===B.head)}'''
    s=replace_once(s,old,new,'mock qObj QA')

    old='''function buildContext(level,n){const p=vocab.filter(x=>x.level===level&&x.sentence&&x.word.length>0&&x.sentence.includes(x.word)),out=[];sample(p,Math.min(n*5,p.length)).forEach(c=>{if(out.length>=n)return;const d=similarWord(p,c).filter(x=>x.word.length<=8).slice(0,14);if(d.length<3)return;const cs=shuffle([c.word,...sample(d,3).map(x=>x.word)]),ans=cs.indexOf(c.word),sent=c.sentence.replace(c.word,"（　　　）");out.push(qObj({id:`cx-${c.id}`,type:"文脈規定",instruction:"（　　　）に入れるのに最もよいものを、一つ選んでください。",question:sent,choices:cs,answer:ans,explain:`正解：${c.word}（${c.reading}）／${c.meaning}`}))});return out}'''
    new='''function buildContext(level,n){const p=vocab.filter(x=>x.level===level&&x.sentence&&x.word.length>0&&x.sentence.includes(x.word)),out=[];sample(p,Math.min(n*6,p.length)).forEach(c=>{if(out.length>=n)return;let d=similarWord(p,c).filter(x=>x.word.length<=8),same=d.filter(x=>posBucket(x.pos)===posBucket(c.pos));if(same.length>=3)d=same;d=d.slice(0,18);if(d.length<3)return;const cs=shuffle([c.word,...sample(d,3).map(x=>x.word)]),ans=cs.indexOf(c.word),sent=c.sentence.replace(c.word,"（　　　）");out.push(qObj({id:`cx-${c.id}`,type:"文脈規定",instruction:"（　　　）に入れるのに最もよいものを、一つ選んでください。",question:sent,choices:cs,answer:ans,explain:`正解：${c.word}（${c.reading}）／${c.meaning}`}))});return out}'''
    s=replace_once(s,old,new,'mock vocab context')

    old='''function buildGrammarForm(level,n){const p=usableGrammar(level),exprs=[...new Set(p.map(x=>x.expr))],out=[];sample(p,Math.min(n*5,p.length)).forEach(c=>{if(out.length>=n)return;const ds=exprs.filter(x=>x!==c.expr&&Math.abs(x.length-c.expr.length)<=6);if(ds.length<3)return;const cs=shuffle([c.expr,...sample(ds,3)]),ans=cs.indexOf(c.expr),sent=c.jp.replace(c.expr,"（　　　）");out.push(qObj({id:`gf-${c.id}`,type:"文法形式の判断",instruction:"（　　　）に入れるのに最もよいものを、一つ選んでください。",question:sent,choices:cs,answer:ans,explain:`正確文法：${c.title}。原句：${c.jp}`}))});return out}'''
    new='''function buildGrammarForm(level,n){const p=usableGrammar(level),exprs=[...new Set(p.map(x=>x.expr))],out=[];sample(p,Math.min(n*8,p.length)).forEach(c=>{if(out.length>=n)return;let ds=exprs.filter(x=>x!==c.expr&&grammarChoiceCompatible(x,c.expr));if(ds.length<3)return;const cs=shuffle([c.expr,...sample(ds,3)]),ans=cs.indexOf(c.expr),sent=c.jp.replace(c.expr,"（　　　）");out.push(qObj({id:`gf-${c.id}`,type:"文法形式の判断",instruction:"（　　　）に入れるのに最もよいものを、一つ選んでください。",question:sent,choices:cs,answer:ans,explain:`正確文法：${c.title}。原句：${c.jp}`}))});return out}'''
    s=replace_once(s,old,new,'mock grammar compatible distractors')

    old='''function buildTextGrammar(level,n){const p=usableGrammar(level),out=[];for(let i=0;i<n*4&&p.length>3&&out.length<n;i++){const [a,b]=sample(p,2);if(a.id===b.id)continue;const ds=[...new Set(p.map(x=>x.expr).filter(x=>x!==b.expr&&Math.abs(x.length-b.expr.length)<=6))];if(ds.length<3)continue;const passage=`${a.jp}\\n${b.jp.replace(b.expr,"（　　　）")}`,cs=shuffle([b.expr,...sample(ds,3)]);out.push(qObj({id:`tg-${a.id}-${b.id}`,type:"文章の文法",instruction:"文章の流れに合うように、（　　　）に入れるのに最もよいものを一つ選んでください。",passage,question:"",choices:cs,answer:cs.indexOf(b.expr),explain:`正確文法：${b.title}。原句：${b.jp}`}))}return out}'''
    new='''function buildTextGrammar(level,n){return buildGrammarForm(level,n).map(q=>({...q,id:`tg-${q.id}`,type:"文脈文法",instruction:"文脈に合うように、（　　　）に入れるのに最もよいものを一つ選んでください。",passage:q.question,question:""}))}'''
    s=replace_once(s,old,new,'mock fake text grammar')

    marker='''function readingTypes(level){return level==="N1"?["短文理解","中文理解","長文理解","統合理解","主題理解"]:level==="N2"?["短文理解","中文理解","統合理解","主題理解"]:level==="N3"?["短文理解","中文理解","長文理解"]:["短文理解","中文理解"]}\n'''
    insert='''function sceneCombos(level){const d=ORIGINAL_SCENE_DATA[level];if(!d)return[];const out=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of d.actions)out.push({person,place,time,action});return shuffle(out)}
function buildReadingContent(level,n){const d=ORIGINAL_SCENE_DATA[level],out=[];if(!d)return out;const combos=sceneCombos(level);for(let i=0;i<combos.length&&out.length<n;i++){const x=combos[i],place2=d.places.find(v=>v!==x.place)||x.place,time2=d.times.find(v=>v!==x.time)||x.time,action2=d.actions.find(v=>v!==x.action)||x.action,act=x.action.replace(/。$/,""),act2=action2.replace(/。$/,""),v=i%3;let passage,question,correct,wrongs;if(v===0){passage=`${x.person}は${x.time}に${x.place}へ行き、${act}。そのあと${place2}へ行きます。`;question="最初に何をしますか。";correct=`${x.time}に${x.place}で${act}`;wrongs=[`${time2}に${x.place}で${act}`,`${x.time}に${place2}で${act}`,`${x.time}に${x.place}で${act2}`]}else if(v===1){passage=`${x.person}は最初${x.time}に${x.place}へ行く予定でした。しかし予定が変わり、${time2}に${place2}へ行って${act}。`;question="変更後の予定はどれですか。";correct=`${time2}に${place2}へ行く`;wrongs=[`${x.time}に${x.place}へ行く`,`${x.time}に${place2}へ行く`,`${time2}に${x.place}へ行く`]}else{passage=`${x.person}は${x.time}に${x.place}で${act}予定です。その前に${place2}で${act2}必要があります。`;question="先にする必要があることは何ですか。";correct=`${place2}で${act2}`;wrongs=[`${x.place}で${act}`,`${place2}で${act}`,`${x.place}で${act2}`]}const cs=shuffle([correct,...wrongs]);out.push(qObj({id:`rdq-${level}-${i}`,type:readingTypes(level)[i%readingTypes(level).length],score:"reading",instruction:"次の文章を読んで、内容と合うものを一つ選んでください。",passage,question,choices:cs,answer:cs.indexOf(correct),explain:`本文：${passage}`}))}return out}
function buildInfo(level,n){const out=[],families=[i=>{const t=15+i%3;return{p:`市民図書館\\n平日：9時～18時\\n休館日：毎週火曜日\\n土曜日：9時～${t}時`,c:`土曜日は${t}時まで利用できる。`,w:["土曜日は18時まで利用できる。","毎週木曜日が休館日だ。","毎日8時から利用できる。"]}},i=>{const t=19+i%2;return{p:`スポーツセンター\\nプール：10時～${t}時\\nトレーニング室：9時～21時\\n木曜日はプール清掃のため利用できません。`,c:"木曜日はプールを利用できない。",w:["木曜日は全施設が休みだ。",`プールは毎日21時まで使える。`,"トレーニング室は10時から開く。"]}},i=>{const fee=800+i*100;return{p:`市立美術館\\n開館：10時～17時\\n入館料：${fee}円\\n金曜日は20時まで延長\\n高校生以下は無料`,c:"金曜日は20時まで入館できる。",w:["毎日20時まで開いている。",`高校生も${fee}円必要だ。`,"開館は9時からだ。"]}}];for(let i=0;i<n;i++){const x=families[i%families.length](i),cs=shuffle([x.c,...x.w]);out.push(qObj({id:`info-${level}-${i}`,type:"情報検索",score:"reading",instruction:"次の案内を読んで、正しいものを一つ選んでください。",passage:x.p,choices:cs,answer:cs.indexOf(x.c),explain:`案内の記載：${x.c}`}))}return out}
'''
    if 'function buildReadingContent(level,n)' not in s:
        s=replace_once(s,marker,marker+insert,'mock reading generators')

    marker='''function listeningTypes(level){return level==="N1"||level==="N2"?["課題理解","ポイント理解","概要理解","統合理解"]:level==="N3"?["課題理解","ポイント理解","概要理解"]:["課題理解","ポイント理解"]}\n'''
    insert='''function tokenShadowedMock(s,x){for(const g of MUT_GROUPS)for(const longer of g){if(longer!==x&&longer.length>x.length&&longer.includes(x)&&s.includes(longer))return true}return false}
function safeMutate(s){const out=[];for(const g of MUT_GROUPS){for(const x of g){if(!s.includes(x)||tokenShadowedMock(s,x))continue;for(const y of g)if(y!==x){const z=s.replace(x,y);if(z!==s&&!out.includes(z))out.push(z)}}}const m=s.match(/\\d+/);if(m){const num=+m[0];for(const d of [-1,1,2]){const z=s.replace(m[0],String(Math.max(1,num+d)));if(z!==s&&!out.includes(z))out.push(z)}}return out}
function buildListeningContent(level,n){const p=shuffle(grammar[level].filter(x=>x.jp.length>=8&&x.jp.length<=75&&safeMutate(x.jp).length>=3)),out=[],types=listeningTypes(level);for(const c of p){if(out.length>=n)break;const alts=sample(safeMutate(c.jp),3);if(alts.length<3)continue;const cs=shuffle([c.jp,...alts]),type=types[out.length%types.length];out.push(qObj({id:`ls-${type}-${c.id}`,type,score:"listening",instruction:"音声を聞いて、内容と一致しているものを一つ選んでください。",choices:cs,answer:cs.indexOf(c.jp),explain:`音声の内容：${c.jp}`,audioText:c.jp,audioId:c.id.replace(/^g-/,"")}))}return out}
'''
    if 'function buildListeningContent(level,n)' not in s:
        s=replace_once(s,marker,marker+insert,'mock listening generator')

    old='''function buildListening(level,n){const qr=Math.min(3,(QUICK_RESPONSE[level]||[]).length),needsVerbal=["N3","N4","N5"].includes(level),verbal=needsVerbal?Math.min(2,(QUICK_RESPONSE[level]||[]).length):0,scene=Math.max(4,Math.round(n*.28));let candidates=[...buildQuickResponse(level,qr),...(verbal?buildQuickResponse(level,verbal,"発話表現"):[]),...buildOriginalScenes(level,scene+5),...buildListeningContent(level,n+8)];let out=takeDiverse(candidates,n);if(out.length<n)out=takeDiverse([...out,...buildOriginalScenes(level,n*2),...buildListeningContent(level,n*2)],n);return out}'''
    new='''function buildListening(level,n){const scene=Math.max(6,Math.round(n*.45));let candidates=[...buildOriginalScenes(level,scene+8),...buildListeningContent(level,n+12)];let out=qualityGate(takeDiverse(candidates,n),`listening-${level}`);if(out.length<n)out=qualityGate(takeDiverse([...out,...buildOriginalScenes(level,n*3),...buildListeningContent(level,n*3)],n),`listening-topup-${level}`);return out}'''
    s=replace_once(s,old,new,'mock remove weak quick response')

    old='''function buildVocab(level,n){let out=[];const parts=level==="N1"?[8,0,7,5]:[6,5,6,3];out.push(...buildKanji(level,parts[0]),...buildOrthography(level,parts[1]),...buildContext(level,parts[2]),...specialQs(level,parts[3]));if(out.length<n)out.push(...buildKanji(level,n-out.length));return sample(unique(out),n)}'''
    new='''function buildVocab(level,n){let out=[];const parts=level==="N1"?[8,0,7,5]:[6,5,6,3];out.push(...buildKanji(level,parts[0]),...buildOrthography(level,parts[1]),...buildContext(level,parts[2]),...specialQs(level,parts[3]));if(out.length<n)out.push(...buildKanji(level,n-out.length));return qualityGate(sample(unique(out),n),`vocab-${level}`)}'''
    s=replace_once(s,old,new,'mock vocab gate')

    old='''function buildGrammar(level,n){const a=Math.ceil(n*.5),b=Math.ceil(n*.25),c=n-a-b;let out=[...buildGrammarForm(level,a),...buildComposition(level,b),...buildTextGrammar(level,c)];if(out.length<n)out.push(...buildGrammarForm(level,n-out.length));return sample(unique(out),n)}'''
    new='''function buildGrammar(level,n){const a=Math.ceil(n*.55),b=Math.ceil(n*.25),c=n-a-b;let out=[...buildGrammarForm(level,a),...buildComposition(level,b),...buildTextGrammar(level,c)];if(out.length<n)out.push(...buildGrammarForm(level,n-out.length));return qualityGate(sample(unique(out),n),`grammar-${level}`)}'''
    s=replace_once(s,old,new,'mock grammar gate')

    old='''function buildReading(level,n){const info=Math.max(2,Math.round(n*.22)),content=n-info;let candidates=[...buildReadingContent(level,content+4),...buildInfo(level,info+4)];return takeDiverse(candidates,n)}'''
    new='''function buildReading(level,n){const info=Math.max(2,Math.round(n*.22)),content=n-info;let candidates=[...buildReadingContent(level,content+8),...buildInfo(level,info+6)];return qualityGate(takeDiverse(candidates,n),`reading-${level}`)}'''
    s=replace_once(s,old,new,'mock reading gate')

    old='''function buildSection(level,section,mode){const scale=mode==="quick"?.42:1,plan=Object.fromEntries(Object.entries(section.plan).map(([k,v])=>[k,Math.max(3,Math.round(v*scale))]));let qs=[];if(plan.vocab)qs.push(...buildVocab(level,plan.vocab));if(plan.grammar)qs.push(...buildGrammar(level,plan.grammar));if(plan.reading)qs.push(...buildReading(level,plan.reading));if(plan.listening)qs.push(...buildListening(level,plan.listening));return diversifyQuestions(level,qs)}'''
    new='''function buildSection(level,section,mode){const scale=mode==="quick"?.42:1,plan=Object.fromEntries(Object.entries(section.plan).map(([k,v])=>[k,Math.max(3,Math.round(v*scale))]));let qs=[];if(plan.vocab)qs.push(...buildVocab(level,plan.vocab));if(plan.grammar)qs.push(...buildGrammar(level,plan.grammar));if(plan.reading)qs.push(...buildReading(level,plan.reading));if(plan.listening)qs.push(...buildListening(level,plan.listening));return qualityGate(diversifyQuestions(level,qs),`section-${level}-${section.key}`)}'''
    s=replace_once(s,old,new,'mock section gate')

    old='''loadAll();\n})();'''
    new='''if(globalThis.__MOCKTEST_QA__){globalThis.__mockTestQA={loadAll,buildVocab,buildGrammar,buildReading,buildListening,buildTest,questionQualityErrors,qualityGate,qaCounts:()=>({vocab:vocab.length,grammar:Object.fromEntries(Object.entries(grammar).map(([k,v])=>[k,v.length]))})}}else loadAll();\n})();'''
    s=replace_once(s,old,new,'mock QA export')
    p.write_text(s,encoding='utf-8')
else:
    print('mocktest.js already has quality v1')

p=Path('mocktest.html')
h=p.read_text(encoding='utf-8')
h=re.sub(r'mocktest\\.js\\?v=[^"\\s<]+','mocktest.js?v=20260822-quality1',h)
p.write_text(h,encoding='utf-8')

print('quality patch complete')
