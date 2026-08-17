from pathlib import Path


def replace_once(path, old, new, label):
    p=Path(path); s=p.read_text(encoding='utf-8')
    if new in s:
        print(f'{path}: {label} already applied'); return
    n=s.count(old)
    if n!=1:
        raise SystemExit(f'{path}: {label} expected 1 match, got {n}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')
    print(f'{path}: applied {label}')

# Word audio: mobile uses HF index/bundles first; desktop remains GitHub first.
replace_once('wordaudio-multivoice.js',
"var url1=v.indexGithubUrl||v.indexUrl||'',url2=v.indexHfUrl||'';",
"var m=guard().isMobile,url1=m?(v.indexHfUrl||v.indexGithubUrl||v.indexUrl||''):(v.indexGithubUrl||v.indexUrl||v.indexHfUrl||''),url2=m?(v.indexGithubUrl||v.indexUrl||''):(v.indexHfUrl||'');",
'word index mobile HF first')
replace_once('wordaudio-multivoice.js',
"var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl,bundle.url].filter(Boolean),last=null;",
"var end=offset+size-1,urls=(guard().isMobile?[bundle.hfUrl,bundle.githubUrl,bundle.url]:[bundle.githubUrl,bundle.hfUrl,bundle.url]).filter(Boolean),last=null;",
'word bundle mobile HF first')

# Legacy/dedicated word-list VOICEVOX reader.
replace_once('wordlist-voicevox.js',
"var end=offset+size-1,urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null;",
"var g=window.MobileSupertonicGuard,end=offset+size-1,urls=(g&&g.isMobile?[bundle.hfUrl,bundle.githubUrl]:[bundle.githubUrl,bundle.hfUrl]).filter(Boolean),last=null;",
'wordlist bundle mobile HF first')
replace_once('wordlist-voicevox.js',
"var d=await fetchJsonFallback(sp.indexGithubUrl,sp.indexHfUrl);",
"var g=window.MobileSupertonicGuard,d=await fetchJsonFallback(g&&g.isMobile?(sp.indexHfUrl||sp.indexGithubUrl):(sp.indexGithubUrl||sp.indexHfUrl),g&&g.isMobile?sp.indexGithubUrl:sp.indexHfUrl);",
'wordlist index mobile HF first')

# Listening hosted Supertonic bundles.
replace_once('listening-supertonic-hosted.js',
"var urls=[bundle.githubUrl,bundle.hfUrl].filter(Boolean),last=null,end=offset+size-1;",
"var g=window.MobileSupertonicGuard,urls=(g&&g.isMobile?[bundle.hfUrl,bundle.githubUrl]:[bundle.githubUrl,bundle.hfUrl]).filter(Boolean),last=null,end=offset+size-1;",
'listening Supertonic mobile HF first')

# Conversation: centralize source ordering so all hosted engines share it.
replace_once('conversation-hosted-audio.js',
"function pick(a){return a[Math.floor(Math.random()*a.length)]}",
"function pick(a){return a[Math.floor(Math.random()*a.length)]}\nfunction mobileFirst(urls){const a=(urls||[]).filter(Boolean);return window.MobileSupertonicGuard?.isMobile?a.sort((x,y)=>(/huggingface\\.co/i.test(y)?1:0)-(/huggingface\\.co/i.test(x)?1:0)):a}",
'conversation mobile source ordering helper')
replace_once('conversation-hosted-audio.js',
"async function playRangeUrls(urls,member,rate){let last=null;for(const url of urls.filter(Boolean)){",
"async function playRangeUrls(urls,member,rate){let last=null;for(const url of mobileFirst(urls)){",
'conversation range mobile HF first')
replace_once('conversation-hosted-audio.js',
"for(const url of [sprite.githubUrl,sprite.hfUrl].filter(Boolean)){",
"for(const url of mobileFirst([sprite.githubUrl,sprite.hfUrl])){",
'conversation legacy VOICEVOX mobile HF first')

# Translator: centralize source ordering as well.
replace_once('translator-hosted-voice.js',
"function esc(s){return String(s==null?'':s).replace(/[&<>\"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c];});}",
"function esc(s){return String(s==null?'':s).replace(/[&<>\"']/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c];});}\nfunction mobileFirst(urls){var a=(urls||[]).filter(Boolean),g=window.MobileSupertonicGuard;return g&&g.isMobile?a.sort(function(x,y){return (/huggingface\\.co/i.test(y)?1:0)-(/huggingface\\.co/i.test(x)?1:0);}):a;}",
'translator mobile source ordering helper')
replace_once('translator-hosted-voice.js',
"async function rangeFallback(urls,member,rate){for(var i=0;i<urls.length;i++){try{var b=await range(urls[i],Number(member[0]),Number(member[1]));await bytesPlay(b,rate);return true;}catch(e){}}return false;}",
"async function rangeFallback(urls,member,rate){urls=mobileFirst(urls);for(var i=0;i<urls.length;i++){try{var b=await range(urls[i],Number(member[0]),Number(member[1]));await bytesPlay(b,rate);return true;}catch(e){}}return false;}",
'translator range mobile HF first')
replace_once('translator-hosted-voice.js',
"for(var i=0;i<[sprite.githubUrl,sprite.hfUrl].filter(Boolean).length;i++){var url=[sprite.githubUrl,sprite.hfUrl].filter(Boolean)[i];",
"var mobileUrls=mobileFirst([sprite.githubUrl,sprite.hfUrl]);for(var i=0;i<mobileUrls.length;i++){var url=mobileUrls[i];",
'translator legacy VOICEVOX mobile HF first')

# Listening VOICEVOX sprite candidates: mobile places HF candidates ahead of GitHub.
replace_once('listening.html',
"for(const c of prepared?.candidates||[]){",
"const mobileCandidates=[...(prepared?.candidates||[])];if(window.MobileSupertonicGuard?.isMobile)mobileCandidates.sort((a,b)=>(/huggingface\\.co/i.test(b?.url||'')?1:0)-(/huggingface\\.co/i.test(a?.url||'')?1:0));for(const c of mobileCandidates){",
'listening VOICEVOX mobile HF first')

print('Mobile Hugging Face first patch complete.')
