import * as ort from 'onnxruntime-web';
import {loadTextToSpeech, loadVoiceStyle, writeWavFile} from './supertonic-helper.js';

const MODEL_BASE='https://huggingface.co/Supertone/supertonic-3/resolve/main/onnx';
const VOICE_BASE='https://huggingface.co/Supertone/supertonic-3/resolve/main/voice_styles';
const VOICES=['F1','F2','F3','F4','F5','M1','M2','M3','M4','M5'];

ort.env.wasm.numThreads=1;
ort.env.wasm.wasmPaths=new URL('./ort/',import.meta.url).href;

let tts=null;
let initPromise=null;
const styles=new Map();
let lastUrl='';

async function checkedFetch(url){
  const r=await fetch(url,{cache:'force-cache'});
  if(!r.ok)throw new Error(`HTTP ${r.status}: ${url}`);
  return r;
}

async function preflight(){
  const [cfg,voice]=await Promise.all([
    checkedFetch(`${MODEL_BASE}/tts.json`).then(r=>r.json()),
    checkedFetch(`${VOICE_BASE}/F1.json`).then(r=>r.json())
  ]);
  if(!cfg?.ae?.sample_rate||!voice?.style_ttl||!voice?.style_dp)throw new Error('Supertonic 資料格式不完整');
  return {sampleRate:cfg.ae.sample_rate,voices:[...VOICES]};
}

async function init(progressCallback=()=>{}){
  if(tts)return {ready:true,voices:[...VOICES],sampleRate:tts.sampleRate};
  if(initPromise)return initPromise;
  initPromise=(async()=>{
    await preflight();
    progressCallback('正在下載／載入 AI 模型…首次約 400 MB');
    const sessionOptions={executionProviders:['wasm'],graphOptimizationLevel:'all'};
    const loaded=await loadTextToSpeech(MODEL_BASE,sessionOptions,(name,i,total)=>{
      progressCallback(`正在載入 ${name}（${i}/${total}）…`);
    });
    tts=loaded.textToSpeech;
    progressCallback('✅ Supertonic 3 AI 語音已準備');
    return {ready:true,voices:[...VOICES],sampleRate:tts.sampleRate};
  })().catch(e=>{initPromise=null;throw e});
  return initPromise;
}

async function getStyle(voice){
  const id=VOICES.includes(voice)?voice:'F1';
  if(styles.has(id))return styles.get(id);
  const st=await loadVoiceStyle([`${VOICE_BASE}/${id}.json`]);
  styles.set(id,st);
  return st;
}

async function synthesize(text,{voice='F1',speed=1,totalSteps=5}={}){
  if(!tts)throw new Error('AI 語音尚未啟用');
  const style=await getStyle(voice);
  const result=await tts.call(String(text||''),'ja',style,totalSteps,Math.max(.7,Math.min(2,speed)),.12);
  const wav=writeWavFile(result.wav,tts.sampleRate);
  if(lastUrl)URL.revokeObjectURL(lastUrl);
  lastUrl=URL.createObjectURL(new Blob([wav],{type:'audio/wav'}));
  return {url:lastUrl,voice,duration:Number(result.duration?.[0]||0),sampleRate:tts.sampleRate};
}

function isReady(){return !!tts}

window.SupertonicAI={preflight,init,synthesize,isReady,voices:[...VOICES]};
window.dispatchEvent(new Event('supertonic-ai-module-ready'));
