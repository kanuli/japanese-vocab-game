from pathlib import Path
import runpy
import re

runpy.run_path('.github/scripts/fix_listening_mock_quality_v2.py', run_name='__main__')

# Root-fix one information-search template that could generate a duplicate
# distractor when t == 18. The QA gate already blocked it, but the generator
# itself should never create the bad candidate.
p=Path('mocktest.js')
s=p.read_text(encoding='utf-8')
old='w:["土曜日は18時まで利用できる。","毎週木曜日が休館日だ。","毎日8時から利用できる。"]'
new='w:[`土曜日は${t===18?16:18}時まで利用できる。`,"毎週木曜日が休館日だ。","毎日8時から利用できる。"]'
if old in s:
    s=s.replace(old,new,1)
elif 't===18?16:18' not in s:
    raise SystemExit('mock information-search duplicate root fix marker missing')

# Naturalness hardening: the first scene generator crossed every place with
# every action. That could create structurally valid but semantically odd
# combinations (for example, an action that does not fit the location). Keep
# a place-specific action bank so generated reading/listening scenes stay
# plausible before they even reach the structural QA gate.
if 'const SCENE_ACTIONS=' not in s:
    marker='function readingTypes(level){return level==="N1"?["短文理解","中文理解","長文理解","統合理解","主題理解"]:level==="N2"?["短文理解","中文理解","統合理解","主題理解"]:level==="N3"?["短文理解","中文理解","長文理解"]:["短文理解","中文理解"]}\n'
    scene_actions='''const SCENE_ACTIONS={
N5:{"駅":["電車を待ちます","友達を待ちます","切符を買います"],"学校":["勉強します","先生に質問します","友達に会います"],"店":["買い物をします","店員に聞きます","商品を見ます"],"図書館":["本を借ります","勉強します","本を返します"]},
N4:{"駅前":["友達に電話します","バスを待ちます","待ち合わせをします"],"会議室":["資料を確認します","会議の準備をします","担当者に電話します"],"図書館":["本を予約します","資料を探します","勉強します"],"病院":["受付で確認します","予約を変更します","診察を待ちます"]},
N3:{"会社":["担当者に連絡します","資料を確認します","予定を変更します"],"受付":["担当者に確認します","予約を取り直します","書類を出します"],"駅":["電車の時間を確認します","予定を変更します","友達に連絡します"],"レストラン":["予約を確認します","予約を取り直します","店員に確認します"]},
N2:{"事務所":["責任者に確認します","資料を修正します","参加者へ連絡します"],"会議室":["資料を確認します","日程を調整します","責任者へ報告します"],"受付":["参加者へ連絡します","申込内容を確認します","担当者に確認します"],"研修会場":["資料を配布します","参加者へ連絡します","日程を確認します"]},
N1:{"事務局":["関係者と調整します","資料の内容を再確認します","責任者へ報告します"],"研究室":["研究資料を再確認します","担当者と調整します","責任者へ報告します"],"会議会場":["関係者と調整します","会議資料を再確認します","予定を見直します"],"受付窓口":["申請内容を再確認します","関係者へ報告します","手続きを見直します"]}
};
'''
    if marker not in s:
        raise SystemExit('readingTypes marker missing for SCENE_ACTIONS')
    s=s.replace(marker,marker+scene_actions,1)

old='function sceneCombos(level){const d=ORIGINAL_SCENE_DATA[level];if(!d)return[];const out=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of d.actions)out.push({person,place,time,action});return shuffle(out)}'
new='function sceneCombos(level){const d=ORIGINAL_SCENE_DATA[level],acts=SCENE_ACTIONS[level]||{};if(!d)return[];const out=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of (acts[place]||[]))out.push({person,place,time,action});return shuffle(out)}'
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('sceneCombos naturalness patch marker missing')

# Avoid malformed masu-form concatenations such as "確認します予定です" or
# "電話します必要があります". Use two complete polite sentences instead.
old='passage=`${x.person}は${x.time}に${x.place}で${act}予定です。その前に${place2}で${act2}必要があります。`;question="先にする必要があることは何ですか。";correct=`${place2}で${act2}`'
new='passage=`${x.person}は、まず${place2}で${act2}。そのあと${x.time}に${x.place}で${act}。`;question="先にすることは何ですか。";correct=`${place2}で${act2}`'
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('reading naturalness patch marker missing')

# Make the "go to a place, then act there" templates explicit and natural.
s=s.replace('passage=`${x.person}は${x.time}に${x.place}へ行き、${act}。そのあと${place2}へ行きます。`','passage=`${x.person}は${x.time}に${x.place}へ行き、そこで${act}。そのあと${place2}へ行きます。`')
s=s.replace('passage=`${x.person}は最初${x.time}に${x.place}へ行く予定でした。しかし予定が変わり、${time2}に${place2}へ行って${act}。`','passage=`${x.person}は最初${x.time}に${x.place}へ行く予定でした。しかし予定が変わり、${time2}に${place2}へ行き、そこで${act}。`')

old='function buildOriginalScenes(level,n){const d=ORIGINAL_SCENE_DATA[level],out=[];if(!d)return out;const combos=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of d.actions)combos.push({person,place,time,action});'
new='function buildOriginalScenes(level,n){const d=ORIGINAL_SCENE_DATA[level],acts=SCENE_ACTIONS[level]||{},out=[];if(!d)return out;const combos=[];for(const person of d.people)for(const place of d.places)for(const time of d.times)for(const action of (acts[place]||[]))combos.push({person,place,time,action});'
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('buildOriginalScenes place-action patch marker missing')

old='audio=`${person}は${time}に${place}で${act}予定です。その前に${place2}で${act2}必要があります。`;correct=`先に${place2}で${act2}`'
new='audio=`${person}は、まず${place2}で${act2}。そのあと${time}に${place}で${act}。`;correct=`先に${place2}で${act2}`'
if old in s:
    s=s.replace(old,new,1)
elif new not in s:
    raise SystemExit('listening naturalness patch marker missing')

s=s.replace('audio=`${person}は${time}に${place}へ行って、${act}。`','audio=`${person}は${time}に${place}へ行き、そこで${act}。`')
s=s.replace('audio=`${person}は最初${time}に${place}へ行く予定でしたが、予定が変わり、${time2}に${place2}へ行って${act}。`','audio=`${person}は最初${time}に${place}へ行く予定でしたが、予定が変わり、${time2}に${place2}へ行き、そこで${act}。`')

p.write_text(s,encoding='utf-8')

# Force browsers/GitHub Pages to fetch the latest repaired mocktest.js instead
# of a previously cached pre-naturalness build.
p=Path('mocktest.html')
h=p.read_text(encoding='utf-8')
h2=re.sub(r'mocktest\.js\?v=[^"\s<]+','mocktest.js?v=20260822-quality4',h,count=1)
if h2==h and 'mocktest.js?v=20260822-quality4' not in h:
    raise SystemExit('mocktest.js cache-bust marker not found')
p.write_text(h2,encoding='utf-8')

print('quality v4 naturalness finalization complete')
