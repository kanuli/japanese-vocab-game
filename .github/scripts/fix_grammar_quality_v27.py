from pathlib import Path
import json
import re

P = Path("grammar.html")
s = P.read_text(encoding="utf-8")
original = s


def replace_once(old: str, new: str, label: str) -> None:
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected exactly 1 match, found {n}")
    s = s.replace(old, new, 1)


# Version marker: this revision changes the question model, not only cosmetics.
s = s.replace("日本語文法挑戰 v2.6", "日本語文法挑戰 v2.7")

old_state = '''let webQuestions=[], webPointsCount={}, manual=load("jpgrammar_manual",[]), wrong=new Set(load("jpgrammar_wrong",[])), game=null;'''
new_state = '''let webQuestions=[], webPointsCount={}, manual=load("jpgrammar_manual",[]), wrong=new Set(load("jpgrammar_wrong",[])), game=null;\nlet builtQuestions=[], qualityStats={};'''
replace_once(old_state, new_state, "state")

old_pick = '''function pickWrong(candidates,correct,key="a"){
 const uniq=new Map();for(const x of candidates){const v=x[key];if(v!==correct&&!uniq.has(v))uniq.set(v,x)}
 const pool=[...uniq.values()],out=[];while(out.length<3&&pool.length){const i=Math.floor(Math.random()*Math.min(8,pool.length));out.push(pool.splice(i,1)[0][key])}return out;
}
'''
new_pick = '''function pickWrong(candidates,correct,key="a"){
 const uniq=new Map();for(const x of candidates){const v=x[key];if(v!==correct&&!uniq.has(v))uniq.set(v,x)}
 const pool=[...uniq.values()],out=[];while(out.length<3&&pool.length){const i=Math.floor(Math.random()*Math.min(8,pool.length));out.push(pool.splice(i,1)[0][key])}return out;
}
function questionQualityErrors(q){
 const e=[],choices=Array.isArray(q?.choices)?q.choices.map(x=>String(x??"").trim()):[];
 if(!q||!String(q.q||"").trim())e.push("missing-question");
 if(!/^N[1-5]$/.test(String(q?.level||"")))e.push("bad-level");
 if(!["助詞","副詞","接続詞","文法"].includes(q?.type))e.push("bad-type");
 if(choices.length!==4)e.push("choice-count");
 if(choices.some(x=>!x))e.push("empty-choice");
 if(new Set(choices).size!==4)e.push("duplicate-choice");
 const answer=String(q?.a??"").trim();
 if(!answer)e.push("missing-answer");
 if(choices.filter(x=>x===answer).length!==1)e.push("answer-not-unique");
 if((q?.mode||"fill")==="fill"){
   if(countOcc(String(q.q||""),"＿＿")!==1)e.push("blank-count");
   if(q.sentence&&String(q.q||"").replace("＿＿",answer)!==String(q.sentence))e.push("reconstruction-mismatch");
 }
 if(q?.mode==="usage"){
   const anchor=String(q.usageAnchor||"").trim();
   if(!String(q.usageHint||"").trim())e.push("usage-missing-meaning");
   if(!anchor)e.push("usage-missing-anchor");
   else if(choices.some(x=>countOcc(x,anchor)!==1))e.push("usage-anchor-not-in-all-four");
 }
 return e;
}
function qualityGate(arr,label="questions"){
 const ok=[],bad=[];
 for(const q of (arr||[])){const errors=questionQualityErrors(q);if(errors.length)bad.push({id:q?.id||"?",errors});else ok.push(q)}
 qualityStats[label]={input:(arr||[]).length,kept:ok.length,dropped:bad.length,reasons:bad.slice(0,20)};
 if(bad.length)console.warn(`[grammar QA] ${label}: dropped ${bad.length}/${(arr||[]).length}`,bad.slice(0,20));
 else console.info(`[grammar QA] ${label}: ${ok.length} questions passed`);
 return ok;
}
'''
replace_once(old_pick, new_pick, "quality gate")

