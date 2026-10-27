const {webkit}=require(process.cwd()+'/node_modules/playwright');

const timeout=(p,ms,label)=>Promise.race([
  p,
  new Promise((_,reject)=>setTimeout(()=>reject(new Error(label+' timeout')),ms))
]);

async function installTapTarget(page){
  await page.evaluate(()=>{
    let b=document.getElementById('__mobileAudioUnlockProbe');
    if(!b){
      b=document.createElement('button');
      b.id='__mobileAudioUnlockProbe';
      b.type='button';
      b.textContent='unlock audio';
      b.style.cssText='position:fixed;left:8px;top:8px;width:120px;height:70px;z-index:2147483647;opacity:.01;pointer-events:auto';
      document.body.appendChild(b);
    }
  });
  const target=page.locator('#__mobileAudioUnlockProbe');
  await target.waitFor({state:'visible',timeout:5000});
  await target.tap({timeout:5000});
  await page.waitForTimeout(300);
}

async function probeHosted(page,catalogName,groupName,label){
  return page.evaluate(async ({catalogName,groupName,label})=>{
    const g=window.MobileSupertonicGuard;
    if(!g?.playHostedBytes)throw new Error('shared player missing');
    const cat=await fetch('./'+catalogName+'?probe='+Date.now(),{cache:'no-store'}).then(r=>{
      if(!r.ok)throw new Error(label+' catalog HTTP '+r.status);
      return r.json();
    });
    if(cat.status!=='ready')throw new Error(label+' catalog not ready');
    const group=cat[groupName]||{};
    const key=Object.keys(group)[0];
    const meta=group[key];
    if(!meta)throw new Error(label+' no voice metadata');
    const idxUrls=[meta.indexHfUrl,meta.indexGithubUrl,meta.indexUrl].filter(Boolean);
    let idx=null,lastIndexError=null;
    for(const u of idxUrls){
      try{
        const r=await fetch(u,{cache:'no-store'});
        if(!r.ok)throw new Error('HTTP '+r.status);
        idx=await r.json();
        break;
      }catch(e){lastIndexError=e;}
    }
    if(!idx)throw new Error(label+' index failed: '+String(lastIndexError||'no URL'));
    const bundle=Object.values(idx.bundles||{})[0];
    if(!bundle)throw new Error(label+' no bundle');
    const row=Object.entries(bundle.members||{})[0];
    if(!row)throw new Error(label+' no bundle member');
    const member=row[1],offset=Number(member[0]),size=Number(member[1]);
    const urls=[bundle.hfUrl,bundle.githubUrl,bundle.url].filter(Boolean);
    let bytes=null,status=0,usedUrl='',lastRangeError=null;
    for(const url of urls){
      try{
        const resp=await fetch(url,{headers:{Range:'bytes='+offset+'-'+(offset+size-1)},cache:'no-store'});
        const len=Number(resp.headers.get('content-length')||0);
        if(resp.status!==206&&!(resp.status===200&&len===size))throw new Error('Range HTTP '+resp.status+' len '+len+' expected '+size);
        const b=await resp.arrayBuffer();
        if(b.byteLength!==size)throw new Error('bytes '+b.byteLength+'/'+size);
        bytes=b;status=resp.status;usedUrl=url;break;
      }catch(e){lastRangeError=e;}
    }
    if(!bytes)throw new Error(label+' range failed: '+String(lastRangeError||'no source'));
    const started=performance.now();
    const out=await g.playHostedBytes(bytes,1);
    return {
      label,key,status,size,
      backend:out?.backend||'',
      provider:/huggingface\.co/i.test(usedUrl)?'hf':'github',
      ms:Math.round(performance.now()-started),
      state:g.audioState()
    };
  },{catalogName,groupName,label});
}


