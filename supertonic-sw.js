const CACHE_NAME="supertonic-model-v1";
self.addEventListener("install",event=>{self.skipWaiting()});
self.addEventListener("activate",event=>{event.waitUntil(self.clients.claim())});
function isSupertonicAsset(request){try{const u=new URL(request.url);return u.hostname==="huggingface.co"&&u.pathname.startsWith("/Supertone/supertonic-3/resolve/")&&(u.pathname.includes("/onnx/")||u.pathname.includes("/voice_styles/"))}catch{return false}}
self.addEventListener("fetch",event=>{if(!isSupertonicAsset(event.request))return;event.respondWith((async()=>{const cache=await caches.open(CACHE_NAME);const hit=await cache.match(event.request,{ignoreSearch:true});if(hit)return hit;const response=await fetch(event.request);if(response.ok||response.type==="opaque")await cache.put(event.request,response.clone());return response})())});
