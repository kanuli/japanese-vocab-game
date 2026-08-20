#!/usr/bin/env python3
"""Build ready delta catalogs/indexes from generated missing-word manifests.

Base 22,333-word hosted libraries remain immutable. The browser checks these
small delta catalogs only when a base catalog has no exact reading|written key.
"""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
LABELS={'F1':'🌙 沉穩低柔女聲（F1）','F2':'🌸 明亮活潑女聲（F2）','F3':'🎙️ 專業播音女聲（F3）','F4':'✨ 清晰自信女聲（F4）','F5':'💕 溫柔療癒女聲（F5）','M1':'⚡ 活力自信男聲（M1）','M2':'🌑 低沉穩重男聲（M2）','M3':'🧭 權威專業男聲（M3）','M4':'🙂 柔和親切男聲（M4）','M5':'📖 溫暖舒緩男聲（M5）'}

def write(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def bundle(man,repo,hf,tag,hfdir):
 asset=str(man['asset']);return {'githubUrl':f'https://github.com/{repo}/releases/download/{tag}/{asset}','hfUrl':f'https://huggingface.co/datasets/{hf}/resolve/main/{hfdir}/{asset}?download=true','members':man['members']}
def index_urls(name,repo,hf,tag,hfdir):
 return {'indexGithubUrl':f'https://github.com/{repo}/releases/download/{tag}/{name}','indexHfUrl':f'https://huggingface.co/datasets/{hf}/resolve/main/{hfdir}/indexes/{name}?download=true'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--engine',choices=['voicevox','supertonic3','aivis'],required=True);ap.add_argument('--catalog',default='word-audio-delta-catalog.json');ap.add_argument('--manifest-dir',required=True);ap.add_argument('--out-dir',default='word-audio-delta-publish');ap.add_argument('--repo',default=os.environ.get('GITHUB_REPO','kanuli/japanese-vocab-game'));ap.add_argument('--hf',default=os.environ.get('HF_DATASET_REPO','kanuli1983/japanese-listening-voicevox-backup'));ap.add_argument('--tag',required=True);ap.add_argument('--hf-dir',required=True);args=ap.parse_args()
 src=json.loads(Path(args.catalog).read_text(encoding='utf-8'));words=src.get('words') or {};items=src.get('items') or [];n=int(src.get('wordCount',-1));
 if n<=0 or n!=len(words) or n!=len(items):raise SystemExit('Bad/empty delta source catalog')
 ids={str(x['id']) for x in items};mdir=Path(args.manifest_dir);out=Path(args.out_dir);out.mkdir(parents=True,exist_ok=True)
 group={};recordings=0
 if args.engine=='voicevox':
  files=sorted(mdir.glob('s??-delta.json'))
  if len(files)!=43:raise SystemExit(f'Expected 43 VOICEVOX delta manifests, got {len(files)}')
  for p in files:
   m=json.loads(p.read_text(encoding='utf-8'));key=str(m['speakerKey']);members=m.get('members') or {}
   if set(members)!=ids:raise SystemExit(f'{key} delta coverage mismatch')
   idxname=f'word-voicevox-delta-{key}-index.json';idx={'version':1,'engine':'voicevox','speakerKey':key,'speaker':m['speaker'],'style':m['style'],'styleId':m['styleId'],'wordCount':n,'shardCount':1,'bundles':{'0':bundle(m,args.repo,args.hf,args.tag,args.hf_dir)}};write(out/idxname,idx)
   group[key]={'name':m['speaker'],'style':m['style'],'styleId':m['styleId'],'credit':m.get('credit') or f"VOICEVOX:{m['speaker']}",**index_urls(idxname,args.repo,args.hf,args.tag,args.hf_dir)};recordings+=n
  cat={'version':1,'status':'ready','engine':'voicevox-delta','storage':'github-releases+hf-range-bundles','wordCount':n,'speakerCount':len(group),'recordingCount':recordings,'shardCount':1,'coverageRule':'exact reading|written-form','words':words,'speakers':group}
  name='word-voicevox-delta-catalog.json'
 elif args.engine=='supertonic3':
  files=sorted(mdir.glob('*-shard0.json'));found={}
  for p in files:
   m=json.loads(p.read_text(encoding='utf-8'));v=str(m.get('voice') or '');
   if v in LABELS:found[v]=m
  if set(found)!=set(LABELS):raise SystemExit(f'Supertonic delta voices mismatch: {sorted(found)}')
  for v in LABELS:
   m=found[v];members=m.get('members') or {}
   if set(members)!=ids:raise SystemExit(f'{v} delta coverage mismatch')
   idxname=f'word-supertonic3-delta-{v}-index.json';idx={'version':1,'engine':'supertonic-3','voice':v,'label':LABELS[v],'wordCount':n,'shardCount':1,'bundles':{'0':bundle(m,args.repo,args.hf,args.tag,args.hf_dir)}};write(out/idxname,idx)
   group[v]={'label':LABELS[v],**index_urls(idxname,args.repo,args.hf,args.tag,args.hf_dir)};recordings+=n
  cat={'version':1,'status':'ready','engine':'supertonic-3-delta','storage':'github-releases+hf-range-bundles','wordCount':n,'voiceCount':len(group),'recordingCount':recordings,'shardCount':1,'coverageRule':'exact reading|written-form','words':words,'voices':group};name='word-supertonic3-delta-catalog.json'
 else:
  files=sorted(mdir.glob('a*-shard0.json'))
  if not 1<=len(files)<=4:raise SystemExit(f'Expected 1-4 Aivis delta manifests, got {len(files)}')
  model=None
  for p in files:
   m=json.loads(p.read_text(encoding='utf-8'));k=str(m.get('key') or '');members=m.get('members') or {}
   if not k or set(members)!=ids:raise SystemExit(f'{p.name} delta coverage mismatch')
   idxname=f'word-aivis-delta-{k}-index.json';idx={'version':1,'engine':'aivisspeech-style-bert-vits2','voice':k,'speaker':m['speaker'],'style':m['style'],'styleId':m['styleId'],'displayName':f"{m['speaker']}｜{m['style']}",'modelName':m['modelName'],'modelVersion':m['modelVersion'],'modelArchitecture':m['modelArchitecture'],'license':m['license'],'licenseSha256':m['licenseSha256'],'wordCount':n,'shardCount':1,'bundles':{'0':bundle(m,args.repo,args.hf,args.tag,args.hf_dir)}};write(out/idxname,idx)
   group[k]={'speaker':m['speaker'],'style':m['style'],'displayName':idx['displayName'],'modelName':m['modelName'],'modelVersion':m['modelVersion'],'modelArchitecture':m['modelArchitecture'],'license':m['license'],'licenseSha256':m['licenseSha256'],**index_urls(idxname,args.repo,args.hf,args.tag,args.hf_dir)};recordings+=n
   mm={'name':m['modelName'],'version':m['modelVersion'],'architecture':m['modelArchitecture'],'license':m['license'],'licenseSha256':m['licenseSha256']}
   if model is not None and model!=mm:raise SystemExit('Aivis model metadata differs across delta manifests')
   model=mm
  cat={'version':1,'status':'ready','engine':'aivisspeech-style-bert-vits2-delta','storage':'github-releases+hf-range-bundles','wordCount':n,'voiceCount':len(group),'recordingCount':recordings,'shardCount':1,'coverageRule':'exact reading|written-form','model':model,'words':words,'voices':group};name='word-aivis-delta-catalog.json'
 write(out/name,cat);print(args.engine,{'words':n,'voices':len(group),'recordings':recordings,'catalog':name})
if __name__=='__main__':main()
