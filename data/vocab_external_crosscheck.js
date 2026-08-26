// Conservative manual cross-check layer for exact core rows. External dictionaries are
// used only to validate lexical sense/level; proprietary wording, examples and audio are
// not copied. Meanings below are short independent Traditional-Chinese paraphrases.
(()=>{"use strict";
const map=window.VOCAB_CORE_VERIFIED;
const rows=[
  ["あなた","あなた","N5","你；您"],
  ["いくら","いくら","N4","多少（錢）；無論怎樣"],
  ["ある","ある","N5","有；在"],
  ["あの","あの","N5","那；那個"],
  ["その","その","N5","那；那個"],
  ["おじ","おじ","N5","伯父；叔父；叔叔"],
  ["おば","おば","N5","伯母；叔母；阿姨"],
  ["する","する","N5","做；進行；執行"],
  ["あれ","あれ","N5","那個、那；咦、欸（依語境）"],
  ["いつ","いつ","N5","何時；什麼時候"],
  ["いい","いい","N5","好；良好；可以"],
  ["うん","うん","N5","嗯；是的；好"],
  ["ここ","ここ","N5","這裡；此處"],
  ["そこ","そこ","N5","那裡；那邊"],
  ["どう","どう","N5","如何；怎麼；怎樣"],
  ["どの","どの","N5","哪個；哪一個"],
  ["そう","そう","N5","對、是；那樣、如此；那麼；啊（突然想起時）"],
  ["だけ","だけ","N5","只；僅；只是"],
  ["ない","ない","N5","沒有；不存在；缺少"],
  ["ごくごく","ごくごく","N2","咕嘟咕嘟地大口喝"],
  ["ぱらぱら","ぱらぱら","N1","零零落落地掉落；快速翻頁；稀稀落落"],
  ["ようやく","ようやく","N3","終於；總算；好不容易；逐漸"],
  ["おえる","終える","N4","結束；做完；完成"],
  ["めんきょ","免許","N3","執照；許可證；許可"],
  ["しゅ","手","N5","～手；從事某項工作或擔任某種角色的人"],
  ["あと","あと","N5","還有；另外；其餘"],
  ["で","で","N2","那麼；然後呢（催促對方繼續說）"],
  ["もくもく","もくもく","N1","（煙、雲等）滾滾升起、冒出"],
  ["より","より(副)","N2","更；更加；進一步"],
  ["いわば","いわば","N2","可以說；可謂；所謂"],
  ["くわえる","くわえる","N3","叼；銜；咬在嘴裡"],
  ["にじ","虹","N2","彩虹"],
  ["きる","きる","N2","～完；徹底做到最後（接在動詞連用形後）"],
  ["かける","駆ける","N3","奔跑；飛奔；疾馳"],
  ["ごさ","誤差","N1","誤差；偏差；測量或計算上的差值"],
  ["み","味","N1","種、份（計算食品、飲料或藥品種類的量詞）"],
  ["どんぞこ","どん底","N1","最底層；最低點；最差狀態"],
  ["はいはい","はいはい","N1","（嬰兒）爬行；爬爬"],
  ["かられる","駆られる","N2","被～驅使；受～催迫"],
  ["たたえる","たたえる","N1","充滿；蓄滿；洋溢；流露"],
  ["ウエア","ウエア","N1","衣著；衣服；服裝"],
  ["ゆがみ","ゆがみ","N2","歪斜；扭曲；變形；性格或狀態上的扭曲"],
  ["ぜんだま","善玉","N1","好人；正派角色；有益的一方"],
  ["こがねいろ","こがね色","N1","金黃色；黃金色"],
  ["とろみ","とろみ","N1","（醬汁、湯等的）黏稠度；濃稠狀態"],
  ["さきのばし","先延ばし","N1","延期；拖延；擱置"],
  ["すいか","西瓜","N5","西瓜"],
  ["これ","これ","N5","這個；這"],
  ["それ","それ","N5","那個；那"],
  ["おもしろい","面白い","N5","有趣的；好玩的"],
  ["あかるい","明るい","N5","明亮的；開朗的"],
  ["おわる","終わる","N5","結束；完結"],
  ["べんきょう","勉強","N5","學習；用功"],
  ["さんぽ","散歩","N5","散步"],
  ["だんだん","だんだん","N5","逐漸；漸漸"],
  ["もし","もし","N4","如果；假如"]
];
let applied=0;
if(map instanceof Map){
  for(const [reading,display,level,meaning] of rows){
    const key=`${reading}|${display}`;
    const current=map.get(key);
    if(!current)continue;
    map.set(key,{...current,level,meaning,meaningSource:"manual-secondary-crosscheck",levelSource:"manual-secondary-crosscheck",externalCrosscheck:true});
    applied++;
  }
}
window.VOCAB_EXTERNAL_CROSSCHECK_META={
  version:"20260826-v5-jlpt-conflict-sanity",
  configured:rows.length,
  applied,
  policy:"Secondary exact sense/level validation only; no bulk scraping or copied dictionary text. High-risk world-source JLPT conflicts are sanity-checked against Mazii/MOJi/時雨 where available; 時雨 explicitly confirms the added common-word sentinels.",
  references:["Mazii","MOJi辞書","時雨日中辭典","JMdict/Tomoshi","OpenJLPT","Waller/Tanos"]
};
})();