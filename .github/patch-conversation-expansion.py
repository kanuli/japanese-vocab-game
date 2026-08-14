from pathlib import Path

p=Path('conversation.html')
s=p.read_text(encoding='utf-8')
if 'conversation-expansion.js' not in s:
    needle='<script src="./conversation-data-5.js?v=20260814v1"></script>'
    repl=needle+'\n<script src="./conversation-expansion.js?v=20260815v1"></script>'
    if needle not in s:
        raise SystemExit('conversation data script anchor not found')
    s=s.replace(needle,repl,1)
s=s.replace('N1–N5｜車站、超市、餐廳、酒店、醫院、工作等真實場景｜聽力・跟讀・聽寫','N1–N5｜26 個真實場景｜每個場景 25 組會話（每級 5 組）｜聽力・跟讀・聽寫')
s=s.replace('日本語・場面別會話 v1.1｜繁體中文解釋｜Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。','日本語・場面別會話 v1.3｜26 場景 × 每場景 25 組 = 650 組會話｜N1–N5 每級每場景 5 組｜繁體中文解釋｜Supertonic AI、VOICEVOX、AivisSpeech、裝置日語語音。')
p.write_text(s,encoding='utf-8')
