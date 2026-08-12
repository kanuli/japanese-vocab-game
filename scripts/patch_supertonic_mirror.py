#!/usr/bin/env python3
from pathlib import Path

HF_MODEL='https://huggingface.co/datasets/kanuli1983/japanese-listening-voicevox-backup/resolve/main/supertonic-3/onnx'
HF_VOICE='https://huggingface.co/datasets/kanuli1983/japanese-listening-voicevox-backup/resolve/main/supertonic-3/voice_styles'
OLD_MODEL='https://huggingface.co/Supertone/supertonic-3/resolve/main/onnx'
OLD_VOICE='https://huggingface.co/Supertone/supertonic-3/resolve/main/voice_styles'

src=Path('src/listening-supertonic-entry.js')
s=src.read_text(encoding='utf-8')
assert OLD_MODEL in s and OLD_VOICE in s
s=s.replace(OLD_MODEL,HF_MODEL).replace(OLD_VOICE,HF_VOICE)
src.write_text(s,encoding='utf-8')

vendor=Path('vendor/supertonic-browser.js')
v=vendor.read_text(encoding='utf-8')
assert OLD_MODEL in v and OLD_VOICE in v
v=v.replace(OLD_MODEL,HF_MODEL).replace(OLD_VOICE,HF_VOICE)
vendor.write_text(v,encoding='utf-8')

sw=Path('supertonic-sw.js')
sw.write_text(r'''const CACHE_NAME="supertonic-model-v1";
const HF_HOST="huggingface.co";
const OWN_PREFIX="/datasets/kanuli1983/japanese-listening-voicevox-backup/resolve/main/supertonic-3/";
const OLD_PREFIX="/Supertone/supertonic-3/resolve/main/";
const GH_BASE="https://github.com/kanuli/japanese-vocab-game/releases/download/supertonic-3-model-v1/";
self.addEventListener("install",event=>{self.skipWaiting()});
self.addEventListener("activate",event=>{event.waitUntil(self.clients.claim())});
function infoFor(request){try{const u=new URL(request.url);if(u.hostname!==HF_HOST)return null;let rel="";if(u.pathname.startsWith(OWN_PREFIX))rel=u.pathname.slice(OWN_PREFIX.length);else if(u.pathname.startsWith(OLD_PREFIX))rel=u.pathname.slice(OLD_PREFIX.length);else return null;const parts=rel.split("/");if(parts.length!==2)return null;const [section,file]=parts;if(section!=="onnx"&&section!=="voice_styles")return null;return{section,file}}catch{return null}}
function releaseUrl(info){const name=info.section==="onnx"?`onnx-${info.file}`:`voice-${info.file}`;return GH_BASE+encodeURIComponent(name)}
function upstreamUrl(info){return `https://huggingface.co/Supertone/supertonic-3/resolve/main/${info.section}/${info.file}`}
async function legacyCacheHit(cache,info){const keys=await cache.keys();const suffix=`/${info.section}/${info.file}`;for(const req of keys){try{if(new URL(req.url).pathname.endsWith(suffix)){const hit=await cache.match(req);if(hit)return hit}}catch{}}return null}
async function fetchOk(url){const r=await fetch(url,{cache:"force-cache"});if(!r.ok&&r.type!=="opaque")throw new Error(`HTTP ${r.status}`);return r}
self.addEventListener("fetch",event=>{const info=infoFor(event.request);if(!info)return;event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const exact=await cache.match(event.request,{ignoreSearch:true});if(exact)return exact;const legacy=await legacyCacheHit(cache,info);if(legacy){await cache.put(event.request,legacy.clone());return legacy}let response=null;try{response=await fetchOk(event.request)}catch{}if(!response){try{response=await fetchOk(releaseUrl(info))}catch{}}if(!response)response=await fetchOk(upstreamUrl(info));if(response.ok||response.type==="opaque")await cache.put(event.request,response.clone());return response})())});
''',encoding='utf-8')
print('Patched Supertonic to project Hugging Face mirror with GitHub Release + upstream service-worker fallbacks')
