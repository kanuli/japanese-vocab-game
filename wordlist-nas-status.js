(function(root){
'use strict';
function install(){
  var W=root.WA=root.WA||{};
  if(typeof W.speak!=='function'||W.__nasStatusInstalled)return;
  W.__nasStatusInstalled=true;
  var baseSpeak=W.speak;

  W.speak=async function(){
    var out=await baseSpeak.apply(W,arguments);
    var rec=W.lastSpeak||{};
    if(rec&&rec.nas&&rec.playbackSuccess&&!rec.playbackFailure){
      var msg=rec.conjugation
        ? '✅ NAS Japanese API 動詞活用已播放｜'+String(rec.provider||out&&out.engine||'')+'｜'+String(rec.selectedVoice||rec.key||out&&out.key||'')
        : '✅ NAS Japanese API 已播放｜'+String(rec.provider||out&&out.engine||'')+'｜'+String(rec.selectedVoice||rec.key||out&&out.key||'');
      setTimeout(function(){
        var audioStatus=document.getElementById('audioStatus');
        var voiceStatus=document.getElementById('voiceStatus');
        if(audioStatus)audioStatus.textContent=msg;
        if(voiceStatus)voiceStatus.textContent=msg;
      },0);
    }
    return out;
  };
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});
else install();
})(typeof window!=='undefined'?window:this);
