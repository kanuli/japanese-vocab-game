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


def patch_grammar():
    path = 'grammar.html'
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if 'grammar-reference-expansion.js' not in s:
        anchor = '<script>\n(()=>{"use strict";'
        require(s, anchor, path)
        s = s.replace(anchor, '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
    if 'window.REFERENCE_GRAMMAR_EXPANSION' not in s:
        anchor = 'const BUILTIN=[{'
        require(s, anchor, path)
        s = s.replace(anchor, 'const BUILTIN=[...(window.REFERENCE_GRAMMAR_EXPANSION||[]),{', 1)
    s = s.replace('助詞・副詞・接続詞・文法表現｜Web 題庫 + ふりがな',
                  '助詞・副詞・接続詞・文法表現｜Web 題庫 + 原創 cross-reference coverage + ふりがな')
    write_if_changed(path, s)


def patch_listening():
    path = 'listening.html'
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if 'listening-reference-expansion.js' not in s:
        anchor = '<script>\n(()=>{"use strict";'
        require(s, anchor, path)
        s = s.replace(anchor, '<script src="./listening-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
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
    # Reference scripts do not yet have pre-recorded VOICEVOX sprites. The existing speak() path
    # safely falls back to Supertonic/device Japanese when VOICEVOX has no record, so keep these
    # questions selectable rather than hiding them from the default engine.
    s = s.replace("p=p.filter(voicevoxQuestionAvailable);",
                  "p=p.filter(x=>voicevoxQuestionAvailable(x)||String(x?.source||'').includes('cross-reference'));", 1)
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
    write_if_changed(path, s)


def patch_mocktest():
    html_path = 'mocktest.html'
    hp = ROOT / html_path
    h = hp.read_text(encoding='utf-8')
    if 'grammar-reference-expansion.js' not in h:
        anchor = '<script src="./mocktest.js?v=20260822-quality5"></script>'
        require(h, anchor, html_path)
        h = h.replace(anchor, '<script src="./grammar-reference-expansion.js?v=20260826v1"></script>\n' + anchor, 1)
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
        'version': '2026-08-26-v1',
        'policy': 'data/CONTENT_REFERENCE_POLICY.md',
        'referenceMap': 'data/content_reference_map.json',
        'expansions': {
            'grammar': 'grammar-reference-expansion.js',
            'listening': 'listening-reference-expansion.js',
            'conversation': 'conversation-reference-expansion.js'
        },
        'integratedPages': ['grammar.html', 'listening.html', 'conversation.html', 'mocktest.html', 'mocktest.js'],
        'sharedPagesReviewed': {
            'vocabulary': ['index.html', 'wordlist.html', 'wordaudio.html', 'vocab-plus-game.html', 'vocabulary-plus.html'],
            'pronunciation': ['pronunciation.html'],
            'utility': ['translator.html']
        },
        'notes': [
            'Vocabulary pages continue using the shared world-evidence calibration layer instead of a new duplicate level system.',
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
