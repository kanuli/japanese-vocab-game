#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
changed=[]

def replace_once(path, old, new):
    p=ROOT/path
    s=p.read_text(encoding='utf-8')
    if new in s:
        return
    if old not in s:
        raise SystemExit(f'{path}: anchor not found: {old[:120]!r}')
    s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')
    changed.append(path)

# Severe catalog weaknesses are filtered at runtime rather than allowing obvious-answer items into a session.
old = 'function hasCatalogOptions(x){return !listeningCatalogErrorsV2(x).length}'
new = '''function hasCatalogOptions(x){return !listeningCatalogErrorsV2(x).length}
const EXTREME_CHOICE_V4=/一定|完全|永遠|絕對|全部|全都|永久|必定|毫無|任何[^，。]{0,8}都不/;
function zhCharSetV4(s){return new Set([...catalogNorm(s)].filter(c=>/[\\u3400-\\u9fff]/.test(c)))}
function zhOverlapV4(a,b){const A=zhCharSetV4(a),B=zhCharSetV4(b);if(!A.size||!B.size)return 0;let n=0;A.forEach(c=>{if(B.has(c))n++});return n/Math.max(1,Math.min(A.size,B.size))}
function catalogChoiceQualityV4(x){
 const errs=listeningCatalogErrorsV2(x);if(errs.length)return{pass:false,errors:errs,extremeWrong:0,nearMiss:0,lengthOutlier:0};
 const correct=String(x.correctZh||'').trim(),target=catalogNorm(correct),wrongs=(x.choicesZh||[]).map(v=>String(v||'').trim()).filter(v=>catalogNorm(v)!==target);
 const extremeWrong=wrongs.filter(w=>EXTREME_CHOICE_V4.test(w)&&!EXTREME_CHOICE_V4.test(correct)).length;
 const nearMiss=wrongs.filter(w=>zhOverlapV4(correct,w)>=.12).length;
 const base=Math.max(1,[...catalogNorm(correct)].length);const lengthOutlier=wrongs.filter(w=>{const r=[...catalogNorm(w)].length/base;return r<.45||r>2.2}).length;
 return{pass:extremeWrong<2&&lengthOutlier<2&&nearMiss>=1,errors:[],extremeWrong,nearMiss,lengthOutlier};
}'''
replace_once('listening.html',old,new)

old = 'function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&(hasCatalogOptions(x)||mutations(x.jp).length>=3));'
new = 'function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&((hasCatalogOptions(x)&&catalogChoiceQualityV4(x).pass)||(!hasCatalogOptions(x)&&rankedMutationsV4(x.jp).length>=3)));'
replace_once('listening.html',old,new)

old = '''function mutations(s){const out=[];for(const g of GROUPS){for(const x of g){if(!s.includes(x)||tokenShadowed(s,x))continue;for(const y of g){if(y!==x){const z=s.replace(x,y);if(z!==s&&!out.includes(z))out.push(z)}}}}const m=s.match(/\\d+/);if(m){const n=+m[0];for(const d of [-1,1,2]){const v=Math.max(1,n+d);const z=s.replace(m[0],String(v));if(z!==s&&!out.includes(z))out.push(z)}}return out}'''
new = '''function mutationFamiliesV4(s){const families=[];for(const g of GROUPS){for(const x of g){if(!s.includes(x)||tokenShadowed(s,x))continue;const a=[];for(const y of g){if(y===x)continue;const z=s.replace(x,y);if(z!==s&&!a.includes(z))a.push(z)}if(a.length)families.push(a)}}const m=s.match(/\\d+/);if(m){const n=+m[0],a=[];for(const d of [-2,-1,1,2]){const v=Math.max(1,n+d),z=s.replace(m[0],String(v));if(z!==s&&!a.includes(z))a.push(z)}if(a.length)families.push(a)}return families}
function mutations(s){return [...new Set(mutationFamiliesV4(s).flat())]}
function rankedMutationsV4(s){const f=mutationFamiliesV4(s).sort((a,b)=>b.length-a.length);const same=f.find(a=>a.length>=3);if(same)return [...same];const out=[];for(const a of f){for(const z of a){if(!out.includes(z))out.push(z)}}return out}'''
replace_once('listening.html',old,new)

old = '''function makeChoices(q){if(hasCatalogOptions(q))return{choicesZh:[...q.choicesZh],correctZh:q.correctZh,quality:"GitHub 原創題庫：四個相近語意選項"};const d=shuffle(mutations(q.jp));if(d.length<3)return null;return{choices:shuffle([q.jp,...d.slice(0,3)]),quality:"GitHub 基礎題：同一句只改一個關鍵細節"}}'''
new = '''function makeChoices(q){if(hasCatalogOptions(q)&&catalogChoiceQualityV4(q).pass)return{choicesZh:[...q.choicesZh],correctZh:q.correctZh,quality:"GitHub 原創題庫：通過全庫 quality gate 的四個近義情境選項"};const d=rankedMutationsV4(q.jp);if(d.length<3)return null;return{choices:shuffle([q.jp,...shuffle(d).slice(0,3)]),quality:"GitHub 基礎題：優先同一語意維度，只改一個關鍵細節"}}'''
replace_once('listening.html',old,new)

# Make the UI transparent that session availability is quality-filtered.
replace_once('listening.html','<div class="source"><strong>🎯 相似答案規則</strong><div class="muted">四個答案只使用同一句子並改一個關鍵細節，例如時間、方向、數字、程度或常見動詞；繁體中文翻譯也必須保持相似。任何一層不夠接近就會跳過該句，不使用不相關答案湊數。</div></div>',
'''<div class="source"><strong>🎯 相似答案規則</strong><div class="muted">原創 catalog 會先通過全庫 quality gate：排除多個極端送分錯項、長度明顯失衡或完全脫離同一情境的選項。Hanabira 基礎題優先在同一語意維度改一個關鍵細節，例如時間、方向、數字、程度或常見動詞；不足三個合理變體就不抽出。</div></div>''')

# Manifest records the durable batch-4 quality layer.
p=ROOT/'data/reference_upgrade_manifest.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['version']='2026-08-27-quality-depth-batch4-v1'
d['qualityDepthBatch4']={
  'scope':'full listening database quality audit: 6,690 original catalog plus remote Hanabira base examples',
  'runtime':['severe catalog distractor gate','same-semantic-dimension mutation preference','quality-filtered session pool'],
  'audit':'data/full_listening_quality_batch4_report.json',
  'copyright':'Hanabira examples are evaluated in-memory for aggregate QA; the audit report stores metrics, not copied example text.'
}
text=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
if p.read_text(encoding='utf-8')!=text:
    p.write_text(text,encoding='utf-8');changed.append(str(p.relative_to(ROOT)))
print(json.dumps({'changed':changed,'count':len(changed)},ensure_ascii=False))
