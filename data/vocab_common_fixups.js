// Common vocabulary items that must remain available even if an upstream deck omits or misclassifies them.
// Keep this list small, direct-reviewed, and shared by quiz / word list / word audio.
(()=>{'use strict';
const A=window.ADVANCED_WORDS=window.ADVANCED_WORDS||[];
const FIXUPS=[
  {id:'common-fix-niwa',level:'N5',reading:'にわ',kanji:'庭',displayWord:'庭',meaning:'庭院、院子',pos:'noun',estimated:false,source:'常用 JLPT 補充（教師來源確認）'},
  {id:'common-fix-musubitsukeru',level:'N1',reading:'むすびつける',kanji:'結び付ける',displayWord:'結び付ける',meaning:'連結；聯繫；使產生關聯；綁在一起',pos:'verb',estimated:true,source:'一般辭典常用詞補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-dantotsu',level:'N2',reading:'だんトツ',kanji:'断トツ',displayWord:'断トツ',meaning:'遙遙領先；壓倒性第一；出類拔萃',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-first',level:'N3',reading:'ファースト',kanji:'',displayWord:'ファースト',meaning:'第一；首位；一壘、一壘手；快速的（多見於複合語）',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-sweet',level:'N3',reading:'スイート',kanji:'',displayWord:'スイート',meaning:'甜的、甜蜜的；（酒店的）套房',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-must',level:'N2',reading:'マスト',kanji:'',displayWord:'マスト',meaning:'必需；不可或缺；必備的；桅杆',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-mode',level:'N3',reading:'モード',kanji:'',displayWord:'モード',meaning:'模式；設定；方式；狀態；時尚、流行',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-load-road',level:'N3',reading:'ロード',kanji:'',displayWord:'ロード',meaning:'道路；負荷；載入、讀入（程式或資料）',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-amenity',level:'N2',reading:'アメニティ',kanji:'',displayWord:'アメニティ',meaning:'舒適性；便利設施；（酒店等的）客用品、備品',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'},
  {id:'common-fix-aluminum-foil',level:'N3',reading:'アルミホイル',kanji:'',displayWord:'アルミホイル',meaning:'鋁箔；鋁箔紙',pos:'noun',estimated:true,source:'一般辭典 common coverage 補充（JLPT 分級由 teacher audit 接管）'}
];
const key=x=>`${String(x?.reading||'').trim()}|${String(x?.kanji||x?.displayWord||'').trim()}`;
function apply(words){
  const out=(Array.isArray(words)?words:[]).map(x=>({...x}));
  const fixes=new Map(FIXUPS.map(x=>[key(x),x]));
  const seen=new Set();
  for(let i=0;i<out.length;i++){
    const k=key(out[i]),fix=fixes.get(k);
    if(fix)out[i]={...out[i],...fix};
    seen.add(k);
  }
  for(const fix of FIXUPS){const k=key(fix);if(!seen.has(k)){out.push({...fix});seen.add(k);}}
  return out;
}
const seen=new Set(A.map(key));
for(const item of FIXUPS){if(!seen.has(key(item))){A.push(item);seen.add(key(item));}}
window.VOCAB_COMMON_FIXUPS=FIXUPS.map(x=>({...x}));
window.applyVocabCommonFixups=apply;
})();