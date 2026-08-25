// Common vocabulary items that must remain available even if an upstream deck omits them.
// Keep this list small, direct-reviewed, and shared by quiz / word list / word audio.
(()=>{'use strict';
const A=window.ADVANCED_WORDS=window.ADVANCED_WORDS||[];
const FIXUPS=[
  {id:'common-fix-niwa',level:'N4',reading:'にわ',kanji:'庭',displayWord:'庭',meaning:'庭院、院子',pos:'noun',estimated:false,source:'常用 JLPT 補充（人工確認）'}
];
const key=x=>`${String(x?.reading||'').trim()}|${String(x?.kanji||x?.displayWord||'').trim()}`;
const seen=new Set(A.map(key));
for(const item of FIXUPS){if(!seen.has(key(item))){A.push(item);seen.add(key(item));}}
})();
