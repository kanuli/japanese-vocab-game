(()=>{'use strict';
const root=window.SITUATION_SCENES=window.SITUATION_SCENES||[];
const counts={N5:0,N4:0,N3:0,N2:0,N1:0};
function replaceLine(line,jp){if(jp&&jp!==line.jp){line.jp=jp;return true}return false}
for(const scene of root.filter(s=>s.coverageGapExpansion&&Array.isArray(s.items))){
 for(const it of scene.items){
  const n=counts[it.level]++;const a=it.lines?.[0],b=it.lines?.[1];if(!a||!b)continue;let changed=false,m;
  if(it.level==='N5'){
   if((m=a.jp.match(/^すみません。(.+)について、もう一度教えてください。$/))){
    const v=n%3;const jp=v===0?`すみません。${m[1]}について、もう一度お願いします。`:v===1?`${m[1]}がよく分かりません。もう一度教えてください。`:`すみません。${m[1]}をもう一度説明してください。`;changed=replaceLine(a,jp)||changed;
   }else if((m=a.jp.match(/^(.+)てもいいですか。$/))&&n%3===1){changed=replaceLine(a,`${m[1]}ても大丈夫ですか。`)||changed}
   if(changed&&/^はい。/.test(b.jp)){b.jp=b.jp.replace(/^はい。/,'はい、')}
  }
  if(it.level==='N4'){
   m=a.jp.match(/^すみません、(.+)ので、(.+)について確認したいです。どうしたらいいですか。$/);
   if(m){const v=n%4;const jp=v===0?a.jp:v===1?`${m[1]}ので、${m[2]}について教えてもらえますか。`:v===2?`${m[1]}ため、${m[2]}を確認したいのですが、まず何をすればいいですか。`:`${m[2]}について質問があります。${m[1]}ので、どうすればいいですか。`;changed=replaceLine(a,jp)||changed}
   m=b.jp.match(/^まず(.+)。必要なら(.+)。$/);if(m){const v=n%4;const jp=v===0?b.jp:v===1?`最初に${m[1]}。そのあと、必要なら${m[2]}。`:v===2?`${m[1]}。それから、必要な場合は${m[2]}。`:`先に${m[1]}。必要に応じて${m[2]}。`;changed=replaceLine(b,jp)||changed}
  }
  if(it.level==='N3'){
   m=a.jp.match(/^(.+)のですが、(.+)を進めるには何を確認すればいいでしょうか。$/);
   if(m){const v=n%4;const jp=v===0?a.jp:v===1?`${m[1]}のですが、${m[2]}の前に確認することはありますか。`:v===2?`${m[1]}ので、${m[2]}を進める前に何を確認したらいいでしょうか。`:`${m[2]}について相談があります。${m[1]}ので、先に確認する点を教えてください。`;changed=replaceLine(a,jp)||changed}
   m=b.jp.match(/^最初に(.+)。そのあと、(.+)かどうか確認してください。$/);if(m){const v=n%4;const jp=v===0?b.jp:v===1?`まず${m[1]}。次に、${m[2]}か確認してください。`:v===2?`${m[1]}のが先です。その後で、${m[2]}かどうか見てください。`:`先に${m[1]}。確認できたら、${m[2]}かどうかも確認してください。`;changed=replaceLine(b,jp)||changed}
  }
  if(it.level==='N2'){
   m=a.jp.match(/^(.+)という事情があります。通常の方法が難しい場合、(.+)ことは可能でしょうか。$/);
   if(m){const v=n%4;const jp=v===0?a.jp:v===1?`${m[1]}という事情があり、通常どおりでは難しそうです。${m[2]}ことは可能でしょうか。`:v===2?`${m[1]}ため、別の方法を検討しています。${m[2]}という対応はできますか。`:`${m[1]}という事情を踏まえ、${m[2]}方法が取れるか確認したいです。`;changed=replaceLine(a,jp)||changed}
   m=b.jp.match(/^条件を確認したうえで、(.+)方法をご案内できます。難しい場合は別の案も検討します。$/);if(m){const v=n%4;const jp=v===0?b.jp:v===1?`条件を確認してから、${m[1]}方法をご案内します。合わなければ別案も考えます。`:v===2?`${m[1]}方法が使えるか条件を確認します。難しければ別の方法をご提案します。`:`まず条件を整理し、${m[1]}方法が適切か判断します。必要なら代替案も提示します。`;changed=replaceLine(b,jp)||changed}
  }
  if(it.level==='N1'){
   m=a.jp.match(/^(.+)という事情を踏まえると、通常どおりの対応では支障が出かねません。(.+)ことも含め、実情に即した対応をご検討いただけないでしょうか。$/);
   if(m){const v=n%4;const jp=v===0?a.jp:v===1?`${m[1]}という事情がある以上、通常対応だけでは支障が生じるおそれがあります。${m[2]}可能性も含め、個別にご検討いただけますか。`:v===2?`${m[1]}を踏まえると、一律の対応では十分とは言えません。${m[2]}ことも選択肢として、柔軟な対応をご検討願えないでしょうか。`:`${m[1]}という制約があるため、通常手順にこだわると問題が残りかねません。${m[2]}ことも含め、実情に合う方法をご検討いただければと思います。`;changed=replaceLine(a,jp)||changed}
   m=b.jp.match(/^一律には判断できませんが、事情と条件を確認したうえで、(.+)ことが可能か個別に検討いたします。$/);if(m){const v=n%4;const jp=v===0?b.jp:v===1?`事情と条件を整理したうえで、${m[1]}ことが妥当か個別に判断いたします。`:v===2?`一律の基準だけでは決められないため、条件を確認し、${m[1]}ことが可能か検討します。`:`まず制約と必要条件を確認し、その結果を踏まえて${m[1]}ことができるか判断いたします。`;changed=replaceLine(b,jp)||changed}
  }
  if(changed){it.qualityDepthBatch3=true;scene.qualityDepthBatch3=true}
 }
}
})();