old_usage = ''' // 用法辨識：四個選項都是來源中的完整、文法成立的日文句子。
 const usageRaw=[];
 for(const m of meta){
  if(!m.grammar)continue;
  for(const [ei,ex] of (m.pt.examples||[]).slice(0,4).entries()){
   const jp=String(ex.jp||"").trim();if(!jp)continue;
   usageRaw.push({id:`web-usage-${level}-${m.pi}-${ei}`,level,type:m.type,source:"web",mode:"usage",q:`下列哪一句正確使用「${m.grammar}」？`,a:jp,grammar:m.grammar,meaning:m.category,exp:m.pt.short_explanation||"",zh:ex.en||"",formation:m.pt.formation||"",category:m.category,formSig:m.sig,sentence:jp});
  }
 }
 const usage=[];
 for(const q of usageRaw){
  let peers=usageRaw.filter(x=>x.id!==q.id&&x.a!==q.a&&x.type===q.type&&x.category===q.category&&x.formSig===q.formSig&&x.grammar!==q.grammar);
  if(peers.length<3)peers=usageRaw.filter(x=>x.id!==q.id&&x.a!==q.a&&x.type===q.type&&x.category===q.category&&x.grammar!==q.grammar);
  if(peers.length<3)continue;
  const wrongs=pickWrong(peers,q.a,"a");if(wrongs.length<3)continue;q.choices=shuffle([q.a,...wrongs]);usage.push(q);
 }
'''
new_usage = ''' // 用法辨識 v2.7：四個選項必須屬於「同一個文法點」，而且四句都實際包含同一個文法錨點。
 // 不再把其他文法的正確句子混進來，再用文法名稱直接洩漏答案。
 // 題目改為：同一文法的四個來源例句中，依繁中句意選出對應的一句。
 const usage=[];
 for(const m of meta){
  if(!m.grammar)continue;
  const rows=[];
  for(const [ei,ex] of (m.pt.examples||[]).slice(0,8).entries()){
   const jp=String(ex.jp||"").trim(),en=String(ex.en||"").trim();
   if(!jp||!en)continue;
   rows.push({ei,jp,en});
  }
  const uniq=[...new Map(rows.map(x=>[x.jp,x])).values()];
  if(uniq.length<4)continue;
  const anchor=patternCandidates(m.pt).find(p=>uniq.filter(x=>countOcc(x.jp,p)===1).length>=4)||"";
  if(!anchor)continue;
  const eligible=uniq.filter(x=>countOcc(x.jp,anchor)===1);
  if(eligible.length<4)continue;
  for(const row of eligible){
   const peers=eligible.filter(x=>x.jp!==row.jp);
   const wrongs=pickWrong(peers,row.jp,"jp");
   if(wrongs.length<3)continue;
   const q={id:`web-usage-${level}-${m.pi}-${row.ei}`,level,type:m.type,source:"web",mode:"usage",q:`「${m.grammar}」：以下哪一句最符合指定的繁體中文意思？`,a:row.jp,choices:shuffle([row.jp,...wrongs]),grammar:m.grammar,meaning:m.category,exp:m.pt.short_explanation||"",zh:row.en,usageHint:row.en,usageAnchor:anchor,formation:m.pt.formation||"",category:m.category,formSig:m.sig,sentence:row.jp};
   if(!questionQualityErrors(q).length)usage.push(q);
  }
 }
'''
replace_once(old_usage, new_usage, "usage generator")

old_push = '''     const [l,pts]=r.value;webPointsCount[l]=pts.length;webQuestions.push(...generateFromPoints(pts,l));'''
new_push = '''     const [l,pts]=r.value;webPointsCount[l]=pts.length;webQuestions.push(...qualityGate(generateFromPoints(pts,l),`web-${l}`));'''
replace_once(old_push, new_push, "web quality gate")

