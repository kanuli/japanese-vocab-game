#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request
TARGET_PER_LEVEL=2000
LEVELS=['N5','N4','N3','N2','N1']
FILES={x:f'grammar_ja_{x}_full_alphabetical_0001.json' for x in LEVELS}
BASE='https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/'
TYPE_LABELS={'quick_response':'即時應答','point':'重點理解','task':'任務理解','summary':'概要理解','inference':'推論／意圖理解'}
NAMES=['田中さん','佐藤さん','鈴木さん','高橋さん','山田さん','伊藤さん','中村さん','小林さん','加藤さん','吉田さん','山本さん','松本さん','井上さん','木村さん','林さん','清水さん']
TIMES=['八時','八時半','九時','九時半','十時','十時半','十一時','十一時半','一時','一時半','二時','三時']
ALT_TIMES=['七時半','八時','八時半','九時','九時半','十時','十時半','十一時','十二時','一時','二時','四時']
DAYS=['今日','明日','あさって','月曜日','火曜日','水曜日','木曜日','金曜日','土曜日','日曜日','来週の月曜日','来週の金曜日']
PLACES=['駅','図書館','市役所','銀行','病院','会社','学校','郵便局','スーパー','会議室','受付','レストラン']
ALT_PLACES=['空港','公園','教室','事務室','売店','ホテル','地下鉄の駅','一階','二階','三階','倉庫','入口']
OBJECTS=['資料','申込書','切符','薬','本','傘','かばん','鍵','弁当','領収書','予約票','荷物']
ACTIONS=['提出します','受け取ります','確認します','予約します','コピーします','返します','届けます','買います','電話します','説明します','整理します','送ります']
REASONS=['電車が遅れている','担当者が不在だ','雨が強くなった','予約がいっぱいだ','会議が長引いている','必要な資料がまだ届いていない','体調がよくない','工事で入口が使えない','予定が変更された','機械の点検が必要だ','道路が混んでいる','参加者が増えた']
EVENTS=['会議','説明会','授業','面接','予約','発表','研修','健康診断','見学','打ち合わせ','試験','受付']
CHORES=['資料を受付に出す','担当者に電話する','予約を変更する','コピーを三部取る','荷物を二階へ運ぶ','申込書に名前を書く','鍵を受付へ返す','会議室を予約する','メールを確認する','切符を買う','薬を受け取る','本を図書館へ返す']
def get_json(url):
    with urllib.request.urlopen(url,timeout=120) as r:return json.loads(r.read().decode('utf-8'))
def base_counts():
    out={}
    for level in LEVELS:
        n=0
        for p in get_json(BASE+FILES[level]):
            for e in p.get('examples') or []:
                jp=str(e.get('jp','')).strip()
                if 5<=len(jp)<=95:n+=1
        out[level]=n
    return out
def pick(seq,i,mul=1,add=0):return seq[(i*mul+add)%len(seq)]
def rotate(correct,distractors,i):
    vals=[correct]+list(distractors);assert len(vals)==4 and len(set(vals))==4
    k=i%4;return vals[k:]+vals[:k]
