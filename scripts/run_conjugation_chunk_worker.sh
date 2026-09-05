#!/bin/bash
set -euo pipefail
retry() { n=0; until "$@"; do n=$((n+1)); echo "retry $n: $*"; if [ "$n" -ge 3 ]; then return 1; fi; sleep $((n*8)); done; }
INV_FILE="word-conjugation-reading-inventory-${INV}.json"
test -f "$INV_FILE"
if echo "$INV" | grep -q "^smoke"; then BASE_TAG=word-conj-chunks-smoke; else BASE_TAG=word-conj-chunks-v1; fi
export BASE_TAG INV_FILE
python - <<'PY'
import json,os,sys
from pathlib import Path
inv=json.loads(Path(os.environ["INV_FILE"]).read_text(encoding="utf-8"))
cs=int(os.environ["CS"]); ce=int(os.environ["CE"])
if ce<cs: sys.exit("chunk_end < chunk_start")
if ce-cs>3: sys.exit("ONE run = ONE voice + 1-4 chunks")
n=int(inv.get("chunkCount") or 0)
if cs<0 or (n>0 and ce>=n): sys.exit(f"chunk out of range 0..{n-1}")
chunks=list(range(cs,ce+1))
Path("chunks.txt").write_text("\n".join(map(str,chunks))+"\n")
print("chunks", chunks, "baseTag", os.environ["BASE_TAG"], "unique", inv.get("uniqueReadingCount"), "chunkSize", inv.get("chunkSize"))
PY
SAVED_HF_OIDC="${HF_OIDC_RESOURCE-}"
# Public model download must not use dataset OIDC (invalid_grant / aborted grant).
unset HF_OIDC_RESOURCE HF_TOKEN HUGGINGFACE_HUB_TOKEN HUGGING_FACE_HUB_TOKEN || true
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg libsndfile1
if [ "$PROVIDER" = supertonic3 ]; then
  retry python -m pip install --quiet --disable-pip-version-check 'numpy>=1.21,<2' 'supertonic==1.2.2'
  python -c "from supertonic import TTS; print('imported TTS ok')"
  python - <<'PY'
import time, traceback
from supertonic import TTS
last=None
for i in range(1,4):
    try:
        print("prewarm TTS attempt", i, flush=True)
        TTS(auto_download=True)
        print("prewarm TTS ok", flush=True)
        break
    except Exception as e:
        last=e
        print("prewarm TTS failed", i, type(e).__name__, e, flush=True)
        traceback.print_exc()
        time.sleep(8*i)
else:
    raise SystemExit("TTS model download failed: %s: %s" % (type(last).__name__, last))
PY
elif [ "$PROVIDER" = voicevox ]; then
  retry docker pull voicevox/voicevox_engine:cpu-latest
  docker run --rm -d --name voicevox-engine -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
  n=0; until curl -fsS http://127.0.0.1:50021/version >/dev/null; do n=$((n+1)); if [ "$n" -ge 60 ]; then docker logs voicevox-engine || true; exit 1; fi; sleep 2; done
  python - <<'PY'
import json,os
from pathlib import Path
key=os.environ['VOICE']
meta=json.loads(Path('word-voicevox-speakers.json').read_text(encoding='utf-8'))[key]
name=os.environ.get('SPEAKER_NAME_IN') or meta['speaker']
sid=os.environ.get('STYLE_ID_IN') or str(meta['styleId'])
style=os.environ.get('STYLE_NAME_IN') or meta['style']
Path('/tmp/vv.env').write_text('export SPEAKER_NAME=%s\nexport STYLE_ID=%s\nexport STYLE_NAME=%s\n' % (repr(name), repr(sid), repr(style)))
print(key, name, sid, style)
PY
  . /tmp/vv.env
