#!/usr/bin/env python3
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'listening-gap-expansion.js'
s=p.read_text(encoding='utf-8')
anchor="const actionsZh=['確認資料','更改預約','領取藥物','寄送包裹','向老師商量','購物','聯絡負責人','提交申請表'];"
insert=anchor+"\nconst actionsTe=['資料を確認して','予約を変更して','薬を受け取って','荷物を送って','先生に相談して','買い物をして','担当者へ連絡して','申請書を出して'];\nconst actionsDict=['資料を確認する','予約を変更する','薬を受け取る','荷物を送る','先生に相談する','買い物をする','担当者へ連絡する','申請書を出す'];\nconst actionsAbility=['資料を確認できるようになりました','予約を変更できるようになりました','薬を受け取れるようになりました','荷物を送れるようになりました','先生に相談できるようになりました','買い物ができるようになりました','担当者へ連絡できるようになりました','申請書を出せるようになりました'];"
if 'const actionsTe=' not in s:
    if anchor not in s: raise SystemExit('actionsZh anchor missing')
    s=s.replace(anchor,insert,1)
s=s.replace("${act.replace('ます','て')}","${pick(actionsTe,i)}")
s=s.replace("${act.replace('します','できるようになりました')}","${pick(actionsAbility,i)}")
s=s.replace("${act.replace('します','する')}","${pick(actionsDict,i)}")
p.write_text(s,encoding='utf-8')
print('listening gap naturalness patch applied')
