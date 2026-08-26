(()=>{'use strict';
const root=window.SITUATION_SCENES=window.SITUATION_SCENES||[];
const patches=[
 {"sceneId":"weather-warning","level":"N4","occurrence":0,"item":{"level":"N4","situation":"台風情報・予定変更と助言","lines":[{"role":"A","jp":"すみません。台風が近づいているので、明日の予定を別の時間に変更したいです。","zh":"不好意思，因為颱風正在接近，我想把明天的安排改到其他時間。"},{"role":"B","jp":"午後より午前中のほうが安全そうです。早い時間に変更したほうがいいと思います。","zh":"看來上午比下午安全。我建議改到較早的時間。"}]}},
 {"sceneId":"japanese-learning","level":"N3","occurrence":0,"item":{"level":"N3","situation":"日本語クラス・申込み手続き","lines":[{"role":"A","jp":"日本語クラスの申込み手続きをしたいのですが、何から始めればいいでしょうか。","zh":"我想辦理日語課程報名手續，應該先做甚麼？"},{"role":"B","jp":"まず受付で申請書を受け取り、必要事項を書いてから提出してください。","zh":"請先在接待處領取申請表，填好必要資料後再提交。"}]}},
 {"sceneId":"dietary-restrictions","level":"N2","occurrence":0,"item":{"level":"N2","situation":"食物アレルギー・例外対応","lines":[{"role":"A","jp":"食物アレルギーがあるのですが、今回に限り、通常の方法以外で料理を用意していただくことは可能でしょうか。","zh":"我有食物過敏。只有這次，可以用一般方式以外的方法準備餐點嗎？"},{"role":"B","jp":"事情がある場合は、厨房と確認したうえで個別に対応できるか検討します。","zh":"如有特殊情況，我們會先與廚房確認，再個別考慮能否處理。"}]}}
];
for(const p of patches){
 const scene=root.find(s=>s.id===p.sceneId);if(!scene||!Array.isArray(scene.items))continue;
 const indexes=[];scene.items.forEach((x,i)=>{if(x.level===p.level)indexes.push(i)});
 const idx=indexes[p.occurrence||0];if(Number.isInteger(idx))scene.items[idx]=p.item;
}
})();
