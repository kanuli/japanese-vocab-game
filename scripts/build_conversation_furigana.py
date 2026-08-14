#!/usr/bin/env python3
import html
import json
import re
from pathlib import Path
from fugashi import Tagger

KANJI_CLASS=r'\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF々〆ヶ'
KANA_CLASS=r'ぁ-ゖァ-ヺー'
KANJI=re.compile(f'[{KANJI_CLASS}]')
KANJI_GROUP=re.compile(f'^[{KANJI_CLASS}]+$')
KANA_GROUP=re.compile(f'^[{KANA_CLASS}]+$')
GROUPS=re.compile(f'([{KANJI_CLASS}]+|[{KANA_CLASS}]+|[^{KANJI_CLASS}{KANA_CLASS}]+)')

def kata_to_hira(text: str) -> str:
    out=[]
    for ch in text:
        code=ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code-0x60))
        else:
            out.append(ch)
    return ''.join(out)

def get_reading(token):
    f=token.feature
    for name in ('kana','pron','pronBase','kanaBase'):
        value=getattr(f,name,None)
        if value and value != '*':
            return kata_to_hira(str(value))
    return ''

def full_ruby(surface: str, reading: str) -> str:
    return f'<ruby>{html.escape(surface,quote=True)}<rt>{html.escape(reading,quote=True)}</rt></ruby>'

def kanji_only_ruby(surface: str, reading: str) -> str:
    """Put ruby only above kanji groups, leaving okurigana outside ruby."""
    groups=GROUPS.findall(surface)
    if not groups or ''.join(groups) != surface:
        return full_ruby(surface,reading)
    if not any(KANJI_GROUP.fullmatch(g) for g in groups):
        return html.escape(surface,quote=True)
    if all(KANJI_GROUP.fullmatch(g) for g in groups):
        return full_ruby(surface,reading)

    out=[]
    pos=0
    for i,g in enumerate(groups):
        safe=html.escape(g,quote=True)
        if KANA_GROUP.fullmatch(g):
            expected=kata_to_hira(g)
            if not reading.startswith(expected,pos):
                return full_ruby(surface,reading)
            out.append(safe)
            pos += len(expected)
            continue
        if KANJI_GROUP.fullmatch(g):
            next_kana=None
            for later in groups[i+1:]:
                if KANA_GROUP.fullmatch(later):
                    next_kana=kata_to_hira(later)
                    break
                if not KANJI_GROUP.fullmatch(later):
                    break
            if next_kana:
                idx=reading.find(next_kana,pos)
                if idx < pos:
                    return full_ruby(surface,reading)
                ruby_reading=reading[pos:idx]
                if not ruby_reading:
                    return full_ruby(surface,reading)
                out.append(f'<ruby>{safe}<rt>{html.escape(ruby_reading,quote=True)}</rt></ruby>')
                pos=idx
            else:
                ruby_reading=reading[pos:]
                if not ruby_reading:
                    return full_ruby(surface,reading)
                out.append(f'<ruby>{safe}<rt>{html.escape(ruby_reading,quote=True)}</rt></ruby>')
                pos=len(reading)
            continue
        return full_ruby(surface,reading)

    if pos != len(reading):
        return full_ruby(surface,reading)
    return ''.join(out)

def ruby_sentence(text: str, tagger: Tagger) -> str:
    parts=[]
    for token in tagger(text):
        surface=str(token.surface)
        safe=html.escape(surface,quote=True)
        if not KANJI.search(surface):
            parts.append(safe)
            continue
        reading=get_reading(token)
        if not reading:
            parts.append(safe)
            continue
        parts.append(kanji_only_ruby(surface,reading))
    return ''.join(parts)

def main():
    source=Path('conversation-lines.json')
    data=json.loads(source.read_text(encoding='utf-8'))
    tagger=Tagger()
    mapping={}
    ruby_count=0
    for text in data['lines']:
        rendered=ruby_sentence(text,tagger)
        mapping[text]=rendered
        ruby_count += rendered.count('<ruby>')
    meta={
        'version':3,
        'sceneCount':data['sceneCount'],
        'totalLines':data['totalLines'],
        'uniqueLines':data['uniqueLines'],
        'mappedLines':len(mapping),
        'rubyTokens':ruby_count,
        'generator':'fugashi+UniDic kanji-only ruby',
    }
    payload=(
        'window.CONVERSATION_FURIGANA_META='+json.dumps(meta,ensure_ascii=False,separators=(',',':'))+';\n'
        'window.CONVERSATION_FURIGANA=Object.freeze('+json.dumps(mapping,ensure_ascii=False,separators=(',',':'))+');\n'
    )
    Path('conversation-furigana.js').write_text(payload,encoding='utf-8')
    print(f"Generated furigana for {len(mapping)} unique lines with {ruby_count} ruby spans.")

if __name__=='__main__':
    main()