async function testWordlistPublicPlayback(page){
  // Use the actual vocabulary UI click (not just a raw HTTP Range or
  // directly invoking MobileSupertonicGuard) on desktop/mobile page.
  await page.waitForFunction(()=>Array.isArray(window.WA?.words)&&WA.words.length>32000
    &&window.WORD_AUDIO_MULTI_VOICE?.version>=5,null,{timeout:45000});
  const voiceToggle=page.locator('.voice-toggle');
  if(await voiceToggle.count()&&await voiceToggle.getAttribute('aria-expanded')==='false'){
    await voiceToggle.tap();
    await page.waitForFunction(()=>document.querySelector('.voice-toggle')?.getAttribute('aria-expanded')==='true');
  }
  const cases=[['supertonic3','F3'],['voicevox','s01']];
  for(const [engine,voice] of cases){
    const diag=await page.evaluate(()=>{
      const e=document.querySelector('#audioEngine'),v=document.querySelector('#voice');
      const style=e&&getComputedStyle(e),rect=e&&e.getBoundingClientRect();
      return{enginePresent:!!e,engineDisabled:e?.disabled,
        engineValue:e?.value,engineHTML:e?.outerHTML?.slice(0,650),
        display:style?.display,visibility:style?.visibility,
        rect:rect?{width:rect.width,height:rect.height}:null,
        voicePresent:!!v,voiceDisabled:v?.disabled,
        voiceOptions:v?.options?.length,words:window.WA?.words?.length};
    });
    console.log('WORDLIST ENGINE DIAGNOSTIC',JSON.stringify({engine,voice,diag}));
    await page.selectOption('#audioEngine',engine,{timeout:5000});
    await page.waitForFunction(({voice})=>Array.from(document.querySelectorAll('#voice option'))
      .some(o=>o.value===voice),{voice},{timeout:25000});
    await page.selectOption('#voice',voice);
    const w=await page.evaluate(async eng=>{
      const c=await window.WORD_AUDIO_MULTI_VOICE.loadCatalog(eng);
      if(!c||c.status!=='ready')throw new Error('Unready '+eng+' catalog');
      // Select a real dictionary word guaranteed present in this engine.
      const w=window.WA.words.find(w=>!!c.words[
        String(w.reading||'')+'|'+String(w.kanji||w.displayWord||w.reading||'')]);
      if(!w)throw new Error('No vocabulary item found in '+eng+' catalog');
      return{reading:w.reading,written:w.kanji||w.displayWord||w.reading};
    },engine);
    await page.locator('#search').fill(w.reading);
    await page.waitForFunction(w=>Array.from(document.querySelectorAll('#vocabBody tr'))
      .some(r=>r.querySelector('.word-cell')?.textContent===w.written
        &&r.querySelector('.reading-cell')?.textContent===w.reading),
      w,{timeout:25000});
    const rowIndex=await page.evaluate(w=>Array.from(document.querySelectorAll('#vocabBody tr'))
      .findIndex(r=>r.querySelector('.word-cell')?.textContent===w.written
        &&r.querySelector('.reading-cell')?.textContent===w.reading),w);
    if(rowIndex<0)throw new Error('Exact wordlist row not found '+JSON.stringify({engine,voice,w}));
    const row=page.locator('#vocabBody tr').nth(rowIndex);
    const before=await page.evaluate(()=>Number(window.WA?.__speakSeq||0));
    await row.locator('.play-btn').tap({timeout:20000});
    try{
      await page.waitForFunction(({before})=>{
        const r=window.WA?.lastSpeak;
        return !!r&&r.seq>before&&!r.pending&&(r.playbackSuccess||r.playbackFailure||r.hostedMiss);
      },{before},{timeout:30000});
    }catch(err){
      const state=await page.evaluate(()=>({
        speak:window.WA?.lastSpeak,status:document.querySelector('#audioStatus')?.textContent,
        voice:document.querySelector('#voice')?.value,engine:document.querySelector('#audioEngine')?.value
      }));
      throw new Error('PUBLIC WORDLIST PLAYBACK TIMEOUT '+JSON.stringify({engine,voice,w,state,error:String(err)}));
    }
    const rec=await page.evaluate(()=>({
      status:document.querySelector('#audioStatus')?.textContent||'',
      speak:window.WA?.lastSpeak,
      guard:window.MobileSupertonicGuard?.audioState?.()
    }));
    if(!rec.speak?.hostedHit||!rec.speak?.playbackSuccess||rec.speak?.playbackFailure
        ||rec.speak?.fallbackUsed||rec.speak?.provider!==engine||rec.speak?.key!==voice
        ||!rec.speak?.resolvedUrl||!/^✅/.test(rec.status)){
      throw new Error('PUBLIC WORDLIST PLAYBACK FAIL '+JSON.stringify({engine,voice,w,rec}));
    }
    console.log('PUBLIC WORDLIST AUDIO PASS',JSON.stringify({
      engine,voice,word:w,status:rec.status,provider:rec.speak.provider,
      selectedVoice:rec.speak.selectedVoice,hostedHit:rec.speak.hostedHit,
      playbackSuccess:rec.speak.playbackSuccess,
      httpStatus:rec.speak.httpStatus,resolvedUrl:rec.speak.resolvedUrl,
      mobileAudioContext:rec.guard?.audioContextState
    }));
  }
}

