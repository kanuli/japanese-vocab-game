from pathlib import Path
import runpy
import re

# Apply the base repair first. It is intentionally idempotent.
runpy.run_path('.github/scripts/fix_listening_mock_quality_v1.py', run_name='__main__')

# ---- Listening: validate source structure at load time; validate rendered Chinese at play time. ----
p=Path('listening.html')
s=p.read_text(encoding='utf-8')
if 'function listeningCatalogErrorsV2' not in s:
    pat=r'function listeningCatalogErrors\(x\)\{.*?return e\}\nfunction hasCatalogOptions\(x\)\{return !listeningCatalogErrors\(x\)\.length\}'
    repl='''function listeningCatalogErrorsV2(x){const e=[],cs=Array.isArray(x?.choicesZh)?x.choicesZh.map(v=>String(v||"").trim()):[],correct=String(x?.correctZh||"").trim();if(cs.length!==4)e.push("choice-count");if(cs.some(v=>!v))e.push("empty-choice");const keys=cs.map(catalogNorm);if(new Set(keys).size!==4)e.push("duplicate-choice");const target=catalogNorm(correct);if(!target||keys.filter(k=>k===target).length!==1)e.push("answer-not-unique");return e}
function hasCatalogOptions(x){return !listeningCatalogErrorsV2(x).length}'''
    s,n=re.subn(pat,repl,s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'listening structural gate replacement failed: {n}')
    s=s.replace('const errs=listeningCatalogErrors(x);','const errs=listeningCatalogErrorsV2(x);')
    # Keep the existing every-option-needs-a-similar-peer test, but do not reject
    # authored alternatives only because they use different words from the correct answer.
    old='''if(r!==correctRow){const a=normChoice(correctRow.zh),b=normChoice(r.zh),len=Math.min(a.length,b.length)/Math.max(1,Math.max(a.length,b.length));if(len<.58||zhChoiceSim(correctRow.zh,r.zh)<.14)return null}'''
    new='''if(r!==correctRow){const a=normChoice(correctRow.zh),b=normChoice(r.zh),len=Math.min(a.length,b.length)/Math.max(1,Math.max(a.length,b.length));if(len<.45)return null}'''
    if old not in s: raise SystemExit('listening rendered-choice gate marker missing')
    s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')

# ---- Mock exam: ensure generator QA never reduces required exam question counts. ----
p=Path('mocktest.js')
s=p.read_text(encoding='utf-8')
if 'function uniqBy(a,key)' not in s:
    needle='function unique(a){const seen=new Set;return a.filter(x=>{const k=(x&&typeof x==="object")?(x.id||JSON.stringify(x)):String(x);if(seen.has(k))return false;seen.add(k);return true})}\n'
    if needle not in s: raise SystemExit('unique helper marker missing')
    s=s.replace(needle,needle+'function uniqBy(a,key){const seen=new Set;return a.filter(x=>{const k=key(x);if(seen.has(k))return false;seen.add(k);return true})}\n',1)

    s=s.replace('const d=similarReading(p,c).slice(0,8);','const d=uniqBy(similarReading(p,c),x=>x.reading).slice(0,10);')
    s=s.replace('const d=similarWord(p,c).slice(0,10);','const d=uniqBy(similarWord(p,c),x=>x.word).slice(0,12);')
    s=s.replace('let d=similarWord(p,c).filter(x=>x.word.length<=8),same=d.filter(x=>posBucket(x.pos)===posBucket(c.pos));','let d=uniqBy(similarWord(p,c).filter(x=>x.word.length<=8),x=>x.word),same=d.filter(x=>posBucket(x.pos)===posBucket(c.pos));')

    # Sentence-order questions can contain repeated chunks, so raw permutations can
    # collapse to the same visible answer. Deduplicate by normalized visible string.
    pat=r'function buildComposition\(level,n\)\{.*?return out\}'
    repl='''function buildComposition(level,n){const p=grammar[level].filter(x=>x.jp.length>=12&&x.jp.length<=55),out=[];sample(p,Math.min(n*10,p.length)).forEach(c=>{if(out.length>=n)return;const chunks=splitChunks(c.jp);if(!chunks)return;const correct=chunks.join(" "),seen=new Set([qaNorm(correct)]),wrong=[];for(const perm of shuffle(permutations4(chunks))){const z=perm.join(" "),k=qaNorm(z);if(seen.has(k))continue;seen.add(k);wrong.push(z);if(wrong.length===3)break}if(wrong.length<3)return;const cs=shuffle([correct,...wrong]),ans=cs.indexOf(correct);out.push(qObj({id:`gc-${c.id}`,type:"文の組み立て",instruction:"次の文を正しい順序に並べたものを、一つ選んでください。",question:`① ${chunks[0]}　② ${chunks[1]}　③ ${chunks[2]}　④ ${chunks[3]}`,choices:cs,answer:ans,explain:`正しい文：${c.jp}`}))});return out}'''
    s,n=re.subn(pat,repl,s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'buildComposition replacement failed: {n}')

    # QA may reject a malformed candidate. Generate a reserve pool and top up so a
    # formal mock never silently loses a question.
    pat=r'function buildVocab\(level,n\)\{.*?\}\nfunction usableGrammar'
    repl='''function buildVocab(level,n){let out=[];const parts=level==="N1"?[8,0,7,5]:[6,5,6,3];out.push(...buildKanji(level,parts[0]),...buildOrthography(level,parts[1]),...buildContext(level,parts[2]),...specialQs(level,parts[3]));let gated=qualityGate(sample(unique(out),n),`vocab-${level}`);if(gated.length<n){const reserve=qualityGate(unique([...buildKanji(level,n*2),...buildOrthography(level,n),...buildContext(level,n)]),`vocab-reserve-${level}`);gated=unique([...gated,...reserve])}return sample(gated,n)}
function usableGrammar'''
    s,n=re.subn(pat,repl,s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'buildVocab topup replacement failed: {n}')

    pat=r'function buildGrammar\(level,n\)\{.*?\}\nconst MUT_GROUPS='
    repl='''function buildGrammar(level,n){const a=Math.ceil(n*.55),b=Math.ceil(n*.25),c=n-a-b;let out=[...buildGrammarForm(level,a+3),...buildComposition(level,b+3),...buildTextGrammar(level,c+3)];let gated=qualityGate(unique(out),`grammar-${level}`);if(gated.length<n){const reserve=qualityGate(unique([...buildGrammarForm(level,n*2),...buildComposition(level,n)]),`grammar-reserve-${level}`);gated=unique([...gated,...reserve])}return sample(gated,n)}
const MUT_GROUPS='''
    s,n=re.subn(pat,repl,s,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'buildGrammar topup replacement failed: {n}')
    p.write_text(s,encoding='utf-8')

print('quality v2 refinement complete')