elif [ "$PROVIDER" = aivis ]; then
  mkdir -p "$HOME/.local/share/AivisSpeech-Engine"
  sudo chown -R 1000:1000 "$HOME/.local/share/AivisSpeech-Engine"
  retry docker pull ghcr.io/aivis-project/aivisspeech-engine:cpu-latest
  docker run --rm -d --name aivis-engine -p 127.0.0.1:10101:10101 -v "$HOME/.local/share/AivisSpeech-Engine:/home/user/.local/share/AivisSpeech-Engine-Dev" ghcr.io/aivis-project/aivisspeech-engine:cpu-latest
  n=0; until curl -fsS http://127.0.0.1:10101/speakers >/dev/null; do n=$((n+1)); if [ "$n" -ge 150 ]; then docker logs aivis-engine || true; exit 1; fi; sleep 2; done
  MAX_STYLES=4 OUT=aivis-model.json python scripts/discover_aivis_model.py
fi
mkdir -p conj-chunk-out staging
OVERALL=0
# Read chunk indexes on fd 3 so child commands in the loop cannot consume the
# remaining chunk list from stdin. This keeps 1-4 chunk runs truly resumable.
while IFS= read -r CHUNK <&3; do
  [ -n "$CHUNK" ] || continue
  echo "::group::chunk $CHUNK"

  # GitHub limits a release to 1000 assets. Keep smoke on its single release,
  # but shard v1 generation releases by 20 chunk indexes. Even with all 16
  # configured voices and both audio + status assets this stays <=640 assets.
  if echo "$INV" | grep -q "^smoke"; then
    TAG="$BASE_TAG"
  else
    printf -v BUCKET '%02d' "$((CHUNK / 20))"
    TAG="${BASE_TAG}-b${BUCKET}"
  fi
  export TAG
  if ! gh release view "$TAG" >/dev/null 2>&1; then
    gh release create "$TAG" --title "Conjugation generation chunks $TAG" --notes "Small resumable conjugation audio chunks. Not public runtime shards. Compact later into ~20 range-readable bundles." >/dev/null 2>&1 || gh release view "$TAG" >/dev/null
  fi

  ASSET=$(node scripts/conjugation_chunk_pipeline.js asset-name --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK")
  : > /tmp/release-assets.txt
  gh release view "$TAG" --json assets -q '.assets[].name' >> /tmp/release-assets.txt || true
  # Old v1 assets remain valid durable evidence and must still participate in
  # resume checks after release sharding.
  if [ "$TAG" != "$BASE_TAG" ]; then
    gh release view "$BASE_TAG" --json assets -q '.assets[].name' >> /tmp/release-assets.txt || true
  fi
  sort -u /tmp/release-assets.txt -o /tmp/release-assets.txt
  if node scripts/conjugation_chunk_pipeline.js skip-check --status word-conjugation-generation-status.json --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK" --release-assets /tmp/release-assets.txt; then
    echo "SKIP — ALREADY COMPLETE $ASSET"
    echo "::endgroup::"
    continue
  fi
  export CHUNK ASSET INVENTORY="$INV_FILE" OUT_DIR=conj-chunk-out CATALOG_OUT=conj-chunk-out/chunk-catalog.json SKIP_OUT=conj-chunk-out/skip.json ASSET_NAME="$ASSET"
  if echo "$INV" | grep -q "^smoke"; then
    unset LEGACY_CATALOG || true
    echo "smoke inventory: disable F3 v1 legacy reuse so clips are newly synthesized"
  elif [ "$PROVIDER" = supertonic3 ] && [ "$VOICE" = F3 ] && [ -f word-supertonic3-conj-catalog.json ]; then
    export LEGACY_CATALOG=word-supertonic3-conj-catalog.json
  else
    unset LEGACY_CATALOG || true
  fi
  if [ "$PROVIDER" = aivis ]; then export MODEL=aivis-model.json; fi
  rm -f conj-chunk-out/skip.json
  GEN_OK=0
  GEN_ERR="generation failed"
  for attempt in 1 2 3; do
    echo "synth attempt $attempt"
    if python -u scripts/generate_conjugation_chunk.py > /tmp/gen.out 2> /tmp/gen.err; then
      GEN_OK=1
      cat /tmp/gen.out
      break
    fi
    cat /tmp/gen.out /tmp/gen.err || true
    sleep $((attempt*8))
  done
  if [ -f conj-chunk-out/skip.json ]; then
    echo "generator skip $(cat conj-chunk-out/skip.json)"
    python - <<'PY'
import json,datetime,os
from pathlib import Path
plan=json.loads(Path('conj-chunk-out/chunk-plan.json').read_text()) if Path('conj-chunk-out/chunk-plan.json').is_file() else {}
rec={'status':'complete','reused':True,'expectedCount':plan.get('expected',0),'generatedCount':0,'reusedCount':len(plan.get('reused') or []),'validation':{'ok':True,'reason':'legacy reuse, no synth'},'persistedAsset':None,'sha256':None,'size':0,'githubAvailable':True,'hfAvailable':False,'githubRelease':os.environ['TAG'],'timestamp':datetime.datetime.utcnow().isoformat()+'Z','retry':0,'error':None}
Path('conj-chunk-out/record.json').write_text(json.dumps(rec))
PY
    node scripts/conjugation_chunk_pipeline.js update-status --status word-conjugation-generation-status.json --inventory "$INV_FILE" --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK" --record conj-chunk-out/record.json --out word-conjugation-generation-status.json
    FRAG="status-${PROVIDER}-${VOICE}-${INV}-chunk$(printf '%03d' "$CHUNK").json"
    cp conj-chunk-out/record.json "$FRAG"
    if retry gh release upload "$TAG" "$FRAG" --clobber; then
      echo "REUSE STATUS PASS $FRAG"
    else
      echo "reuse status publish failed"; OVERALL=1
    fi
    echo "::endgroup::"
    continue
  fi
  if [ "$GEN_OK" != 1 ]; then
    echo "generation failed after retries"; OVERALL=1
    python - <<'PY'
import json,datetime,os
from pathlib import Path

def read_tail(p, n=2000):
    path=Path(p)
    if not path.is_file():
        return ""
    return path.read_text(errors="replace")[-n:]

plan={}
if Path("conj-chunk-out/chunk-plan.json").is_file():
    try:
        plan=json.loads(Path("conj-chunk-out/chunk-plan.json").read_text(encoding="utf-8"))
    except Exception:
        plan={}
inv={}
inv_file=os.environ.get("INV_FILE","")
if inv_file and Path(inv_file).is_file():
    try:
        inv=json.loads(Path(inv_file).read_text(encoding="utf-8"))
    except Exception:
        inv={}
chunk=int(os.environ.get("CHUNK") or 0)
cs=int(inv.get("chunkSize") or 0)
rows=inv.get("readings") or []
fallback=len(rows[chunk*cs:chunk*cs+cs]) if cs else 0
expected=plan.get("expected", fallback)
blob="\n".join(x for x in [read_tail("/tmp/gen.out", 2000), read_tail("/tmp/gen.err", 2000)] if x).strip()[-2000:]
err=blob or "generation failed"
Path("conj-chunk-out").mkdir(parents=True, exist_ok=True)
Path("conj-chunk-out/record.json").write_text(json.dumps({
    "status":"failed",
    "expectedCount":expected,
    "generatedCount":0,
    "validation":{"ok":False},
    "persistedAsset":None,
    "githubAvailable":False,
    "retry":3,
    "error":err,
    "failedReadingIds":[],
    "timestamp":datetime.datetime.utcnow().isoformat()+"Z"
}, ensure_ascii=False))
print("recorded gen error expected", expected, "bytes", len(err), flush=True)
print(err[:400], flush=True)
PY
    node scripts/conjugation_chunk_pipeline.js update-status --status word-conjugation-generation-status.json --inventory "$INV_FILE" --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK" --record conj-chunk-out/record.json --failed --out word-conjugation-generation-status.json || true
    echo "::endgroup::"; continue
  fi
  VAL_OK=0
  for attempt in 1 2 3; do
    TAR="conj-chunk-out/$ASSET" CATALOG=conj-chunk-out/chunk-catalog.json OUT=conj-chunk-out/validation.json python scripts/validate_conjugation_chunk.py && VAL_OK=1 && break
    sleep $((attempt*5))
  done
  if [ "$VAL_OK" != 1 ]; then
    echo "validation failed; not marking complete"; OVERALL=1
    python - <<'PY'
import json,datetime
from pathlib import Path
v=json.loads(Path('conj-chunk-out/validation.json').read_text()) if Path('conj-chunk-out/validation.json').is_file() else {}
Path('conj-chunk-out/record.json').write_text(json.dumps({'status':'failed','validation':v,'persistedAsset':None,'githubAvailable':False,'retry':3,'error':'validation failed','failedReadingIds':v.get('failedReadingIds') or [],'timestamp':datetime.datetime.utcnow().isoformat()+'Z'}))
PY
    node scripts/conjugation_chunk_pipeline.js update-status --status word-conjugation-generation-status.json --inventory "$INV_FILE" --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK" --record conj-chunk-out/record.json --failed --out word-conjugation-generation-status.json || true
    echo "::endgroup::"; continue
  fi
  mkdir -p staging remote-check
  cp "conj-chunk-out/$ASSET" "staging/$ASSET"
  PUB_OK=0
  for attempt in 1 2 3; do
    if gh release upload "$TAG" "staging/$ASSET" --clobber; then
      rm -f "remote-check/$ASSET"
      if gh release download "$TAG" -p "$ASSET" -D remote-check; then
        LOCAL=$(sha256sum "staging/$ASSET" | awk '{print $1}')
        REMOTE=$(sha256sum "remote-check/$ASSET" | awk '{print $1}')
        if [ "$LOCAL" = "$REMOTE" ]; then PUB_OK=1; break; fi
        echo "remote sha mismatch $LOCAL $REMOTE"
      fi
    fi
    sleep $((attempt*8))
  done
  HF_OK=false
  if [ -n "${SAVED_HF_OIDC}" ]; then export HF_OIDC_RESOURCE="$SAVED_HF_OIDC"; fi
  if python -m pip show huggingface_hub >/dev/null 2>&1 || python -m pip install --quiet --disable-pip-version-check 'huggingface_hub>=1.19,<2'; then
    if hf upload "$HF_DATASET_REPO" "staging/$ASSET" "$HF_DIR/$ASSET" --repo-type dataset --commit-message "conj chunk $PROVIDER $VOICE $CHUNK"; then HF_OK=true; fi
  fi || true
  if [ "$PUB_OK" != 1 ]; then
    echo "publish/remote validation failed; not marking complete"; OVERALL=1
    echo "::endgroup::"; continue
  fi
  export HF_OK ASSET TAG
  python - <<'PY'
import json,os,datetime
from pathlib import Path
v=json.loads(Path('conj-chunk-out/validation.json').read_text())
cat=json.loads(Path('conj-chunk-out/chunk-catalog.json').read_text())
rec={'status':'complete','expectedCount':len(cat.get('items') or []),'generatedCount':len(cat.get('items') or []),'reusedCount':0,'validation':v,'persistedAsset':os.environ['ASSET'],'sha256':v.get('sha256'),'size':v.get('size'),'githubAvailable':True,'hfAvailable':os.environ.get('HF_OK','false')=='true','githubRelease':os.environ['TAG'],'timestamp':datetime.datetime.utcnow().isoformat()+'Z','retry':0,'error':None}
Path('conj-chunk-out/record.json').write_text(json.dumps(rec))
PY
  node scripts/conjugation_chunk_pipeline.js update-status --status word-conjugation-generation-status.json --inventory "$INV_FILE" --provider "$PROVIDER" --voice "$VOICE" --inventory_version "$INV" --chunk "$CHUNK" --record conj-chunk-out/record.json --out word-conjugation-generation-status.json
  FRAG="status-${PROVIDER}-${VOICE}-${INV}-chunk$(printf '%03d' "$CHUNK").json"
  cp conj-chunk-out/record.json "$FRAG"
  if ! retry gh release upload "$TAG" "$FRAG" --clobber; then
    echo "status fragment publish failed"; OVERALL=1
    echo "::endgroup::"
    continue
  fi
  echo "PUBLISH PASS $ASSET release=$TAG"
  echo "::endgroup::"
done 3< chunks.txt
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add word-conjugation-generation-status.json
if git diff --cached --quiet; then echo status unchanged; else
  git commit -m "Checkpoint conjugation chunk ${PROVIDER} ${VOICE}"
  n=0
  until git pull --rebase origin main && git push origin main; do
    n=$((n+1)); if [ "$n" -ge 5 ]; then echo 'status push failed'; break; fi; sleep $((n*3))
  done
fi
docker stop voicevox-engine aivis-engine 2>/dev/null || true
exit "$OVERALL"