async function checkGenericVoiceTest(context,path,playRealAudio=false){
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  try{
    const r=await page.goto('http://127.0.0.1:4173/'+path+'?genericVoiceTest='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
    if(!r||r.status()>=400)throw new Error(path+' HTTP '+(r?.status()||'none'));
    await page.locator('#genericVoiceTest').waitFor({state:'visible',timeout:12000});
    await installTapTarget(page);
    await page.selectOption('#genericVoiceEngine','voicevox');
    await page.waitForFunction(()=>{
      const s=document.querySelector('#genericVoiceChoice');
      return !!s&&s.options.length>=44&&!/載入中|失敗/.test(s.textContent||'');
    },null,{timeout:15000});
    const state=await page.evaluate(()=>({
      card:!!document.querySelector('#genericVoiceTest'),
      engine:document.querySelector('#genericVoiceEngine')?.value,
      voiceCount:document.querySelector('#genericVoiceChoice')?.options.length||0,
      mode:document.documentElement.dataset.mobileSupertonic,
      local:window.MobileSupertonicGuard?.localAllowed,
      version:window.MobileSupertonicGuard?.version
    }));
    if(!state.card||state.engine!=='voicevox'||state.voiceCount<44||state.mode!=='hosted-only'||state.local!==false||state.version<4){
      throw new Error(path+' generic voice setup '+JSON.stringify(state));
    }
    if(playRealAudio){
      await page.selectOption('#genericVoiceChoice',{index:1});
      await page.locator('#genericVoicePlay').tap({timeout:5000});
      await page.waitForFunction(()=>/^✅/.test(document.querySelector('#genericVoiceStatus')?.textContent||''),null,{timeout:30000});
    }
    if(errors.length)throw new Error(errors.join(' | '));
    console.log('GENERIC VOICE TEST PASS',path,JSON.stringify({...state,realPlayback:playRealAudio}));
  }finally{
    await page.close();
  }
}

(async()=>{
  const browser=await webkit.launch({headless:true});
  const context=await browser.newContext({
    userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1',
    viewport:{width:390,height:844},
    hasTouch:true,
    isMobile:true,
    serviceWorkers:'block'
  });
  try{
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',e=>errors.push(String(e)));
    const r=await page.goto('http://127.0.0.1:4173/wordaudio.html?realMobileAudio='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
    if(!r||r.status()>=400)throw new Error('wordaudio HTTP '+(r?.status()||'none'));
    await page.waitForTimeout(1200);
    await installTapTarget(page);
    const base=await page.evaluate(()=>({
      mode:document.documentElement.dataset.mobileSupertonic,
      guard:window.MobileSupertonicGuard?.audioState?.(),
      version:window.MobileSupertonicGuard?.version,
      engine:document.querySelector('#audioEngine')?.value
    }));
    if(base.mode!=='hosted-only'||base.version<4||base.engine!=='supertonic3'||base.guard?.unlockRequested!==true){
      throw new Error('mobile unlock/setup '+JSON.stringify(base));
    }
    console.log('UNLOCK PASS',JSON.stringify(base));

    const vv=await timeout(probeHosted(page,'word-voicevox-catalog.json','speakers','VOICEVOX'),30000,'VOICEVOX real playback');
    console.log('REAL AUDIO PASS',JSON.stringify(vv));
    const st=await timeout(probeHosted(page,'word-supertonic3-catalog.json','voices','Supertonic'),30000,'Supertonic real playback');
    console.log('REAL AUDIO PASS',JSON.stringify(st));
    if(!vv.backend||!st.backend)throw new Error('missing playback backend');
    if(errors.length)throw new Error(errors.join(' | '));
    await page.close();

    const other=['wordlist.html','listening.html','conversation.html','pronunciation.html','translator.html'];
    for(const p of other){
      const q=await context.newPage(),errs=[];
      q.on('pageerror',e=>errs.push(String(e)));
      const rr=await q.goto('http://127.0.0.1:4173/'+p+'?mobileAudio='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
      if(!rr||rr.status()>=400)throw new Error(p+' HTTP '+(rr?.status()||'none'));
      await q.waitForTimeout(1200);
      await installTapTarget(q);
      const s=await q.evaluate(()=>({
        mode:document.documentElement.dataset.mobileSupertonic,
        version:window.MobileSupertonicGuard?.version,
        state:window.MobileSupertonicGuard?.audioState?.(),
        local:window.MobileSupertonicGuard?.localAllowed
      }));
      if(s.mode!=='hosted-only'||s.version<4||s.local!==false||s.state?.unlockRequested!==true||errs.length){
        throw new Error(p+' '+JSON.stringify({s,errs}));
      }
      console.log('MOBILE PAGE PASS',p,JSON.stringify(s));
      if(p==='wordlist.html')await testWordlistPublicPlayback(q);
      await q.close();
    }

    await checkGenericVoiceTest(context,'index.html',true);
    await checkGenericVoiceTest(context,'grammar.html',false);
    await checkGenericVoiceTest(context,'wordaudio.html',false);
    await checkGenericVoiceTest(context,'vocab-plus-game.html',false);
    await checkGenericVoiceTest(context,'vocabulary-plus.html',false);

    const mock=await context.newPage();
    const mr=await mock.goto('http://127.0.0.1:4173/mocktest.html?voiceExclusion='+Date.now(),{waitUntil:'domcontentloaded',timeout:30000});
    if(!mr||mr.status()>=400)throw new Error('mocktest HTTP '+(mr?.status()||'none'));
    await mock.waitForTimeout(1200);
    const excluded=await mock.evaluate(()=>!document.querySelector('#genericVoiceTest')&&!document.querySelector('#pageSampleVoice'));
    if(!excluded)throw new Error('mocktest must remain excluded from generic voice test');
    console.log('MOCKTEST VOICE EXCLUSION PASS');
    await mock.close();
  }finally{
    await browser.close();
  }
})().catch(e=>{console.error('MOBILE HOSTED AUDIO FAIL',e);process.exit(1)});
