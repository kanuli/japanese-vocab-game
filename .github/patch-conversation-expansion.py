from pathlib import Path

p=Path('conversation.html')
s=p.read_text(encoding='utf-8')
base='<script src="./conversation-data-5.js?v=20260814v1"></script>'
exp='<script src="./conversation-expansion.js?v=20260815v1"></script>'
world='<script src="./conversation-world-expansion.js?v=20260815v1"></script>'
if exp not in s:
    if base not in s: raise SystemExit('conversation data script anchor not found')
    s=s.replace(base,base+'\n'+exp,1)
if world not in s:
    if exp not in s: raise SystemExit('conversation expansion anchor not found')
    s=s.replace(exp,exp+'\n'+world,1)
# Never downgrade the current 61-scene copy if this legacy installer is run again.
s=s.replace('N1–N5｜26 個真實場景｜每個場景 25 組會話（每級 5 組）｜聽力・跟讀・聽寫','N1–N5｜61 個真實生活場景｜1,525 組會話｜每個場景每級 5 組｜聽力・跟讀・聽寫')
s=s.replace('N1–N5｜車站、超市、餐廳、酒店、醫院、工作等真實場景｜聽力・跟讀・聽寫','N1–N5｜61 個真實生活場景｜1,525 組會話｜每個場景每級 5 組｜聽力・跟讀・聽寫')
s=s.replace('日本語・場面別會話 v1.3｜26 場景 × 每場景 25 組 = 650 組會話｜N1–N5 每級每場景 5 組｜繁體中文解釋｜','日本語・場面別會話 v2.0｜61 場景 × 每場景 25 組 = 1,525 組會話｜N1–N5 每級每場景 5 組｜漢字ふりがな＋繁體中文解釋｜')
s=s.replace('日本語・場面別會話 v1.1｜繁體中文解釋｜','日本語・場面別會話 v2.0｜61 場景 × 每場景 25 組 = 1,525 組會話｜N1–N5 每級每場景 5 組｜漢字ふりがな＋繁體中文解釋｜')
p.write_text(s,encoding='utf-8')
