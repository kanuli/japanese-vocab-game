(function(){'use strict';
var voice=document.getElementById('voice');
if(!voice)return;
var card=voice.closest?voice.closest('section.card'):null;
if(!card||card.querySelector('.voice-toggle'))return;

/* Voice controls disclosure. Mobile starts collapsed to save vertical space;
   desktop starts expanded. Existing voice controls and event listeners are
   preserved because the original DOM nodes are moved, not recreated. */
var children=[];
while(card.firstChild)children.push(card.removeChild(card.firstChild));

var toggle=document.createElement('button');
toggle.type='button';
toggle.className='voice-toggle';
toggle.setAttribute('aria-controls','voiceToggleContent');

var content=document.createElement('div');
content.id='voiceToggleContent';
content.className='voice-toggle-content';
children.forEach(function(node){
  if(node.nodeType===1&&node.tagName==='H2')return;
  content.appendChild(node);
});
card.appendChild(toggle);
card.appendChild(content);

var style=document.createElement('style');
style.textContent='.voice-toggle{appearance:none;width:100%;border:0;background:transparent;color:#172033;padding:0;display:flex;align-items:center;justify-content:space-between;gap:10px;font:inherit;font-size:18px;font-weight:850;text-align:left;cursor:pointer;min-height:40px}.voice-toggle::after{content:"▾";font-size:14px;color:#667085;transition:transform .16s ease}.card.voice-collapsed .voice-toggle::after{transform:rotate(-90deg)}.voice-toggle-content{margin-top:10px}.card.voice-collapsed .voice-toggle-content{display:none}.voice-toggle:focus-visible{outline:2px solid #3568dd;outline-offset:4px;border-radius:6px}@media(max-width:820px){.voice-toggle{min-height:44px;font-size:16px}.voice-toggle-content{margin-top:8px}}';
document.head.appendChild(style);

var isMobile=window.matchMedia&&window.matchMedia('(max-width: 820px)').matches;
function setOpen(open){
  card.classList.toggle('voice-collapsed',!open);
  toggle.setAttribute('aria-expanded',open?'true':'false');
  toggle.textContent=open?'🔊 單字語音｜VOICEVOX / Supertonic 3 / AivisSpeech':'🔊 單字語音｜按此展開';
}
setOpen(!isMobile);
toggle.addEventListener('click',function(){
  setOpen(toggle.getAttribute('aria-expanded')!=='true');
});

/* Load the adjective/noun inflection extension only after the established
   verb engine and its UI have finished loading. This keeps verb behaviour
   untouched and lets the list refresh its 活用 buttons once extended. */
document.addEventListener('DOMContentLoaded',function(){
  if(window.__wordlistAdjNounInflectionLoaded)return;
  window.__wordlistAdjNounInflectionLoaded=true;
  var s=document.createElement('script');
  s.src='./wordlist-adjective-noun-inflection.js?v=20260912v1';
  s.onload=function(){if(window.WA&&typeof window.WA.available==='function')window.WA.available();};
  document.head.appendChild(s);
},{once:true});
})();
