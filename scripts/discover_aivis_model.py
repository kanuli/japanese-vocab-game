#!/usr/bin/env python3
import hashlib,json,os,re,urllib.request
from pathlib import Path
ENGINE=os.environ.get('AIVIS_ENGINE_URL','http://127.0.0.1:10101').rstrip('/');OUT=Path(os.environ.get('OUT','aivis-model.json'));MAX_STYLES=int(os.environ.get('MAX_STYLES','4'))
def get(path):
 with urllib.request.urlopen(ENGINE+path,timeout=180) as r:return json.loads(r.read().decode('utf-8'))
models=get('/aivm_models');speakers=get('/speakers');defaults=[x for x in models.values() if x.get('is_default_model')]
if not defaults:raise SystemExit('No default AIVMX model')
m=defaults[0];man=m.get('manifest') or {};lic=str(man.get('license') or '');arch=str(man.get('model_architecture') or '')
if m.get('is_private_model'):raise SystemExit('Default AIVMX is private')
if 'Style-Bert-VITS2' not in arch:raise SystemExit('Default AIVMX is not Style-Bert-VITS2: '+arch)
accepted=('acml','aivis common model license','cc0','creative commons zero','パブリックドメイン')
if not any(x in lic.lower() for x in accepted):raise SystemExit('License not on publish allowlist: '+re.sub(r'\s+',' ',lic)[:500])
ms=(man.get('speakers') or [])
if not ms:raise SystemExit('No AIVMX speaker metadata')
name=str(ms[0].get('name') or '').strip();g=next((x for x in speakers if str(x.get('name') or '').strip()==name),None)
if not g:raise SystemExit('Default AIVMX speaker not in /speakers: '+name)
styles=list(g.get('styles') or []);pref=('ノーマル','Normal','通常');styles.sort(key=lambda x:(0 if str(x.get('name') or '') in pref else 1,int(x.get('id',0))));styles=styles[:MAX_STYLES]
if not styles:raise SystemExit('No Aivis talk styles')
out={'version':1,'modelUuid':str(man.get('uuid') or ''),'modelName':str(man.get('name') or name),'modelVersion':str(man.get('version') or ''),'modelArchitecture':arch,'license':lic,'licenseSha256':hashlib.sha256(lic.encode()).hexdigest(),'speaker':name,'styles':[{'key':f'a{i:02d}','speaker':name,'style':str(x.get('name') or ''),'styleId':int(x['id'])} for i,x in enumerate(styles,1)]}
OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Aivis model:',out['modelName'],out['modelVersion'],out['modelArchitecture']);print('Speaker:',name,'styles:',out['styles']);print('License:',re.sub(r'\s+',' ',lic)[:500])
