(()=>{'use strict';
const scenes=window.SITUATION_SCENES||[];
const pick=(a,s,i)=>a[(Math.abs([...String(s||'')].reduce((n,c)=>n+c.codePointAt(0),0))+i)%a.length];
let rewritten=0,duplicateFixes=0,awkwardFixes=0;

const worldA={
 N5:(n,k)=>pick([
  `${n}をしたいです。どこへ行けばいいですか。`,
  `すみません。${n}をする場所はどこですか。`,
  `${n}はどこでできますか。`,
  `${n}をお願いしたいのですが、どこへ行けばいいですか。`,
  `すみません。${n}について、どこへ行けばいいですか。`
 ],n,k),
 N4:(n,k)=>pick([
  `${n}をする前に、必要なものを教えてください。`,
  `${n}の前に、何を用意すればいいですか。`,
  `${n}に必要なものを教えてください。`,
  `${n}をしたいのですが、何を準備すればいいですか。`,
  `${n}のために準備するものは何ですか。`
 ],n,k),
 N3:(n,issue,k)=>pick([
  `${n}について質問があります。${issue}場合でも問題ありませんか。`,
  `${issue}のですが、${n}はそのままで大丈夫ですか。`,
  `${n}を確認したいです。${issue}場合はどうすればいいですか。`,
  `${issue}という状況です。${n}について注意することはありますか。`,
  `${n}について教えてください。${issue}場合でも対応できますか。`
 ],n+issue,k),
 N2:(n,issue,k)=>pick([
  `${issue}という状況です。${n}について、どう対応すればいいですか。`,
  `${n}について相談です。${issue}のですが、次に何をすればいいですか。`,
  `${issue}ため、${n}の対応方法を確認したいです。`,
  `${n}について、${issue}という問題があります。どのように対応すればいいでしょうか。`,
  `${issue}場合、${n}について利用できる方法を教えてください。`
 ],n+issue,k),
 N1:(n,issue,k)=>pick([
  `${n}についてご相談です。${issue}という事情があるのですが、通常とは異なる方法で対応していただけますか。`,
  `${issue}という事情があります。${n}について、通常以外の方法で対応できるか確認したいです。`,
  `${n}について確認させてください。${issue}という場合、別の方法で対応していただくことは可能ですか。`,
  `${n}を利用したいのですが、${issue}という事情があります。通常とは別の対応をお願いできますでしょうか。`,
  `${issue}ため、通常の進め方が難しい状況です。${n}について代替の対応を相談できますか。`
 ],n+issue,k)
};
const worldB=(solve,key,k)=>pick([
 `${solve}。条件を確認して、利用できる方法をご案内します。`,
 `${solve}。状況を伺ったうえで、可能な手続きを確認します。`,
 `${solve}。詳細を確認し、対応できる方法をご説明します。`,
 `${solve}。事情に応じて必要な手順を一緒に確認しましょう。`,
 `${solve}。個別の条件を確認してから、適切な方法をご案内します。`
],key,k);

for(const s of scenes){
 (s.items||[]).forEach((x,i)=>{
  const a=x.lines?.[0],b=x.lines?.[1];if(!a||!b)return;
  let m,changed=false;
  if((m=String(a.jp).match(/^すみません。(.+?)はどこでできますか。$/))){a.jp=worldA.N5(m[1],i);rewritten++;changed=true;}
  else if((m=String(a.jp).match(/^(.+?)には何が必要ですか。$/))){a.jp=worldA.N4(m[1],i);rewritten++;changed=true;}
  else if((m=String(a.jp).match(/^(.+?)について確認したいのですが、「(.+?)」という状況でも大丈夫ですか。$/))){a.jp=worldA.N3(m[1],m[2],i);rewritten++;changed=true;}
  else if((m=String(a.jp).match(/^「(.+?)」という状況なのですが、(.+?)を進めるにはどうすればいいですか。$/))){a.jp=worldA.N2(m[2],m[1],i);rewritten++;changed=true;}
  else if((m=String(a.jp).match(/^(.+?)について相談があります。(.+?)という事情がある場合、通常の方法以外で対応していただくことは可能でしょうか。$/))){
    a.jp=worldA.N1(m[1],m[2],i);
    const bm=String(b.jp).match(/^(.+?)。詳しい条件は状況を確認したうえでご案内します。$/);if(bm)b.jp=worldB(bm[1],m[1]+m[2],i);
    rewritten++;changed=true;
  }

  if(s.referenceExpansion){
    if((m=String(a.jp).match(/^(.+?)をお願いします。$/))){const n=m[1];a.jp=pick([`${n}をお願いします。`,`${n}をお願いできますか。`,`${n}を利用したいです。`,`${n}についてお願いしたいです。`,`${n}を希望しています。`],s.id,i);b.jp=pick(['はい、承知しました。','わかりました。確認します。','はい、対応します。','かしこまりました。','はい、ご案内します。'],s.id,i);rewritten++;changed=true;}
    else if((m=String(a.jp).match(/^(.+?)をしたいです。何を準備したらいいですか。$/))){const n=m[1];a.jp=pick([`${n}をしたいです。何を用意すればいいですか。`,`${n}に必要なものを教えてください。`,`${n}の準備物を教えてください。`,`${n}の前に何を準備すればいいですか。`,`${n}をするために必要なものは何ですか。`],s.id,i);rewritten++;changed=true;}
    else if((m=String(a.jp).match(/^(.+?)ので、(.+?)について確認したいのですが、どうすればいいですか。$/))){const problem=m[1],n=m[2];a.jp=pick([`${problem}ので、${n}について確認したいです。どうすればいいですか。`,`${n}について質問があります。${problem}場合はどうすればいいですか。`,`${problem}ので、${n}の対応方法を教えてください。`,`${n}を確認したいです。${problem}ときは何をすればいいですか。`,`${problem}という状況です。${n}について注意する点はありますか。`],s.id,i);rewritten++;changed=true;}
    else if((m=String(a.jp).match(/^(.+?)という状況です。(.+?)を進める上で、別の方法はありますか。$/))){const problem=m[1],n=m[2];a.jp=pick([`${problem}という状況です。${n}について別の方法はありますか。`,`${n}について相談です。${problem}場合の対応方法を教えてください。`,`${problem}ので、${n}について利用できる別の方法を確認したいです。`,`${n}について、${problem}という問題があります。ほかの対応はできますか。`,`${problem}場合、${n}はどのように対応すればいいでしょうか。`],s.id,i);const bm=String(b.jp).match(/^(.+?)。条件によって必要な手続きが変わる場合があります。$/);if(bm)b.jp=pick([`${bm[1]}。条件を確認すると、必要な手続きがわかります。`,`${bm[1]}。状況によって手順が異なるので、確認して進めてください。`,`${bm[1]}。必要な手続きは条件ごとに確認できます。`,`${bm[1]}。詳しい条件を確認してから手続きをご案内します。`,`${bm[1]}。場合によって手順が変わるため、先に条件を確認してください。`],s.id,i);rewritten++;changed=true;}
    else if((m=String(a.jp).match(/^(.+?)という事情があります。通常の方法では対応が難しいとあれば、(.+?)について例外的な扱いをご検討いただくことは可能でしょうか。$/))){const problem=m[1],n=m[2];a.jp=pick([`${problem}という事情があります。${n}について通常とは別の対応をご相談できますか。`,`${n}について相談があります。${problem}場合、例外的な対応が可能か確認したいです。`,`${problem}ため通常の方法が難しいのですが、${n}について代替の対応をご検討いただけますか。`,`${n}について確認させてください。${problem}という事情がある場合、別の方法で対応できますか。`,`${problem}という状況です。${n}について個別の対応をお願いすることは可能でしょうか。`],s.id,i);const bm=String(b.jp).match(/^(.+?)。実情に即して確認したうえで、可能な対応をご案内いたします。$/);if(bm)b.jp=pick([`${bm[1]}。事情を確認したうえで、可能な方法をご案内します。`,`${bm[1]}。状況を確認し、利用できる対応をご説明します。`,`${bm[1]}。個別の条件を確認してから、可能な手続きをご案内します。`,`${bm[1]}。実際の状況を伺い、対応できる方法を確認します。`,`${bm[1]}。条件に合わせて、可能な対応を検討します。`],s.id,i);rewritten++;changed=true;}
  }

  // Final naturalness cleanup for isolated generated rows that do not match
  // the larger templates above. These are narrow phrase-level corrections.
  const fixes=[
   ['確認を進めるには','確認するには'],['相談を進めるには','相談するには'],['予約を進めるには','予約するには'],['変更を進めるには','変更するには'],
   ['トラブルを進めるには','トラブルに対応するには'],['利用を進めるには','利用するには'],['説明を進めるには','説明するには'],
   ['書類を進めるには','書類の手続きを進めるには'],['購入を進めるには','購入するには'],['支援を進めるには','支援を受けるには'],['違いを進めるには','違いを確認するには']
  ];
  for(const [from,to] of fixes)if(String(a.jp).includes(from)){a.jp=String(a.jp).replace(from,to);awkwardFixes++;changed=true;}
  if(changed)x.qualityDepthBatch7=true;
 });
}

const dupFixes=[
 {a:'一緒にご飯を食べませんか。',b:'いいですね。',na:'今度、一緒にご飯を食べませんか。',nb:'いいですね。ぜひ。',za:'下次一起吃飯嗎？',zb:'好啊，當然。'},
 {a:'燃えるごみは何曜日ですか。',b:'火曜日と金曜日です。',na:'燃えるごみは、何曜日に出しますか。',nb:'火曜日と金曜日に出します。',za:'可燃垃圾星期幾丟？',zb:'星期二和星期五丟。'},
 {a:'財布をなくしました。',b:'どこでなくしましたか。',na:'財布をなくしてしまいました。',nb:'最後に使った場所はどこですか。',za:'我把錢包弄丟了。',zb:'最後一次使用是在甚麼地方？'}
];
for(const f of dupFixes){let seen=0;for(const s of scenes)for(const x of s.items||[]){const a=x.lines?.[0],b=x.lines?.[1];if(a?.jp===f.a&&b?.jp===f.b){seen++;if(seen===2){a.jp=f.na;b.jp=f.nb;a.zh=f.za;b.zh=f.zb;x.qualityDepthBatch7=true;duplicateFixes++;}}}}
window.CONVERSATION_QUALITY_BATCH7={rewritten,duplicateFixes,awkwardFixes};
})();
