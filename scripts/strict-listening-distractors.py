from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

start=s.index('const GROUPS=[')
end=s.index('];\nfunction mutations',start)+2
new_groups=r'''const GROUPS=[
["今日","昨日","明日"],["今週","先週","来週"],["今月","先月","来月"],["今年","去年","来年"],["さっき","今","あとで","昨日"],["朝","昼","夜"],["午前","午後"],["右","左"],["上","下"],["前","後"],
["ここ","そこ","あそこ"],["これ","それ","あれ"],["この","その","あの"],["まだ","もう"],["いつも","よく","時々","たまに"],["必ず","たぶん"],["好き","嫌い"],["高い","安い"],["大きい","小さい"],["多い","少ない"],["早い","遅い"],
["行きます","来ます","帰ります"],["行く","来る","帰る"],["買います","売ります"],["買う","売る"],["始まります","終わります"],["始まる","終わる"],["増えます","減ります"],["増える","減る"],
["ます","ません","ました","ませんでした"],["です","ではありません","でした","ではありませんでした"]
]'''
s=s[:start]+new_groups+s[end:]

mstart=s.index('function makeChoices(q){')
mend=s.index('function render(){',mstart)
strict=r'''function makeChoices(q){const d=shuffle(mutations(q.jp));if(d.length<3)return null;return{choices:shuffle([q.jp,...d.slice(0,3)]),quality:"同一句只改一個關鍵細節"}}
'''
s=s[:mstart]+strict+s[mend:]

p.write_text(s,encoding='utf-8')
print('strict controlled listening distractors enabled')
