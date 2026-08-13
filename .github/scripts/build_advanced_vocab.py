#!/usr/bin/env python3
from __future__ import annotations
import csv, io, json, re, statistics, sys
from collections import defaultdict
from datetime import date
from pathlib import Path
import requests
from opencc import OpenCC

ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/"advanced-vocab.json"
WORDS_URL="https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/core/words.json"
FREQ_URLS=[
 "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/enrichment/frequency-subtitles.json",
 "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/enrichment/frequency-web.json",
 "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/enrichment/frequency-corpus.json"]
CORE_URL="https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv"
KAIKKI_URLS=[
 "https://kaikki.org/zhwiktionary/%E6%97%A5%E8%AA%9E/kaikki.org-dictionary-%E6%97%A5%E8%AA%9E.jsonl",
 "https://kaikki.org/zhwiktionary/%E6%97%A5%E8%AF%AD/kaikki.org-dictionary-%E6%97%A5%E8%AF%AD.jsonl"]
UA={"User-Agent":"kanuli-japanese-vocab-game/advanced-builder"}; MAX_WORDS=8000
cc=OpenCC("s2twp"); KANA_RE=re.compile(r"^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$"); JP_RE=re.compile(r"[ぁ-ゖァ-ヺ一-龯々〆ヵヶ]")
BLOCK=("arch","obs","dated","hist","rare","dial","surname","given name","proper noun","place name","person name")

def get_json(u):
 r=requests.get(u,timeout=90,headers=UA); r.raise_for_status(); return r.json()

def primary(e):
 ks=e.get("kanji") or []; rs=e.get("kana") or []
 w=next((x.get("text") for x in ks if x.get("common") and x.get("text")),None) or next((x.get("text") for x in ks if x.get("text")),None)
 rlist=[x for x in rs if x.get("common") and x.get("text")] or [x for x in rs if x.get("text")]
 if not rlist:return None
 if w:
  app=[x for x in rlist if "*" in (x.get("appliesToKanji") or []) or w in (x.get("appliesToKanji") or [])]; rd=(app or rlist)[0]["text"]
 else: rd=rlist[0]["text"]; w=rd
 return (w,rd) if KANA_RE.match(rd or "") else None

def forms(e): return {x.get("text") for g in (e.get("kanji") or [],e.get("kana") or []) for x in g if x.get("text")}
def blocked(e):
 text=" ".join(str(x).lower() for s in e.get("sense",[]) for k in ("misc","dialect","partOfSpeech") for x in (s.get(k) or []))
 return any(t in text for t in BLOCK)
def pos(e):
 p=" ".join(str(x).lower() for s in e.get("sense",[]) for x in (s.get("partOfSpeech") or []))
 if "verb" in p:return "verb"
 if "adverb" in p:return "adv"
 if "adjective" in p:return "adj"
 if "conjunction" in p:return "conj"
 if "particle" in p:return "particle"
 if "noun" in p:return "noun"
 return "other"

def core_forms():
 try:
  r=requests.get(CORE_URL,timeout=90,headers=UA); r.raise_for_status(); seen=set()
  lines=[x for x in r.text.splitlines() if not x.startswith("#")]
  for row in csv.reader(io.StringIO("\n".join(lines)),delimiter="\t"):
   if len(row)>6:
    w=re.sub(r"<[^>]+>|\s+","",row[3]);
    if w:seen.add(w)
    f=re.sub(r"[一-龯々〆ヵヶ]+\[([^\]]+)\]",r"\1",row[6]); f=re.sub(r"\[([^\]]+)\]",r"\1",f); f=re.sub(r"<[^>]+>|\s+","",f)
    if KANA_RE.match(f or ""):seen.add(f)
  return seen
 except Exception as e: print("core dedupe unavailable",e,file=sys.stderr); return set()

def extract_freq(data):
 ranks={}; counts={}
 def walk(x,d=0):
  if d>8:return
  if isinstance(x,list):
   for y in x:walk(y,d+1)
  elif isinstance(x,dict):
   term=next((x.get(k) for k in ("word","text","term","surface","lemma") if isinstance(x.get(k),str)),None)
   if term:
    rv=next((x.get(k) for k in ("rank","frequency_rank","freq_rank") if isinstance(x.get(k),(int,float))),None)
    cv=next((x.get(k) for k in ("count","frequency","freq") if isinstance(x.get(k),(int,float))),None)
    if rv and rv>0:ranks[term]=min(float(rv),ranks.get(term,float("inf")))
    elif cv and cv>0:counts[term]=max(float(cv),counts.get(term,0))
   for k,v in x.items():
    if isinstance(k,str) and JP_RE.search(k) and isinstance(v,(int,float)) and v>0:counts[k]=max(float(v),counts.get(k,0))
    elif isinstance(v,(dict,list)):walk(v,d+1)
 walk(data)
 for n,(t,_) in enumerate(sorted(counts.items(),key=lambda z:z[1],reverse=True),1):ranks.setdefault(t,n)
 return ranks