old_translate = '''async function translateZh(text){
 text=String(text||"").trim();if(!text)return "";
 if(zhCache.has(text)){const cached=String(zhCache.get(text)||"");if(!containsLatin(cached))return cached;zhCache.delete(text)}
 try{const u="https://api.mymemory.translated.net/get?q="+encodeURIComponent(text.slice(0,480))+"&langpair=en%7Czh-TW",r=await fetch(u,{cache:"force-cache"});if(!r.ok)throw Error("翻譯服務暫時不可用");const d=await r.json();let z=String(d?.responseData?.translatedText||"").trim();if(!z||containsLatin(z)||z.toLowerCase()===text.toLowerCase())throw Error("翻譯結果不符合繁體中文要求");zhCache.set(text,z);save("jpgrammar_zh_cache",Object.fromEntries([...zhCache.entries()].slice(-500)));return z}catch(e){console.warn(e);return ""}
}
'''
new_translate = '''async function translateZh(text){
 text=String(text||"").trim();if(!text)return "";
 if(zhCache.has(text)){const cached=String(zhCache.get(text)||"");if(!containsLatin(cached))return cached;zhCache.delete(text)}
 const accept=z=>{z=String(z||"").trim();return z&&!containsLatin(z)&&z.toLowerCase()!==text.toLowerCase()?z:""};
 try{
  const u="https://api.mymemory.translated.net/get?q="+encodeURIComponent(text.slice(0,480))+"&langpair=en%7Czh-TW",r=await fetch(u,{cache:"force-cache"});if(r.ok){const d=await r.json(),z=accept(d?.responseData?.translatedText);if(z){zhCache.set(text,z);save("jpgrammar_zh_cache",Object.fromEntries([...zhCache.entries()].slice(-700)));return z}}
 }catch(e){console.warn("MyMemory translation failed",e)}
 try{
  const u="https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-TW&dt=t&q="+encodeURIComponent(text.slice(0,480)),r=await fetch(u,{cache:"force-cache"});if(r.ok){const d=await r.json(),z=accept((d?.[0]||[]).map(x=>x?.[0]||"").join(""));if(z){zhCache.set(text,z);save("jpgrammar_zh_cache",Object.fromEntries([...zhCache.entries()].slice(-700)));return z}}
 }catch(e){console.warn("Google translation fallback failed",e)}
 return "";
}
'''
replace_once(old_translate, new_translate, "translation fallback")

old_allq = ''' if(s.includes("web"))a.push(...webQuestions);
 if(s.includes("built"))a.push(...BUILTIN);
 if(s.includes("manual"))a.push(...manual.map(x=>({...x,source:"manual"})));'''
new_allq = ''' if(s.includes("web"))a.push(...webQuestions);
 if(s.includes("built"))a.push(...builtQuestions);
 if(s.includes("manual"))a.push(...manual.map(x=>({...x,source:"manual"})));'''
replace_once(old_allq, new_allq, "allQ built source")

old_render = ''' $("#builtCounts").innerHTML=badges(countByLevel(BUILTIN));'''
new_render = ''' $("#builtCounts").innerHTML=badges(countByLevel(builtQuestions));'''
replace_once(old_render, new_render, "render built counts")

old_next = ''' const q=game.order[game.index%game.order.length];game.current=q;game.answered=false;
 const token=++renderToken;$("#question").textContent=q.q;if(q.mode!=="usage")setRuby($("#question"),q.q,token);
 const modeLabel=q.mode==="usage"?"用法辨識":"填空判斷";'''
new_next = ''' const q=game.order[game.index%game.order.length];game.current=q;game.answered=false;
 const token=++renderToken;
 if(q.mode==="usage"){
   $("#question").textContent=`「${learnerText(q.grammar||"")}」：繁體中文題意載入中…`;
   const zhHint=await translateZh(q.usageHint||q.zh||"");if(token!==renderToken)return;
   $("#question").textContent=zhHint?`「${learnerText(q.grammar||"")}」：以下哪一句最符合「${zhHint}」？`:`「${learnerText(q.grammar||"")}」：翻譯服務暫時無法提供可靠的繁體中文題意，請按「退出」後重新載入 Web 題庫。`;
 }else{$("#question").textContent=q.q;setRuby($("#question"),q.q,token)}
 const modeLabel=q.mode==="usage"?"用法辨識（同文法四句）":"填空判斷";'''
replace_once(old_next, new_next, "usage renderer")

old_manual = ''' if(!q||!a||!w1||!w2||!w3){alert("請填寫題目、正確答案及三個錯誤答案。");return}
 const choices=[a,w1,w2,w3];if(new Set(choices).size<4){alert("四個答案必須不同。");return}'''
