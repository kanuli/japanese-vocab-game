'use strict';
/* Independent 動詞活用 overlay checks. Does not depend on teacher-audit jobs. */
const {chromium}=require('playwright');
const http=require('http');
const fs=require('fs');
const path=require('path');

const ROOT=process.cwd();
const PORT=Number(process.env.CONJ_PORT||4173);
const MIME={
  '.html':'text/html; charset=utf-8',
  '.js':'text/javascript; charset=utf-8',
  '.css':'text/css; charset=utf-8',
  '.json':'application/json; charset=utf-8',
  '.svg':'image/svg+xml',
  '.png':'image/png',
  '.ico':'image/x-icon'
};

function startServer(){
  return new Promise((resolve,reject)=>{
    const server=http.createServer((req,res)=>{
      const u=new URL(req.url||'/', 'http://127.0.0.1');
      let rel=decodeURIComponent(u.pathname);
      if(rel==='/')rel='/wordlist.html';
      const file=path.normalize(path.join(ROOT, rel.replace(/^\/+/, '')));
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

async function waitVocab(page){
  await page.waitForFunction(()=>{
    const W=window.WA;
    return !!(W&&Array.isArray(W.words)&&W.words.length>100 && document.querySelector('#vocabBody tr'));
  },{timeout:120000});
}

async function findVerbRow(page, written){
  await page.fill('#search', written);
  await page.waitForTimeout(250);
  const row=page.locator('#vocabBody tr').filter({hasText:written}).first();
  await row.waitFor({timeout:30000});
  return row;
}

async function assertNoConj(page, written){
  await page.fill('#search', written);
  await page.waitForTimeout(250);
  const row=page.locator('#vocabBody tr').filter({hasText:written}).first();
  await row.waitFor({timeout:30000});
  const n=await row.locator('.conj-btn').count();
  if(n!==0)throw new Error(written+' unexpectedly has 活用');
}

async function runDesktop(browser){
  const page=await browser.newPage({viewport:{width:1280,height:800}});
  await page.goto('http://127.0.0.1:'+PORT+'/wordlist.html',{waitUntil:'domcontentloaded'});
  await waitVocab(page);
  const row=await findVerbRow(page,'食べる');
  const conjBtn=row.locator('.conj-btn');
  await conjBtn.waitFor();
  const listWrap=page.locator('.table-wrap');
  await listWrap.evaluate(el=>{el.scrollTop=40;});
  const before=await listWrap.evaluate(el=>el.scrollTop);
  await conjBtn.click();
  const overlay=page.locator('#conjOverlay');
  await overlay.waitFor();
  if(!(await overlay.evaluate(el=>el.classList.contains('is-open'))))throw new Error('overlay not open');
  if(await overlay.evaluate(el=>el.classList.contains('is-sheet')))throw new Error('desktop used bottom sheet');
  await page.getByRole('heading',{name:'動詞活用'}).waitFor();
  await page.locator('.conj-section-title',{hasText:'基本活用'}).waitFor();
  await page.locator('.conj-section-title',{hasText:'常用延伸'}).waitFor();
  for(const form of ['食べる','食べます','食べない','食べた','食べて','食べられる','食べよう','食べろ','食べるな','食べれば','食べさせる','食べさせられる']){
    await page.locator('.conj-written',{hasText:form}).first().waitFor();
  }
  for(const form of ['食べなかった','食べません','食べました','食べている','食べたい','食べたら','食べてください']){
    await page.locator('.conj-written',{hasText:form}).first().waitFor();
  }
  const audio=page.locator('.conj-audio-btn').first();
  await audio.click();
  if(!(await overlay.evaluate(el=>el.classList.contains('is-open'))))throw new Error('audio click closed overlay');
  await page.locator('.conj-close').click();
  await overlay.waitFor({state:'hidden'});
  await conjBtn.click();
  await overlay.waitFor();
  await page.keyboard.press('Escape');
  await overlay.waitFor({state:'hidden'});
  await conjBtn.click();
  await overlay.waitFor();
  await overlay.click({position:{x:8,y:8}});
  await overlay.waitFor({state:'hidden'});
  const after=await listWrap.evaluate(el=>el.scrollTop);
  if(Math.abs(after-before)>2)throw new Error('list scroll not preserved desktop '+before+' → '+after);
  await assertNoConj(page,'高校');
  await assertNoConj(page,'ない');
  await page.close();
  return ['desktop ok'];
}

async function runMobile(browser){
  const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const page=await context.newPage();
  await page.goto('http://127.0.0.1:'+PORT+'/wordlist.html',{waitUntil:'domcontentloaded'});
  await waitVocab(page);
  const row=await findVerbRow(page,'食べる');
  const conjBtn=row.locator('.conj-btn');
  await conjBtn.waitFor();
  const box=await conjBtn.boundingBox();
  if(!box||box.height<40)throw new Error('活用 target too small: '+JSON.stringify(box));
  const listWrap=page.locator('.table-wrap');
  await listWrap.evaluate(el=>{el.scrollTop=24;});
  const before=await listWrap.evaluate(el=>el.scrollTop);
  await conjBtn.click();
  const overlay=page.locator('#conjOverlay');
  await overlay.waitFor();
  const sheet=await overlay.evaluate(el=>el.classList.contains('is-sheet'));
  if(!sheet)throw new Error('mobile did not use bottom sheet');
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1);
  if(overflow)throw new Error('horizontal overflow on mobile overlay');
  await page.locator('.conj-section-title',{hasText:'基本活用'}).waitFor();
  await page.locator('.conj-section-title',{hasText:'常用延伸'}).waitFor();
  const dialog=page.locator('.conj-dialog');
  await dialog.evaluate(el=>{el.scrollTop=el.scrollHeight;});
  await page.locator('.conj-written',{hasText:'食べなければならない'}).first().waitFor();
  await page.locator('.conj-close').click();
  await overlay.waitFor({state:'hidden'});
  await conjBtn.click();
  await overlay.waitFor();
  await overlay.click({position:{x:8,y:8}});
  await overlay.waitFor({state:'hidden'});
  const after=await listWrap.evaluate(el=>el.scrollTop);
  if(Math.abs(after-before)>2)throw new Error('list scroll not preserved mobile '+before+' → '+after);
  await assertNoConj(page,'庭');
  await assertNoConj(page,'ない');
  await context.close();
  return ['mobile ok'];
}

(async()=>{
  const server=await startServer();
  let browser;
  try{
    browser=await chromium.launch({headless:true});
    const d=await runDesktop(browser);
    const m=await runMobile(browser);
    console.log('PLAYWRIGHT PASS', d.concat(m).join('; '));
  }finally{
    if(browser)await browser.close();
    server.close();
  }
})().catch(err=>{
  console.error('PLAYWRIGHT FAIL', err&&err.stack||err);
  process.exit(1);
});
