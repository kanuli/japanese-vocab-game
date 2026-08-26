#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
changed = []


def write_if_changed(path: str, text: str):
    p = ROOT / path
    old = p.read_text(encoding='utf-8')
    if old != text:
        p.write_text(text, encoding='utf-8')
        changed.append(path)


def require(text: str, needle: str, path: str):
    if needle not in text:
        raise SystemExit(f'{path}: required patch anchor not found: {needle[:100]!r}')


def add_after_once(s: str, anchor: str, addition: str, path: str):
    if addition in s:
        return s
    require(s, anchor, path)
    return s.replace(anchor, anchor + '\n' + addition, 1)


def patch_grammar():
    path = 'grammar.html'
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if 'grammar-reference-expansion.js' not in s:
        anchor = '<script>\n(()=>{"use strict";'
        require(s, anchor, path)
        s = s.replace(anchor, '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
    s = add_after_once(s,
        '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>',
        '<script src="./grammar-gap-expansion.js?v=20260827v1"></script>', path)
    if 'window.REFERENCE_GRAMMAR_EXPANSION' not in s:
        anchor = 'const BUILTIN=[{'
        require(s, anchor, path)
        s = s.replace(anchor, 'const BUILTIN=[...(window.REFERENCE_GRAMMAR_EXPANSION||[]),{', 1)
    s = s.replace('助詞・副詞・接続詞・文法表現｜Web 題庫 + ふりがな',
                  '助詞・副詞・接続詞・文法表現｜Web 題庫 + 原創 cross-reference coverage + ふりがな')
    s = s.replace('60 題原創繁體中文解說，Web 無法載入時仍可使用。',
                  '168 題本站原創繁體中文題目（原有 60 + cross-reference 96 + coverage-gap 12），Web 無法載入時仍可使用。')
    s = s.replace('156 題本站原創繁體中文題目（原有 60 + cross-reference 96），Web 無法載入時仍可使用。',
                  '168 題本站原創繁體中文題目（原有 60 + cross-reference 96 + coverage-gap 12），Web 無法載入時仍可使用。')
    s = s.replace('BUILTIN.forEach((x,i)=>{x.id="built-"+i;x.source="built";x.mode="fill"});',
                  'BUILTIN.forEach((x,i)=>{x.id=x.id||("built-"+i);x.source=x.source||"built";x.mode=x.mode||"fill"});')
    old='$("#aSource").textContent=q.source==="manual"?"手動題目":q.source==="project-original-cross-reference"?"本站原創 cross-reference 題庫":"內置繁中題庫";'
    new='$("#aSource").textContent=q.source==="manual"?"手動題目":String(q.source||"").includes("cross-reference")?"本站原創 cross-reference 題庫":String(q.source||"").includes("coverage-gap")?"本站原創 coverage-gap 題庫":"內置繁中題庫";'
    s = s.replace(old,new)
    s = s.replace('ふりがな由本地 Kuromoji 字典產生。JLPT 等級為學習用分類，並非官方固定文法清單。</div>',
                  'ふりがな由本地 Kuromoji 字典產生。另加入本站原創 cross-reference 文法 coverage，參考官方 JLPT 能力描述及多來源學習分類，但不複製外部教材例句。JLPT 等級為學習用分類，並非官方固定文法清單。</div>')
    write_if_changed(path, s)


def patch_listening():
    path = 'listening.html'
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if 'listening-reference-expansion.js' not in s:
        anchor = '<script>\n(()=>{"use strict";'
        require(s, anchor, path)
        s = s.replace(anchor, '<script src="./listening-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
    s = add_after_once(s,
        '<script src="./listening-reference-expansion.js?v=20260826v1"></script>',
        '<script src="./listening-gap-expansion.js?v=20260827v1"></script>', path)
    s = add_after_once(s,
        '<script src="./listening-gap-expansion.js?v=20260827v1"></script>',
        '<script src="./listening-gap-topup.js?v=20260827v1"></script>', path)
    s = add_after_once(s,
        '<script src="./listening-gap-topup.js?v=20260827v1"></script>',
        '<script src="./listening-gap-topup-batch2.js?v=20260827v2"></script>', path)
    if '...reference]' not in s:
        anchor = 'items=[...base,...original];'
        require(s, anchor, path)
        repl = 'const reference=Array.isArray(window.REFERENCE_LISTENING_EXPANSION)?window.REFERENCE_LISTENING_EXPANSION:[];items=[...base,...original,...reference];'
        s = s.replace(anchor, repl, 1)
    s = s.replace('const complete=items.length===10000&&Object.values(c).every(v=>v===2000);',
                  'const complete=items.length>=10000&&Object.values(c).every(v=>v>=2000);')
    s = s.replace('正在合併 GitHub 6,690 原創題 + 3,310 基礎題…',
                  '正在合併 GitHub 題庫與本站原創 cross-reference 聽解擴充…')
    s = s.replace('complete?"✅ GitHub 合併題庫完成：10,000 筆（N1–N5 每級 2,000）。遊戲會自動去除重複日文句子。":',
                  'complete?`✅ GitHub 合併題庫完成：${items.length.toLocaleString()} 筆（N1–N5 均達至少 2,000 題；含本站原創 cross-reference coverage）。遊戲會自動去除重複日文句子。`:')
    s = s.replace("p=p.filter(voicevoxQuestionAvailable);",
                  "p=p.filter(x=>voicevoxQuestionAvailable(x)||String(x?.source||'').includes('cross-reference')||String(x?.source||'').includes('coverage-gap'));", 1)
    s = s.replace("p=p.filter(x=>voicevoxQuestionAvailable(x)||String(x?.source||'').includes('cross-reference'));",
                  "p=p.filter(x=>voicevoxQuestionAvailable(x)||String(x?.source||'').includes('cross-reference')||String(x?.source||'').includes('coverage-gap'));", 1)
    s = s.replace('GitHub 10,000 題 → 日語發音 → 4 個清楚關鍵差異答案',
                  'GitHub 10,000+ 題 + 原創 communicative coverage → 日語發音 → 4 個清楚關鍵差異答案')
    write_if_changed(path, s)


def patch_conversation():
    path = 'conversation.html'
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if 'conversation-reference-expansion.js' not in s:
        anchor = '<script src="./conversation-world-expansion.js?v=20260815v1"></script>'
        require(s, anchor, path)
        s = s.replace(anchor, anchor + '\n<script src="./conversation-reference-expansion.js?v=20260826v1"></script>', 1)
    s = add_after_once(s,
        '<script src="./conversation-reference-expansion.js?v=20260826v1"></script>',
        '<script src="./conversation-gap-expansion.js?v=20260827v1"></script>', path)
    s = add_after_once(s,
        '<script src="./conversation-gap-expansion.js?v=20260827v1"></script>',
        '<script src="./conversation-function-topup.js?v=20260827v2"></script>', path)
    s = s.replace('N1–N5｜61 個真實生活場景｜1,525 組會話｜每個場景每級 5 組｜聽力・跟讀・聽寫',
                  'N1–N5｜77 個真實生活場景｜1,925 組會話｜每個場景每級 5 組｜聽力・跟讀・聽寫')
    s = s.replace('日本語・場面別會話 v2.0｜61 場景 × 每場景 25 組 = 1,525 組會話',
                  '日本語・場面別會話 v2.1｜77 場景 × 每場景 25 組 = 1,925 組會話')
    write_if_changed(path, s)


def patch_mocktest():
    html_path = 'mocktest.html'
    hp = ROOT / html_path
    h = hp.read_text(encoding='utf-8')
    if 'grammar-reference-expansion.js' not in h:
        anchor = '<script src="./mocktest.js?v=20260822-quality5"></script>'
        require(h, anchor, html_path)
        h = h.replace(anchor, '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
    h = add_after_once(h,
        '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>',
        '<script src="./grammar-gap-expansion.js?v=20260827v1"></script>', html_path)
    write_if_changed(html_path, h)

    js_path = 'mocktest.js'
    jp = ROOT / js_path
    s = jp.read_text(encoding='utf-8')
    if 'mock-ref-grammar' not in s:
        anchor = 'vocab=v;["N1","N2","N3","N4","N5"].forEach((l,i)=>grammar[l]=gs[i]);clearTimeout(slow);'
        require(s, anchor, js_path)
        repl = '''vocab=v;["N1","N2","N3","N4","N5"].forEach((l,i)=>grammar[l]=gs[i]);const rg=Array.isArray(window.REFERENCE_GRAMMAR_EXPANSION)?window.REFERENCE_GRAMMAR_EXPANSION:[];for(const l of ["N1","N2","N3","N4","N5"]){const extra=rg.filter(x=>x.level===l&&x.q&&x.a).map((x,i)=>({id:`mock-ref-grammar-${l}-${i}`,level:l,title:x.grammar||"原創文法",expr:grammarExpr(x.grammar||""),jp:String(x.q).replace("＿＿",String(x.a))}));grammar[l]=uniqBy([...grammar[l],...extra],x=>`${x.level}|${x.jp}`)}clearTimeout(slow);'''
        s = s.replace(anchor, repl, 1)
    write_if_changed(js_path, s)


def update_manifest():
    path = 'data/reference_upgrade_manifest.json'
    data = {
        'version': '2026-08-27-gap-v3',
        'policy': 'data/CONTENT_REFERENCE_POLICY.md',
        'referenceMap': 'data/content_reference_map.json',
        'expansions': {
            'grammar': ['grammar-reference-expansion.js','grammar-gap-expansion.js'],
            'listening': ['listening-reference-expansion.js','listening-gap-expansion.js','listening-gap-topup.js','listening-gap-topup-batch2.js'],
            'conversation': ['conversation-reference-expansion.js','conversation-gap-expansion.js','conversation-function-topup.js']
        },
        'integratedPages': ['grammar.html', 'listening.html', 'conversation.html', 'mocktest.html', 'mocktest.js'],
        'sharedPagesReviewed': {
            'vocabulary': ['index.html', 'wordlist.html', 'wordaudio.html', 'vocab-plus-game.html', 'vocabulary-plus.html'],
            'pronunciation': ['pronunciation.html'],
            'utility': ['translator.html']
        },
        'notes': [
            'Vocabulary pages continue using the shared world-evidence calibration layer instead of a new duplicate level system.',
            'Targeted grammar gap: N4 passive coverage.',
            'Listening batch 2 raises every targeted sparse subtype to at least five unique expansion examples after sentence deduplication.',
            'Conversation batch 2 fills N4 change/reschedule and recommendation, N3 procedure, and N2 exception communicative-function gaps without increasing scene count.',
            'Pronunciation inherits verified readings; raw count is not expanded independently.',
            'Translator remains a utility and is not treated as a JLPT database.'
        ]
    }
    p = ROOT / path
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if not p.exists() or p.read_text(encoding='utf-8') != text:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        changed.append(path)


patch_grammar()
patch_listening()
patch_conversation()
patch_mocktest()
update_manifest()
print(json.dumps({'changed': changed, 'count': len(changed)}, ensure_ascii=False))
