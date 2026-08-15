#!/usr/bin/env python3
from pathlib import Path

world=Path('conversation-world-expansion.js')
s=world.read_text(encoding='utf-8')
s=s.replace("`${n}について確認したいのですが、${issue}場合でも大丈夫ですか。`", "`${n}について確認したいのですが、「${issue}」という状況でも大丈夫ですか。`")
s=s.replace("`${issue}のですが、${n}を進めるにはどうすればいいですか。`", "`「${issue}」という状況なのですが、${n}を進めるにはどうすればいいですか。`")
world.write_text(s,encoding='utf-8')

p=Path('conversation.html')
h=p.read_text(encoding='utf-8')
anchor='<script src="./conversation-expansion.js?v=20260815v1"></script>'
new=anchor+'\n<script src="./conversation-world-expansion.js?v=20260815v1"></script>'
if 'conversation-world-expansion.js' not in h:
    if anchor not in h: raise SystemExit('conversation expansion anchor not found')
    h=h.replace(anchor,new,1)
h=h.replace('N1–N5｜26 個真實場景｜每個場景 25 組會話（每級 5 組）｜聽力・跟讀・聽寫','N1–N5｜61 個真實生活場景｜1,525 組會話｜每個場景每級 5 組｜聽力・跟讀・聽寫')
h=h.replace('日本語・場面別會話 v1.4｜26 場景 × 每場景 25 組 = 650 組會話｜N1–N5 每級每場景 5 組','日本語・場面別會話 v2.0｜61 場景 × 每場景 25 組 = 1,525 組會話｜N1–N5 每級每場景 5 組')
p.write_text(h,encoding='utf-8')

p=Path('scripts/extract_conversation_lines.mjs')
e=p.read_text(encoding='utf-8')
needle="  'conversation-expansion.js',\n"
if "'conversation-world-expansion.js'" not in e:
    if needle not in e: raise SystemExit('extractor anchor not found')
    e=e.replace(needle,needle+"  'conversation-world-expansion.js',\n",1)
p.write_text(e,encoding='utf-8')
print('Patched conversation world expansion, page, and audio extractor')
