#!/usr/bin/env python3
from pathlib import Path

p = Path('listening.html')
s = p.read_text(encoding='utf-8')

s = s.replace('日本語聽解挑戰 v1.5｜JLPT N1–N5', '日本語聽解挑戰 v1.6｜JLPT N1–N5')

old_pool = '''function selectedLevels(){return $$(".level input:checked").map(x=>x.value)}
function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return p}'''
new_pool = '''function selectedLevels(){return $$(".level input:checked").map(x=>x.value)}
function jpKey(s){return String(s||"").normalize("NFKC").replace(/[\\s　。、，,.！？!?「」『』（）()]/g,"")}
function uniqueBySentence(rows){const seen=new Set();return rows.filter(x=>{const k=jpKey(x.jp);if(!k||seen.has(k))return false;seen.add(k);return true})}
function pool(){let p=items.filter(x=>selectedLevels().includes(x.level)&&mutations(x.jp).length>=3);if($("input[name=mode]:checked").value==="wrong")p=p.filter(x=>wrong.has(x.id));return uniqueBySentence(p)}'''
if old_pool not in s:
    raise SystemExit('pool anchor not found')
s = s.replace(old_pool, new_pool, 1)

old_start_next = '''function start(){const p=pool(),n=+$("input[name=qcount]:checked").value;game={pool:p,order:shuffle(p),limit:n,infinite:n===0,index:0,score:0,streak:0,current:null,plays:0,locked:false,quality:"",lastAudioLabel:"",voicevoxPromise:null,voicevoxPrepared:null};$("#setup").style.display="none";$("#quiz").style.display="block";$("#end").style.display="none";$("#choices").style.display="grid";next()}
async function next(){hideSheet();if(!game)return;if(!game.infinite&&game.index>=game.limit){finish();return}$("#choices").innerHTML='<div class="muted" style="grid-column:1/-1;text-align:center;padding:24px">正在準備 4 個繁體中文相似選項…</div>';let tries=0,q,m,prepared=null;const maxTry=Math.min(35,Math.max(1,game.order.length));while(tries<maxTry&&!prepared){if(game.index>=game.order.length)game.order=shuffle(game.pool);q=game.order[(game.index+tries)%game.order.length];m=makeChoices(q);if(m)prepared=await prepareChineseChoices(q,m);tries++}if(!m||!prepared){alert("目前無法產生 4 個可靠而不重複的繁體中文選項。請按重新載入 Web 後再試。");quit();return}game.current=q;game.quality=m.quality;game.currentZh=prepared.find(x=>x.jp===q.jp)?.zh||"";game.plays=0;game.lastAudioLabel="";game.voicevoxPrepared=null;game.voicevoxPromise=$("input[name=audioEngine]:checked")?.value==="voicevox"?prepareVoicevoxAudio(q):null;game.aiVoiceForQuestion=null;if($("#aiVoice")?.value==="random"){const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];game.aiVoiceForQuestion=a[Math.floor(Math.random()*a.length)]}game.locked=$("input[name=reveal]:checked").value==="hide";$("#playCount").textContent=game.locked?"請先播放音訊":"可直接選擇，亦可播放音訊";$("#choices").innerHTML=prepared.map((x,i)=>`<button class="choice${game.locked?" locked":""}" ${game.locked?"disabled":""} data-v="${encodeURIComponent(x.jp)}"><strong>${String.fromCharCode(65+i)}.</strong> ${esc(x.zh)}</button>`).join("");$$(".choice").forEach(b=>b.onclick=()=>answer(decodeURIComponent(b.dataset.v)));stats()}'''
new_start_next = '''function start(){const p=pool(),n=+$("input[name=qcount]:checked").value;const finiteLimit=n===0?0:Math.min(n,p.length);game={pool:p,order:shuffle(p),limit:finiteLimit,infinite:n===0,index:0,score:0,streak:0,current:null,plays:0,locked:false,quality:"",lastAudioLabel:"",voicevoxPromise:null,voicevoxPrepared:null,cycle:1};$("#setup").style.display="none";$("#quiz").style.display="block";$("#end").style.display="none";$("#choices").style.display="grid";next()}
function refillInfiniteOrder(){game.order=shuffle(game.pool);if(game.order.length>1&&game.current&&jpKey(game.order[0].jp)===jpKey(game.current.jp))game.order.push(game.order.shift());game.cycle++}
async function next(){hideSheet();if(!game)return;if(!game.infinite&&game.index>=game.limit){finish();return}$("#choices").innerHTML='<div class="muted" style="grid-column:1/-1;text-align:center;padding:24px">正在準備 4 個繁體中文相似選項…</div>';let tries=0,q=null,m=null,prepared=null;const maxTry=Math.min(60,Math.max(1,game.pool.length));while(tries<maxTry&&!prepared){if(!game.order.length){if(!game.infinite)break;refillInfiniteOrder()}q=game.order.shift()||null;if(!q)break;m=makeChoices(q);if(m)prepared=await prepareChineseChoices(q,m);tries++}if(!q||!m||!prepared){if(!game.infinite&&game.index>0){game.limit=game.index;finish();return}alert("目前無法產生足夠的可靠繁體中文選項。請按重新載入 Web 後再試。");quit();return}game.current=q;game.quality=m.quality;game.currentZh=prepared.find(x=>x.jp===q.jp)?.zh||"";game.plays=0;game.lastAudioLabel="";game.voicevoxPrepared=null;game.voicevoxPromise=$("input[name=audioEngine]:checked")?.value==="voicevox"?prepareVoicevoxAudio(q):null;game.aiVoiceForQuestion=null;if($("#aiVoice")?.value==="random"){const a=window.SupertonicAI?.voices||["F1","F2","F3","F4","F5","M1","M2","M3","M4","M5"];game.aiVoiceForQuestion=a[Math.floor(Math.random()*a.length)]}game.locked=$("input[name=reveal]:checked").value==="hide";$("#playCount").textContent=game.locked?"請先播放音訊":"可直接選擇，亦可播放音訊";$("#choices").innerHTML=prepared.map((x,i)=>`<button class="choice${game.locked?" locked":""}" ${game.locked?"disabled":""} data-v="${encodeURIComponent(x.jp)}"><strong>${String.fromCharCode(65+i)}.</strong> ${esc(x.zh)}</button>`).join("");$$(".choice").forEach(b=>b.onclick=()=>answer(decodeURIComponent(b.dataset.v)));stats()}'''
if old_start_next not in s:
    raise SystemExit('start/next anchor not found')
s = s.replace(old_start_next, new_start_next, 1)

# Show the unique usable pool rather than raw duplicate records in setup availability.
old_av = 'function availability(){const p=pool();let t=`目前選擇：${p.length.toLocaleString()} 句。`;'
new_av = 'function availability(){const p=pool();let t=`目前選擇：${p.length.toLocaleString()} 個不重複句子。`;'
if old_av not in s:
    raise SystemExit('availability anchor not found')
s = s.replace(old_av, new_av, 1)

p.write_text(s, encoding='utf-8')
print('Patched Listening no-repeat logic')
