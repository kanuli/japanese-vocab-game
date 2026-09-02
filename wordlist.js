(function(){'use strict';
var W=window.WA;if(!W)return;var page=1,selectedKana='',view=[],audioBusy=false;
var VOICES={F1:['🌙 沉穩低柔女聲（F1）','F1：沉穩、略低音、平靜而穩定。適合較成熟、低柔的女聲。'],F2:['🌸 明亮活潑女聲（F2）','F2：明亮、愉快、活潑而年輕。適合可愛、角色感較強的女聲。'],F3:['🎙️ 專業播音女聲（F3）','F3：清晰、專業、播音員風格。適合正式或新聞式發音。'],F4:['✨ 清晰自信女聲（F4）','F4：清脆、自信、表達力強。適合有力而清楚的女聲。'],F5:['💕 溫柔療癒女聲（F5）','F5：親切、溫柔、輕聲而舒緩。適合柔和、陪伴感較強的女聲。'],M1:['⚡ 活力自信男聲（M1）','M1：活潑、正面、自信而清晰。適合一般及有活力的男聲。'],M2:['🌑 低沉穩重男聲（M2）','M2：低沉、厚實、冷靜而嚴肅。適合成熟、穩重的男聲。'],M3:['🧭 權威專業男聲（M3）','M3：精緻、權威、自信可信。適合專業演說或正式旁白。'],M4:['🙂 柔和親切男聲（M4）','M4：柔和、中性、年輕而親切。適合教育及輕鬆內容。'],M5:['📖 溫暖舒緩男聲（M5）','M5：溫暖、輕聲、平靜而舒緩。適合故事及放鬆內容。'],random:['🎲 每個單字隨機聲線','每次試聽隨機使用 F1–F5／M1–M5，避免習慣單一聲線。']};
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function hira(s){return String(s||'').replace(/[ァ-ヶ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-96);}).replace(/[ぁぃぅぇぉゃゅょっ]/g,function(c){return{'ぁ':'あ','ぃ':'い','ぅ':'う','ぇ':'え','ぉ':'お','ゃ':'や','ゅ':'ゆ','ょ':'よ','っ':'つ'}[c]||c;});}
function firstKana(w){var r=hira(w.reading||'').replace(/^[\s・ー]+/,'');return r.charAt(0)||'';}
function engine(){var e=document.getElementById('audioEngine');return e?e.value:'supertonic3';}
W.levels=function(){return ['N1','N2','N3','N4','N5'].filter(function(l){var x=document.getElementById(l.toLowerCase());return x&&x.checked;});};

/* Search normalization + lightweight Japanese deinflection.
   Search may use a changed/conjugated form, while results keep the stored dictionary form. */
function normSearch(s){
  s=String(s==null?'':s);
  try{s=s.normalize('NFKC');}catch(e){}
  return s.toLowerCase().replace(/[ァ-ヶ]/g,function(c){return String.fromCharCode(c.charCodeAt(0)-96);}).replace(/[\s　]+/g,'').replace(/[。．.!！?？、，,]+$/g,'');
}
var I2U={'い':'う','き':'く','ぎ':'ぐ','し':'す','ち':'つ','に':'ぬ','び':'ぶ','み':'む','り':'る'};
var A2U={'わ':'う','か':'く','が':'ぐ','さ':'す','た':'つ','な':'ぬ','ば':'ぶ','ま':'む','ら':'る'};
var E2U={'え':'う','け':'く','げ':'ぐ','せ':'す','て':'つ','ね':'ぬ','べ':'ぶ','め':'む','れ':'る'};
var O2U={'お':'う','こ':'く','ご':'ぐ','そ':'す','と':'つ','の':'ぬ','ぼ':'ぶ','も':'む','ろ':'る'};
function addCandidate(set,queue,s){s=normSearch(s);if(!s||set.has(s)||set.size>=240)return;set.add(s);queue.push(s);}
function fromMasuStem(stem,set,queue){if(!stem)return;addCandidate(set,queue,stem+'る');var last=stem.slice(-1),u=I2U[last];if(u)addCandidate(set,queue,stem.slice(0,-1)+u);if(last==='し')addCandidate(set,queue,stem.slice(0,-1)+'する');if(stem==='き')addCandidate(set,queue,'くる');}
function fromARowStem(stem,set,queue){if(!stem)return;addCandidate(set,queue,stem+'る');var last=stem.slice(-1),u=A2U[last];if(u)addCandidate(set,queue,stem.slice(0,-1)+u);if(last==='し')addCandidate(set,queue,stem.slice(0,-1)+'する');if(stem==='こ')addCandidate(set,queue,'くる');}
function fromERowStem(stem,set,queue){if(!stem)return;addCandidate(set,queue,stem+'る');var last=stem.slice(-1),u=E2U[last];if(u)addCandidate(set,queue,stem.slice(0,-1)+u);}
function fromORowStem(stem,set,queue){if(!stem)return;var last=stem.slice(-1),u=O2U[last];if(u)addCandidate(set,queue,stem.slice(0,-1)+u);}
function replaceEnding(s,end,rep,set,queue){if(s.length>end.length&&s.endsWith(end))addCandidate(set,queue,s.slice(0,-end.length)+rep);}
function deinflectSearch(raw){
  var root=normSearch(raw),set=new Set(),queue=[];addCandidate(set,queue,root);
  for(var qi=0;qi<queue.length&&qi<240;qi++){
    var s=queue[qi],stem,last,u;
    ['ていなかった','でいなかった','ていました','でいました','ていませんでした','でいませんでした','ていません','でいません','ていない','でいない','ています','でいます','ていた','でいた','ている','でいる','てある','である'].forEach(function(end){if(s.endsWith(end)){var lead=end.charAt(0);addCandidate(set,queue,s.slice(0,-end.length)+lead);}});
    ['てしまわなかった','でしまわなかった','てしまわない','でしまわない','てしまいました','でしまいました','てしまった','でしまった','てしまう','でしまう','てしまって','でしまって','ておかなかった','でおかなかった','ておかない','でおかない','ておいた','でおいた','ておいて','でおいて','ておく','でおく','てみなかった','でみなかった','てみない','でみない','てみた','でみた','てみて','でみて','てみる','でみる','てきた','できた','てくる','でくる','ていく','でいく','てください','でください','てくれた','でくれた','てくれる','でくれる','てもらった','でもらった','てもらう','でもらう','てあげた','であげた','てあげる','であげる'].forEach(function(end){if(s.endsWith(end)){var lead=end.charAt(0);addCandidate(set,queue,s.slice(0,-end.length)+lead);}});
    replaceEnding(s,'ちゃった','て',set,queue);replaceEnding(s,'ちゃう','て',set,queue);replaceEnding(s,'ちゃって','て',set,queue);replaceEnding(s,'じゃった','で',set,queue);replaceEnding(s,'じゃう','で',set,queue);replaceEnding(s,'じゃって','で',set,queue);
    replaceEnding(s,'といた','て',set,queue);replaceEnding(s,'といて','て',set,queue);replaceEnding(s,'とく','て',set,queue);replaceEnding(s,'どいた','で',set,queue);replaceEnding(s,'どいて','で',set,queue);replaceEnding(s,'どく','で',set,queue);
    ['なければならなかった','なければならない','なくてはいけなかった','なくてはいけない','ないといけなかった','ないといけない','なくちゃいけない','なくちゃならない'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))addCandidate(set,queue,s.slice(0,-end.length)+'ない');});
    ['ませんでした','ましょう','ました','ません','ます'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromMasuStem(s.slice(0,-end.length),set,queue);});
    ['たくなかった','たくない','たかった','たい'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromMasuStem(s.slice(0,-end.length),set,queue);});
    ['ながら','やすかった','やすくない','やすい','にくかった','にくくない','にくい','すぎました','すぎた','すぎない','すぎる'].forEach(function(end){if(s.length>end.length&&s.endsWith(end)){stem=s.slice(0,-end.length);fromMasuStem(stem,set,queue);if(end.indexOf('すぎ')===0)addCandidate(set,queue,stem+'い');}});
    ['くなかった','くない','かった','くて','ければ'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))addCandidate(set,queue,s.slice(0,-end.length)+'い');});
    ['ではありませんでした','じゃありませんでした','ではなかった','じゃなかった','ではありません','じゃありません','ではない','じゃない','でした','だった','です','だ'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))addCandidate(set,queue,s.slice(0,-end.length));});
    ['なければ','なくて','なかった','ない'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromARowStem(s.slice(0,-end.length),set,queue);});
    if(s.length>2&&s.endsWith('たら'))addCandidate(set,queue,s.slice(0,-1));
    if(s.length>2&&s.endsWith('だら'))addCandidate(set,queue,s.slice(0,-1));
    if(s.length>2&&s.endsWith('れば')){stem=s.slice(0,-2);addCandidate(set,queue,stem+'る');fromERowStem(stem,set,queue);}
    if(s.length>1&&s.endsWith('ば'))fromERowStem(s.slice(0,-1),set,queue);
    if(s.length>2&&s.endsWith('よう')){stem=s.slice(0,-2);addCandidate(set,queue,stem+'る');if(stem==='し')addCandidate(set,queue,'する');if(stem==='こ')addCandidate(set,queue,'くる');}
    if(s.length>1&&s.endsWith('う'))fromORowStem(s.slice(0,-1),set,queue);
    if(s.length>1&&s.endsWith('な'))addCandidate(set,queue,s.slice(0,-1));
    if(s.length>1&&s.endsWith('ろ'))addCandidate(set,queue,s.slice(0,-1)+'る');
    if(s.length>1&&s.endsWith('よ'))addCandidate(set,queue,s.slice(0,-1)+'る');
    if(s==='しろ'||s==='せよ')addCandidate(set,queue,'する');
    if(s==='こい')addCandidate(set,queue,'くる');
    if(s.length>1&&!s.endsWith('れば'))fromERowStem(s,set,queue);
    if(/(いて|いた)$/.test(s))addCandidate(set,queue,s.slice(0,-2)+'く');
    if(/(いで|いだ)$/.test(s))addCandidate(set,queue,s.slice(0,-2)+'ぐ');
    if(/(して|した)$/.test(s)){stem=s.slice(0,-2);addCandidate(set,queue,stem+'す');addCandidate(set,queue,stem+'する');}
    if(/(んで|んだ)$/.test(s)){stem=s.slice(0,-2);['む','ぶ','ぬ'].forEach(function(x){addCandidate(set,queue,stem+x);});}
    if(/(って|った)$/.test(s)){stem=s.slice(0,-2);['う','つ','る','く'].forEach(function(x){addCandidate(set,queue,stem+x);});}
    if(s.length>1&&(s.endsWith('て')||s.endsWith('た')))addCandidate(set,queue,s.slice(0,-1)+'る');
    ['れなかった','れない','れました','れません','れる','れた','れて'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromARowStem(s.slice(0,-end.length),set,queue);});
    ['させられなかった','させられない','させられました','させられません','させられる','させられた','させられて'].forEach(function(end){if(s.length>end.length&&s.endsWith(end)){stem=s.slice(0,-end.length);addCandidate(set,queue,stem+'る');addCandidate(set,queue,stem+'する');if(stem==='こ')addCandidate(set,queue,'くる');}});
    ['せられなかった','せられない','せられました','せられません','せられる','せられた','せられて','されなかった','されない','されました','されません','される','された','されて'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromARowStem(s.slice(0,-end.length),set,queue);});
    ['させなかった','させない','させました','させません','させる','させた','させて'].forEach(function(end){if(s.length>end.length&&s.endsWith(end)){stem=s.slice(0,-end.length);addCandidate(set,queue,stem+'る');addCandidate(set,queue,stem+'する');if(stem==='こ')addCandidate(set,queue,'くる');}});
    ['せなかった','せない','せました','せません','せる','せた','せて'].forEach(function(end){if(s.length>end.length&&s.endsWith(end))fromARowStem(s.slice(0,-end.length),set,queue);});
    if(s.endsWith('る')&&s.length>1){stem=s.slice(0,-1);last=stem.slice(-1);u=E2U[last];if(u)addCandidate(set,queue,stem.slice(0,-1)+u);}
    if(s.endsWith('できる')&&s.length>3)addCandidate(set,queue,s.slice(0,-3)+'する');
    ['した','して','しない','しなかった','します','しました','しません','しませんでした','しよう','しろ','せよ','される','された','させる','させられる'].forEach(function(x){if(s===x)addCandidate(set,queue,'する');});
    ['きた','きて','きない','きなかった','きます','きました','きません','きませんでした','こよう','こい','こない','こなかった','こさせる','こさせられる','こられる','こられない'].forEach(function(x){if(s===x)addCandidate(set,queue,'くる');});
    ['来た','来て','来ない','来なかった','来ます','来ました','来ません','来ませんでした','来よう','来い','来させる','来させられる','来られる','来られない'].forEach(function(x){if(s===normSearch(x))addCandidate(set,queue,'来る');});
  }
  return Array.from(set);
}
function hasJapanese(s){return /[ぁ-ゖァ-ヺ一-龯々〆ヵヶ]/.test(s);}
function smartMatch(w,q,variants){
  if(!q)return true;
  var jp=[w.kanji,w.displayWord,w.reading].map(normSearch).filter(Boolean),i,j,f,v;
  for(i=0;i<jp.length;i++){
    f=jp[i];
    for(j=0;j<variants.length;j++){
      v=variants[j];
      if(f.indexOf(v)>=0)return true;
      if(hasJapanese(f)&&f.length>=2&&v.length>f.length&&v.indexOf(f)>=0)return true;
    }
  }
  return false;
}
function filtered(){var levels=W.levels(),raw=(document.getElementById('search').value||'').trim(),q=normSearch(raw),variants=q?deinflectSearch(q):[];var a=(W.words||[]).filter(function(w){if(levels.indexOf(w.level)<0)return false;if(selectedKana&&firstKana(w)!==selectedKana)return false;if(!q)return true;return smartMatch(w,q,variants);});a.sort(function(a,b){return hira(a.reading||'').localeCompare(hira(b.reading||''),'ja')||String(a.displayWord||a.kanji||'').localeCompare(String(b.displayWord||b.kanji||''),'ja');});return a;}
function setBusy(v){audioBusy=v;document.querySelectorAll('.play-btn').forEach(function(b){b.disabled=v;});var s=document.getElementById('sampleVoice');if(s)s.disabled=v;var voice=document.getElementById('voice');if(voice)voice.disabled=v;var eng=document.getElementById('audioEngine');if(eng)eng.disabled=v;}
function engineLabel(e){return e==='voicevox'?'VOICEVOX':e==='aivis'?'AivisSpeech / Style-Bert-VITS':e==='device'?'裝置 Japanese voice':'Supertonic 3';}
async function speakWord(w){if(audioBusy)return;setBusy(true);var status=document.getElementById('audioStatus'),name=w.kanji||w.displayWord||w.reading;status.textContent='🔊 正在播放：'+name+'（'+w.reading+'）';try{if(!W.speak){status.textContent='⚠️ 多聲線模組尚未載入。';return;}var used=await W.speak(w.reading,w);status.textContent=used?'✅ 已播放：'+name+'｜'+engineLabel(engine()):'⚠️ 語音暫時無法播放。';}catch(e){status.textContent='⚠️ 播放失敗：'+(e&&e.message?e.message:String(e));}finally{setBusy(false);}}
function render(){view=filtered();W.listView=view;var size=Number(document.getElementById('pageSize').value)||50,pages=Math.max(1,Math.ceil(view.length/size));page=Math.max(1,Math.min(page,pages));var start=(page-1)*size,items=view.slice(start,start+size),levels=W.levels();var filterText=selectedKana?'｜「'+selectedKana+'」開頭':'';document.getElementById('summary').textContent=(levels.length?levels.join(' + '):'未選擇等級')+filterText+'｜找到 '+view.length.toLocaleString()+' 個單字';document.getElementById('pageInfo').textContent=page+' / '+pages;document.getElementById('prevPage').disabled=page<=1;document.getElementById('nextPage').disabled=page>=pages;var body=document.getElementById('vocabBody');if(!items.length){body.innerHTML='<tr><td colspan="5" class="empty">沒有符合目前等級／五十音／搜尋條件的單字。</td></tr>';return;}body.innerHTML=items.map(function(w,i){var written=w.kanji||w.displayWord||w.reading;return '<tr><td class="play-cell"><button type="button" class="btn play-btn" data-i="'+(start+i)+'">▶ 聽</button>'+(window.WordlistConjugation&&WordlistConjugation.canConjugate(w)?'<button type="button" class="btn conj-btn" data-i="'+(start+i)+'" aria-haspopup="dialog">活用</button>':'')+'</td><td class="word-cell">'+esc(written)+'</td><td class="reading-cell">'+esc(w.reading)+'</td><td class="meaning-cell">'+esc(w.meaning)+'</td><td class="level-cell">'+esc(w.level+(w.estimated?' 推定':''))+'</td></tr>';}).join('');body.querySelectorAll('.play-btn').forEach(function(b){b.onclick=function(){var w=view[Number(b.dataset.i)];if(w)speakWord(w);};});body.querySelectorAll('.conj-btn').forEach(function(b){b.onclick=function(ev){ev.preventDefault();ev.stopPropagation();var w=view[Number(b.dataset.i)];if(w&&window.WordlistConjugation)WordlistConjugation.open(w,b);};});}
W.available=function(){page=1;render();};
var voice=document.getElementById('voice');voice.innerHTML=Object.keys(VOICES).map(function(k){return '<option value="'+k+'"'+(k==='F3'?' selected':'')+'>'+VOICES[k][0]+'</option>';}).join('');function voiceDesc(){document.getElementById('voiceDesc').textContent=(VOICES[voice.value]||VOICES.F3)[1];}voice.onchange=voiceDesc;voiceDesc();
document.getElementById('sampleVoice').onclick=async function(){if(audioBusy)return;setBusy(true);var st=document.getElementById('voiceStatus');try{var sample=(W.words||[]).find(function(w){return w.reading==='ありがとう';})||(W.words||[])[0];if(!sample)throw new Error('單字資料尚未載入');st.textContent='正在準備 '+engineLabel(engine())+' 試聽…';var used=await W.speak(sample.reading,sample);st.textContent=used?'✅ 試聽完成：'+engineLabel(engine())+'｜'+sample.reading:'⚠️ 試聽暫時無法播放。';}catch(e){st.textContent='⚠️ 試聽失敗：'+(e&&e.message?e.message:String(e));}finally{setBusy(false);}};
document.querySelectorAll('.level input').forEach(function(x){x.onchange=W.available;});document.querySelectorAll('.preset').forEach(function(b){b.onclick=function(){var a=b.dataset.l.split(',');document.querySelectorAll('.level input').forEach(function(x){x.checked=a.indexOf(x.value)>=0;});W.available();};});document.querySelectorAll('.kana-btn').forEach(function(b){b.onclick=function(){selectedKana=b.dataset.k||'';document.querySelectorAll('.kana-btn').forEach(function(x){x.classList.toggle('active',x===b);});page=1;render();};});document.getElementById('search').oninput=function(){page=1;render();};document.getElementById('pageSize').onchange=function(){page=1;render();};document.getElementById('prevPage').onclick=function(){if(page>1&&!audioBusy){page--;render();document.querySelector('.table-wrap').scrollIntoView({behavior:'smooth',block:'start'});}};document.getElementById('nextPage').onclick=function(){var size=Number(document.getElementById('pageSize').value)||50,pages=Math.max(1,Math.ceil(view.length/size));if(page<pages&&!audioBusy){page++;render();document.querySelector('.table-wrap').scrollIntoView({behavior:'smooth',block:'start'});}};render();W.loadData();})();
