from pathlib import Path

p=Path('listening.html')
s=p.read_text(encoding='utf-8')

s=s.replace('日本語聽解挑戰 v1.4｜JLPT N1–N5','日本語聽解挑戰 v1.5｜JLPT N1–N5',1)
s=s.replace(
    'VOICEVOX 音訊直接由公開 GitHub Releases 播放；不需外部雲端帳戶、信用卡或額外登入。Supertonic 與裝置語音只作備援。',
    'VOICEVOX 以 GitHub Releases 為主來源，Hugging Face Dataset 為自動備援；兩者都不需學習者登入。Supertonic 與裝置語音作第二層備援。',
    1,
)
s=s.replace('🎭 VOICEVOX<br>GitHub','🎭 VOICEVOX<br>自動備援',1)
s=s.replace(
    '音訊包由本專案 GitHub Actions 產生並直接發佈至 GitHub Releases。正常使用只需開啟網站並開始練習。',
    '音訊包由 GitHub Actions 自動發佈至 GitHub Releases，並可同步鏡像到 Hugging Face。播放失敗時會自動切換來源。',
    1,
)
s=s.replace(
    'Web 句子來源：Hanabira。VOICEVOX 音訊由公開 GitHub Releases 提供，不需登入；Supertonic 3 在瀏覽器內 ONNX 運算；裝置日語語音只作備援。',
    'Web 句子來源：Hanabira。VOICEVOX 以 GitHub Releases 為主來源、Hugging Face Dataset 為自動備援，兩者均不需學習者登入；Supertonic 3 與裝置日語語音作第二層備援。',
    1,
)

start=s.find('let voicevoxIndex={version:2,items:{}};')
end=s.find('async function waitForAiModule(){', start)
if start < 0 or end < 0:
    raise SystemExit('VOICEVOX JavaScript anchors not found')

new='''let voicevoxIndex={version:2,items:{}};
function voicevoxUrls(rec){const raw=Array.isArray(rec?.urls)?rec.urls:[rec?.url,rec?.backupUrl];return[...new Set(raw.filter(x=>typeof x==="string"&&x.trim()).map(x=>x.trim()))]}
function voicevoxProvider(url){return /huggingface\\.co\\//i.test(url)?"Hugging Face 備援":"GitHub Releases"}
async function loadVoicevoxIndex(){const st=$("#voicevoxStatus");try{const r=await fetch("./voicevox-release-index.json",{cache:"no-cache"});if(!r.ok)throw new Error(`HTTP ${r.status}`);const d=await r.json();if(!d||typeof d!=="object"||!d.items)throw new Error("索引格式不正確");voicevoxIndex=d;const n=Object.keys(d.items||{}).length;const backed=Object.values(d.items||{}).filter(rec=>voicevoxUrls(rec).some(u=>/huggingface\\.co\\//i.test(u))).length;st.textContent=n?`✅ VOICEVOX 已準備：${n.toLocaleString()} 題${backed?` · ${backed.toLocaleString()} 題已設定 Hugging Face 自動備援`:""}。現在可直接開始。`:"⚠️ VOICEVOX 音訊索引目前是空的，將使用其他語音備援。";return n}catch(e){voicevoxIndex={version:2,items:{}};st.textContent="⚠️ VOICEVOX 公開音訊包尚未發佈或暫時無法讀取；將使用其他語音備援。";return 0}}
async function prepareVoicevoxAudio(q){const rec=voicevoxIndex?.items?.[q.id],urls=voicevoxUrls(rec);if(!urls.length)return null;try{const candidates=urls.map(url=>{const audio=new Audio(url);audio.preload="auto";return{url,audio,provider:voicevoxProvider(url)}});return{candidates,out:{...rec,source:"VOICEVOX"}}}catch{return null}}
async function speakVoicevox(rate=1){const st=$("#voicevoxStatus");try{let prepared=game.voicevoxPrepared;if(!prepared&&game.voicevoxPromise)prepared=await game.voicevoxPromise;if(!prepared)prepared=await prepareVoicevoxAudio(game.current);if(!prepared?.candidates?.length)throw new Error("此題尚未有 VOICEVOX 音訊");game.voicevoxPrepared=prepared;let lastError=null;for(let i=0;i<prepared.candidates.length;i++){const candidate=prepared.candidates[i];activeAiAudio=candidate.audio;activeAiAudio.currentTime=0;activeAiAudio.playbackRate=rate;try{await activeAiAudio.play()}catch(e){lastError=e;if(String(e?.name||"").includes("NotAllowed")){$("#playCount").textContent=`✅ VOICEVOX 已載入（${candidate.provider}）；iPhone/Safari 請再按一次播放。`;return true}try{activeAiAudio.pause();activeAiAudio.src=""}catch{}activeAiAudio=null;continue}const meta=prepared.out;const who=[meta.speaker,meta.style].filter(Boolean).join("／");if(candidate.provider==="Hugging Face 備援")st.textContent="✅ GitHub 音訊不可用，已自動切換 Hugging Face 備援。";unlockAfterPlay(`VOICEVOX${who?" · "+who:""} · ${candidate.provider}`);return true}throw lastError||new Error("所有 VOICEVOX 音訊來源均無法播放")}catch(e){st.textContent="⚠️ GitHub 與 Hugging Face 的 VOICEVOX 音訊都無法播放；已改用其他語音備援。";return false}}

'''
s=s[:start]+new+s[end:]

for must in [
    'voicevoxUrls(rec)',
    'Hugging Face 自動備援',
    'GitHub 音訊不可用，已自動切換 Hugging Face 備援',
    'prepared.candidates',
    'voicevoxProvider(url)',
]:
    if must not in s:
        raise SystemExit(f'missing expected fallback code: {must}')

p.write_text(s,encoding='utf-8')
print('Patched listening.html with GitHub -> Hugging Face VOICEVOX failover')
