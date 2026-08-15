from pathlib import Path

p = Path('pronunciation.html')
s = p.read_text(encoding='utf-8')
changed = False

# Load the same local Kuromoji + dictionary furigana approach used by listening.
if './vendor/kuromoji.js' not in s:
    marker = '<script type="module" src="./vendor/supertonic-browser.js"></script>'
    insert = '<script src="./vendor/kuromoji.js"></script>\n<script src="./pronunciation-furigana.js?v=20260816v1"></script>\n' + marker
    if marker not in s:
        raise SystemExit('Could not find Supertonic script marker in pronunciation.html')
    s = s.replace(marker, insert, 1)
    changed = True
elif './pronunciation-furigana.js' not in s:
    marker = '<script type="module" src="./vendor/supertonic-browser.js"></script>'
    s = s.replace(marker, '<script src="./pronunciation-furigana.js?v=20260816v1"></script>\n' + marker, 1)
    changed = True

old = "$('#sentence').textContent=game.current.jp;$('#meta').textContent=`${game.current.level} · ${game.current.source}`;"
new = "const sentenceEl=$('#sentence');sentenceEl.textContent=game.current.jp;if(window.PronunciationFurigana)window.PronunciationFurigana.render(sentenceEl,game.current.jp);$('#meta').textContent=`${game.current.level} · ${game.current.source}`;"
if old in s:
    s = s.replace(old, new, 1)
    changed = True
elif 'PronunciationFurigana.render(sentenceEl,game.current.jp)' not in s:
    raise SystemExit('Could not find pronunciation sentence render marker')

if changed:
    p.write_text(s, encoding='utf-8')
    print('updated pronunciation.html with kanji furigana support')
else:
    print('pronunciation.html already has furigana support')