def freq_maps():
 out=[]
 for u in FREQ_URLS:
  try:
   m=extract_freq(get_json(u)); print("frequency",len(m),u); out.append(m)
  except Exception as e:print("frequency unavailable",u,e,file=sys.stderr)
 return [m for m in out if m]
def agg_rank(fs,maps):
 vals=[]
 for m in maps:
  h=[m[f] for f in fs if f in m]
  if h:vals.append(min(h))
 return int(statistics.median(vals)) if vals else None
def est(rank):
 if rank is None:return "N1"
 if rank<=600:return "N5"
 if rank<=1600:return "N4"
 if rank<=3600:return "N3"
 if rank<=7200:return "N2"
 return "N1"

def glosses(o):
 out=[]
 for s in o.get("senses") or []:
  tags=set(s.get("tags") or [])
  if tags & {"form-of","alt-of","no-gloss","obsolete","archaic"}:continue
  for g in s.get("glosses") or []:
   g=re.sub(r"\s+"," ",str(g)).strip(" 。；;")
   if not 1<len(g)<=90 or re.match(r"^(見|参見|同|另見)[：: ]",g):continue
   t=cc.convert(g)
   if t not in out:out.append(t)
   if len(out)>=2:return out
 return out

def get_zh(targets):
 last=None
 for u in KAIKKI_URLS:
  try:
   r=requests.get(u,stream=True,timeout=(30,180),headers=UA); r.raise_for_status(); found=defaultdict(list); matched=0
   for raw in r.iter_lines(decode_unicode=True):
    if not raw:continue
    try:o=json.loads(raw)
    except:continue
    if o.get("lang_code")!="ja" or o.get("word") not in targets:continue
    gs=glosses(o); matched+=1
    if gs:found[o["word"]].extend(x for x in gs if x not in found[o["word"]])
   print("Kaikki matched",matched,"with gloss",len(found)); return found,u
  except Exception as e:last=e; print("Kaikki failed",u,e,file=sys.stderr)
 raise RuntimeError(f"Chinese Wiktionary unavailable: {last}")

def main():
 src=get_json(WORDS_URL); words=src.get("words",[]); core=core_forms(); fm=freq_maps(); cand={}; byform=defaultdict(set)
 for e in words:
  if e.get("jlpt_waller") or blocked(e):continue
  p=primary(e)
  if not p:continue
  w,rd=p; fs=forms(e)
  if w in core or rd in core or fs & core:continue
  cid=str(e.get("id")); cand[cid]=(e,w,rd,fs,agg_rank(fs,fm))
  for f in fs:byform[f].add(cid)
 print("advanced candidates",len(cand)); zh,zhurl=get_zh(set(byform)); gids=defaultdict(list)
 for f,gs in zh.items():
  for cid in byform[f]:
   for g in gs:
    if g not in gids[cid]:gids[cid].append(g)
 out=[]; seen=set()
 for cid,(e,w,rd,fs,rank) in cand.items():
  gs=gids.get(cid)
  if not gs:continue
  key=(rd,w)
  if key in seen:continue
  seen.add(key); out.append({"id":f"adv-{cid}","level":est(rank),"estimated":True,"reading":rd,"kanji":w if re.search(r"[一-龯々〆ヵヶ]",w) else "","displayWord":w,"meaning":"；".join(gs[:2]),"pos":pos(e),"frequencyRank":rank,"source":"JMdict common + 中文維基詞典（進階補充）","sourceType":"advanced"})
 out.sort(key=lambda x:(x["frequencyRank"] is None,x["frequencyRank"] or 999999,x["reading"])); out=out[:MAX_WORDS]
 levels={f"N{i}":sum(x["level"]==f"N{i}" for x in out) for i in range(1,6)}
 payload={"metadata":{"generated":date.today().isoformat(),"count":len(out),"levels":levels,"classification":"Estimated learning bands; not official JLPT classifications.","sources":["jkindrix/japanese-language-data common JMdict subset (CC BY-SA 4.0)","JMdict / EDRDG","Chinese Wiktionary via kaikki.org (CC BY-SA + GFDL)"],"chineseSourceUrl":zhurl},"words":out}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8"); print("wrote",len(out),levels)
 if len(out)<300:raise RuntimeError(f"Suspiciously small supplement: {len(out)}")
if __name__=="__main__":main()