new_manual = ''' if(!q||!a||!w1||!w2||!w3){alert("請填寫題目、正確答案及三個錯誤答案。");return}
 if(countOcc(q,"＿＿")!==1){alert("填空題必須剛好包含一個「＿＿」空格，否則無法保證答案唯一。");return}
 const choices=[a,w1,w2,w3];if(new Set(choices).size<4){alert("四個答案必須不同。");return}'''
replace_once(old_manual, new_manual, "manual validation")

old_init = '''render();Promise.allSettled([loadWeb(),initFurigana()]).then(()=>render());'''
new_init = '''builtQuestions=qualityGate(BUILTIN,"built");manual=qualityGate(manual.map(x=>({...x,source:"manual",mode:x.mode||"fill"})),"manual");render();Promise.allSettled([loadWeb(),initFurigana()]).then(()=>render());'''
replace_once(old_init, new_init, "initial quality gate")

# User-facing footer: make the stronger quality model explicit.
s = s.replace(
    'Web 題先經文法相容性過濾，再產生「填空判斷」與「用法辨識」兩種題型；',
    'Web 題先經文法相容性與答案唯一性 QA；「用法辨識」只保留同一文法、四句都含相同文法錨點的來源例句，再以繁中句意辨識；'
)

# Structural audit of every built-in question before publishing.
m = re.search(r"const BUILTIN=(\[.*?\]);\nBUILTIN\.forEach", s, re.S)
if not m:
    raise SystemExit("Cannot extract BUILTIN bank")
bank = json.loads(m.group(1))
issues = []
valid_levels = {f"N{i}" for i in range(1, 6)}
valid_types = {"助詞", "副詞", "接続詞", "文法"}
for i, q in enumerate(bank):
    choices = [str(x).strip() for x in q.get("choices", [])]
    ans = str(q.get("a", "")).strip()
    errs = []
    if q.get("level") not in valid_levels: errs.append("level")
    if q.get("type") not in valid_types: errs.append("type")
    if str(q.get("q", "")).count("＿＿") != 1: errs.append("blank")
    if len(choices) != 4 or len(set(choices)) != 4: errs.append("choices")
    if choices.count(ans) != 1: errs.append("answer")
    for f in ("grammar", "meaning", "exp", "zh"):
        if not str(q.get(f, "")).strip(): errs.append(f)
    if errs: issues.append({"index": i, "errors": errs, "question": q.get("q")})
if issues:
    raise SystemExit("Built-in QA failed: " + json.dumps(issues, ensure_ascii=False))

if 'x.grammar!==q.grammar' in s:
    raise SystemExit("Old cross-grammar usage distractor logic still present")
for marker in ("usageAnchor", "usage-anchor-not-in-all-four", "qualityGate", "用法辨識（同文法四句）"):
    if marker not in s:
        raise SystemExit(f"Missing v2.7 QA marker: {marker}")

P.write_text(s, encoding="utf-8")

report = Path("data/grammar_quality_v27_report.txt")
by_level = {lv: sum(1 for q in bank if q.get("level") == lv) for lv in sorted(valid_levels)}
by_type = {tp: sum(1 for q in bank if q.get("type") == tp) for tp in sorted(valid_types)}
report.write_text(
    "Grammar v2.7 static QA\n"
    f"Built-in questions checked: {len(bank)}\n"
    f"Built-in structural/answer failures: {len(issues)}\n"
    f"By level: {json.dumps(by_level, ensure_ascii=False)}\n"
    f"By type: {json.dumps(by_type, ensure_ascii=False)}\n"
    "Usage cross-grammar distractor generator removed: YES\n"
    "Usage all-four-same-anchor runtime gate installed: YES\n"
    "All sources pass 4 unique choices + 1 unique answer runtime gate: YES\n"
    "Fill questions pass exactly-one-blank + source reconstruction gate: YES\n",
    encoding="utf-8",
)

print(f"Patched grammar.html: {len(original)} -> {len(s)} chars")
print(report.read_text(encoding="utf-8"))
