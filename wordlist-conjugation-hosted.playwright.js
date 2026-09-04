'use strict';
const {chromium}=require('playwright');
const http=require('http');
const fs=require('fs');
const path=require('path');
const ROOT=process.cwd();
const PORT=Number(process.env.CONJ_HOSTED_PORT||4174);
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.mp3':'audio/mpeg','.ico':'image/x-icon'};
const MP3=Buffer.from('SUQzBAAAAAAAIlRTU0UAAAAOAAADTGF2ZjYxLjcuMTAzAAAAAAAAAAAAAAD/4zjAAAAAAAAAAAAASW5mbwAAAA8AAAAHAAAC0ABmZmZmZmZmZmZmZmZmZoCAgICAgICAgICAgICAmZmZmZmZmZmZmZmZmZmzs7Ozs7Ozs7Ozs7Ozs7PMzMzMzMzMzMzMzMzMzObm5ubm5ubm5ubm5ubm//////////////////8AAAAATGF2YzYxLjE5AAAAAAAAAAAAAAAAJAQgAAAAAAAAAtA/N3DCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD/4xjEAAAAA0gAAAAATEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVX/4xjEOwAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVX/4xjEdgAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUxBTUUzLjEwMFVVVVVVVVVVVVX/4xjEsQAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/4xjExAAAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/4xjExAAAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/4xjExAAAAA0gAAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVU=','base64');
const FORMS=[
  {lemma:'食べる', written:'食べます', reading:'たべます'},
  {lemma:'食べる', written:'食べなかった', reading:'たべなかった'},
  {lemma:'食べる', written:'食べている', reading:'たべている'},
  {lemma:'食べる', written:'食べました', reading:'たべました'},
  {lemma:'食べる', written:'食べなければならない', reading:'たべなければならない'},
  {lemma:'書く', written:'書きます', reading:'かきます'},
  {lemma:'行く', written:'行って', reading:'いって'},
  {lemma:'行く', written:'行った', reading:'いった'},
  {lemma:'来る', written:'来ます', reading:'きます'},
  {lemma:'来る', written:'来ません', reading:'きません'},
  {lemma:'来る', written:'来なかった', reading:'こなかった'},
  {lemma:'する', written:'します', reading:'します'},
  {lemma:'愛する', written:'愛します', reading:'あいします'}
];
function startServer(){
  return new Promise((resolve,reject)=>{
    const server=http.createServer((req,res)=>{
      const u=new URL(req.url||'/','http://127.0.0.1');
      let rel=decodeURIComponent(u.pathname);
      if(rel==='/')rel='/wordlist.html';
      const file=path.normalize(path.join(ROOT, rel.replace(/^\/+/ , '')));
      if(!file.startsWith(ROOT)){res.writeHead(403);res.end();return;}
      fs.readFile(file,(err,buf)=>{
        if(err){res.writeHead(404);res.end('not found');return;}
        res.writeHead(200,{'content-type':MIME[path.extname(file)]||'application/octet-stream','cache-control':'no-store'});
        res.end(buf);
      });
    });
    server.listen(PORT,'127.0.0.1',()=>resolve(server));
    server.on('error',reject);
  });
}
function idOf(reading){return 'c'+Buffer.from(reading).toString('hex').slice(0,14);}
function fixtureCatalog(kind){
  const words={};
  FORMS.forEach(f=>{words[f.reading+'|'+f.written]=[idOf(f.reading),0];});
  if(kind==='st'){
    const voices={};
    ['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'].forEach(v=>{
      voices[v]={label:v,indexUrl:'./word-supertonic3-conj-v2-'+v+'-index.json?v=fixture',indexGithubUrl:'https://github.com/kanuli/japanese-vocab-game/releases/download/word-supertonic3-conj-v2/'+v+'-index.json'};
    });
    return {version:1,status:'ready',engine:'supertonic-3-conj-delta',wordCount:Object.keys(words).length,voices,words};
  }
  if(kind==='vv'){
    const speakers={s01:{speaker:'四国めたん',style:'ノーマル',indexUrl:'./word-voicevox-conj-s01-index.json?v=fixture',indexGithubUrl:'https://github.com/kanuli/japanese-vocab-game/releases/download/word-voicevox-conj-v1/s01-index.json'}};
    return {version:1,status:'ready',engine:'voicevox-conj-delta',wordCount:Object.keys(words).length,speakers,words};
  }
  const voices={a01:{displayName:'コハク｜ノーマル',indexUrl:'./word-aivis-conj-a01-index.json?v=fixture',indexGithubUrl:'https://github.com/kanuli/japanese-vocab-game/releases/download/word-aivis-conj-v1/a01-index.json'}};
  return {version:1,status:'ready',engine:'aivisspeech-conj-delta',wordCount:Object.keys(words).length,voices,words};
}
function fixtureIndex(voice, kind){
  const members={};
  FORMS.forEach(f=>{members[idOf(f.reading)]=[0,MP3.length];});
  let githubUrl;
  if(kind==='st') githubUrl='https://github.com/kanuli/japanese-vocab-game/releases/download/word-supertonic3-conj-v2/'+voice+'-shard0.tar';
  else if(kind==='vv') githubUrl='https://github.com/kanuli/japanese-vocab-game/releases/download/word-voicevox-conj-v1/'+voice+'-shard0.tar';
  else githubUrl='https://github.com/kanuli/japanese-vocab-game/releases/download/word-aivis-conj-v1/'+voice+'-shard0.tar';
  return {version:1,voice,wordCount:FORMS.length,shardCount:1,bundles:{'0':{githubUrl,hfUrl:githubUrl,url:githubUrl,members}}};
}
async function installMocks(page){
  await page.route('**/*',async route=>{
    const req=route.request();
    const url=req.url();
    if(/word-supertonic3-conj-v2-catalog\.json/.test(url)){
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureCatalog('st'))});
    }
    if(/word-voicevox-conj-catalog\.json/.test(url)){
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureCatalog('vv'))});
    }
    if(/word-aivis-conj-catalog\.json/.test(url)){
      return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureCatalog('ai'))});
    }
    const stIdx=url.match(/(?:word-supertonic3-conj-v2-)?([FM]\d)-index\.json/);
    if(stIdx) return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureIndex(stIdx[1],'st'))});
    if(/(?:word-voicevox-conj-)?s01-index\.json/.test(url)) return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureIndex('s01','vv'))});
    if(/(?:word-aivis-conj-)?a01-index\.json/.test(url)) return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixtureIndex('a01','ai'))});
    if(/releases\/download\/word-(supertonic3-conj-v2|voicevox-conj-v1|aivis-conj-v1)\//.test(url) && /\.tar/.test(url)){
      return route.fulfill({status:206,contentType:'audio/mpeg',headers:{'content-length':String(MP3.length),'content-range':'bytes 0-'+(MP3.length-1)+'/'+MP3.length},body:MP3});
    }
    return route.continue();
  });
}
async function waitVocab(page){
  await page.waitForFunction(()=>{
    const W=window.WA;
    return !!(W&&Array.isArray(W.words)&&W.words.length>100 && document.querySelector('#vocabBody tr'));
  },{timeout:120000});
}
async function openVerb(page, written){
  await page.evaluate((written)=>{
    const W=window.WA;
    const api=window.WordlistConjugation;
    const word=(W&&W.words||[]).find(w=>String(w.kanji||w.displayWord||w.reading||'')===written);
    if(!word) throw new Error('verb not found '+written);
    if(!api||typeof api.open!=='function') throw new Error('conjugation UI unavailable');
    api.open(word,null);
  },written);
  await page.locator('#conjOverlay.is-open').waitFor();
}
async function setEngineVoice(page, engine, voice){
  await page.waitForSelector('#audioEngine',{timeout:30000});
  await page.selectOption('#audioEngine', engine);
  await page.waitForTimeout(400);
  await page.waitForFunction((v)=>{
    const sel=document.getElementById('voice');
    if(!sel)return false;
    return Array.from(sel.options).some(o=>o.value===v);
  }, voice, {timeout:30000});
  await page.selectOption('#voice', voice);
}
async function clickForm(page, written){
  const btn=page.locator('.conj-row').filter({has:page.locator('.conj-written',{hasText:written})}).locator('.conj-audio-btn').first();
  await btn.waitFor();
  const seq0=await page.evaluate(()=>Number((window.WA&&WA.__speakSeq)||0));
  await btn.click();
  await page.waitForFunction((seq0)=>{
    const rec=(window.WA&&WA.lastSpeak)||(window.WordlistConjugation&&WordlistConjugation.lastSpeak)||{};
    if(!rec||rec.pending) return false;
    if(!(Number(rec.seq)>Number(seq0))) return false;
    return !!(rec.hostedHit||rec.fallbackUsed||rec.playbackFailure||rec.hostedMiss);
  }, seq0, {timeout:20000});
  return page.evaluate(()=>{
    const rec=(window.WA&&WA.lastSpeak)||(window.WordlistConjugation&&WordlistConjugation.lastSpeak)||{};
    return {
      requestedReading:rec.requestedReading||'',
      selectedVoice:rec.selectedVoice||'',
      provider:rec.provider||'',
      resolvedUrl:rec.resolvedUrl||rec.resolvedAsset||'',
      hostedHit:!!rec.hostedHit,
      hostedMiss:!!rec.hostedMiss,
      fallbackUsed:!!rec.fallbackUsed,
      playbackSuccess:!!rec.playbackSuccess,
      playbackFailure:!!rec.playbackFailure,
      catalog:rec.catalog||'',
      key:rec.key||'',
      httpStatus:rec.httpStatus||0,
      error:rec.error||''
    };
  });
}
function classify(rec, expectedVoice, expectedEngine){
  const lookupPass=!!(rec.hostedHit && rec.resolvedUrl && rec.fallbackUsed===false && rec.provider===expectedEngine && (rec.selectedVoice===expectedVoice||rec.key===expectedVoice));
  const urlPass=!!(rec.resolvedUrl && rec.resolvedUrl.indexOf(expectedVoice)!==-1 && /releases\/download|huggingface|fixture|shard/.test(rec.resolvedUrl+rec.catalog));
  const audiblePass=!!(lookupPass && rec.playbackSuccess && !rec.playbackFailure);
  return {lookupPass:lookupPass&&urlPass, audiblePass, rec};
}
async function runMocked(browser, viewport, label){
  const context=await browser.newContext(viewport);
  const page=await context.newPage();
  await installMocks(page);
  await page.goto('http://127.0.0.1:'+PORT+'/wordlist.html',{waitUntil:'domcontentloaded'});
  await waitVocab(page);
  const report=[];
  const voiceCases=[
    {engine:'supertonic3', voice:'F3'},
    {engine:'supertonic3', voice:'F1'},
    {engine:'supertonic3', voice:'M1'},
    {engine:'voicevox', voice:'s01'},
    {engine:'aivis', voice:'a01'}
  ];
  for(const vc of voiceCases){
    await setEngineVoice(page, vc.engine, vc.voice);
    await openVerb(page, '食べる');
    const rec=await clickForm(page, '食べました');
    const cls=classify(rec, vc.voice, vc.engine);
    report.push({case:label+' '+vc.engine+' '+vc.voice+' たべました', lookup:cls.lookupPass, audible:cls.audiblePass, rec});
    if(!cls.lookupPass) throw new Error(label+' lookup FAIL '+vc.engine+' '+vc.voice+' '+JSON.stringify(rec));
    await page.locator('.conj-close').click();
    await page.locator('#conjOverlay').waitFor({state:'hidden'});
  }
  const formLemmas=['食べる','書く','行く','来る','する','勉強する'];
  await setEngineVoice(page,'supertonic3','F3');
  for(const form of FORMS){
    if(formLemmas.indexOf(form.lemma)<0) continue;
    await openVerb(page, form.lemma);
    const rec=await clickForm(page, form.written);
    const cls=classify(rec,'F3','supertonic3');
    report.push({case:label+' F3 '+form.written, lookup:cls.lookupPass, audible:cls.audiblePass, rec});
    if(!cls.lookupPass) throw new Error(label+' form lookup FAIL '+form.written+' '+JSON.stringify(rec));
    if(rec.requestedReading!==form.reading) throw new Error('reading mismatch '+form.reading+' vs '+rec.requestedReading);
    await page.locator('.conj-close').click();
    await page.locator('#conjOverlay').waitFor({state:'hidden'});
  }
  await page.fill('#search','ない');
  await page.waitForTimeout(200);
  const nai=page.locator('#vocabBody tr').filter({hasText:'ない'}).first();
  await nai.waitFor({timeout:30000});
  if(await nai.locator('.conj-btn').count()) throw new Error('ない unexpectedly has 活用');
  await page.fill('#search','高校');
  await page.waitForTimeout(200);
  const noun=page.locator('#vocabBody tr').filter({hasText:'高校'}).first();
  await noun.waitFor({timeout:30000});
  if(await noun.locator('.conj-btn').count()) throw new Error('高校 unexpectedly has 活用');
  await context.close();
  return report;
}
async function liveProbe(){
  const out={tabemasu:null, tabemashita:null};
  try{
    const cat=JSON.parse(fs.readFileSync(path.join(ROOT,'word-supertonic3-catalog.json'),'utf8'));
    const idxPath=path.join(ROOT,'word-supertonic3-F3-index.json');
    const idx=JSON.parse(fs.readFileSync(idxPath,'utf8'));
    const entry=cat.words['たべます|食べます'];
    if(entry){
      const shard=String(entry[1]);
      const id=entry[0];
      const bundle=idx.bundles[shard];
      const member=bundle.members[id];
      const url=bundle.githubUrl||bundle.hfUrl;
      const start=Number(member[0]), size=Number(member[1]), end=start+size-1;
      const res=await fetch(url,{headers:{Range:'bytes='+start+'-'+end}});
      out.tabemasu={url, status:res.status, bytes:Number(res.headers.get('content-length')||0), expected:size, ok:res.status===206||res.status===200};
    }
  }catch(e){out.tabemasu={error:String(e&&e.message||e)};}
  try{
    const cat=JSON.parse(fs.readFileSync(path.join(ROOT,'word-supertonic3-conj-catalog.json'),'utf8'));
    const words=cat.words||{};
    const hit=Object.keys(words).find(k=>k.split('|')[0]==='たべました');
    out.tabemashita={hostedInConjV1:!!hit, note:hit?'present in F3 v1':'missing from F3 8000-cap catalog; v2 generation required'};
  }catch(e){out.tabemashita={error:String(e&&e.message||e)};}
  return out;
}
(async()=>{
  const server=await startServer();
  let browser;
  try{
    browser=await chromium.launch({headless:true});
    const desktop=await runMocked(browser,{viewport:{width:1280,height:800}},'desktop');
    const mobile=await runMocked(browser,{viewport:{width:390,height:844},isMobile:true,hasTouch:true},'mobile');
    const live=await liveProbe();
    const lookupFails=[].concat(desktop,mobile).filter(x=>!x.lookup);
    const audibleOk=[].concat(desktop,mobile).filter(x=>x.audible).length;
    const lookupOk=[].concat(desktop,mobile).filter(x=>x.lookup).length;
    console.log('HOSTED LOOKUP PASS', lookupOk, 'cases; audible', audibleOk);
    console.log('LIVE PROBE', JSON.stringify(live));
    if(lookupFails.length) throw new Error('lookup failures '+JSON.stringify(lookupFails));
    if(!live.tabemasu||!live.tabemasu.ok){
      console.log('LIVE HTTP for lemma たべます not confirmed in this runner:', live.tabemasu);
    }else{
      console.log('LIVE HTTP lemma たべます', live.tabemasu.status, live.tabemasu.url);
    }
  }finally{
    if(browser)await browser.close();
    server.close();
  }
})().catch(err=>{
  console.error('HOSTED PLAYWRIGHT FAIL', err&&err.stack||err);
  process.exit(1);
});
