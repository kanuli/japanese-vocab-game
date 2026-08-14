#!/usr/bin/env python3
import html
import json
import re
from pathlib import Path
from fugashi import Tagger

KANJI = re.compile(r'[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF々〆ヶ]')

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

def ruby_sentence(text: str, tagger: Tagger) -> str:
    parts=[]
    for token in tagger(text):
        surface=str(token.surface)
        safe=html.escape(surface, quote=True)
        if not KANJI.search(surface):
            parts.append(safe)
            continue
        reading=get_reading(token)
        if not reading:
            parts.append(safe)
            continue
        parts.append(f'<ruby>{safe}<rt>{html.escape(reading, quote=True)}</rt></ruby>')
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
        'version':1,
        'sceneCount':data['sceneCount'],
        'totalLines':data['totalLines'],
        'uniqueLines':data['uniqueLines'],
        'mappedLines':len(mapping),
        'rubyTokens':ruby_count,
        'generator':'fugashi+UniDic',
    }
    payload=(
        'window.CONVERSATION_FURIGANA_META='+json.dumps(meta,ensure_ascii=False,separators=(',',':'))+';\n'
        'window.CONVERSATION_FURIGANA=Object.freeze('+json.dumps(mapping,ensure_ascii=False,separators=(',',':'))+');\n'
    )
    Path('conversation-furigana.js').write_text(payload,encoding='utf-8')
    print(f"Generated furigana for {len(mapping)} unique lines with {ruby_count} ruby tokens.")

if __name__=='__main__':
    main()
