// Conservative manual cross-check layer for core rows that remained ambiguous after
// exact JMdict/Tomoshi matching. External dictionaries are used only to validate the
// lexical sense/level; their proprietary wording, examples, audio, and other content
// are not copied into this project. Meanings below are short independent paraphrases.
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
  ["どの","どの","N5","哪個；哪一個"]
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
  version:"20260826-v2",
  configured:rows.length,
  applied,
  policy:"Secondary manual sense/level validation only; no bulk scraping or copied dictionary text.",
  references:["Mazii","MOJi辞書","時雨日中辭典"]
};
})();
