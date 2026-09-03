#!/usr/bin/env python3
"""Generate one frozen-inventory chunk for one provider voice. Never rebuild inventory."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    inventory = Path(os.environ["INVENTORY"])
    provider = os.environ["PROVIDER"].strip()
    voice = os.environ["VOICE"].strip()
    chunk = int(os.environ["CHUNK"])
    out_dir = Path(os.environ.get("OUT_DIR", "conj-chunk-out"))
    catalog_out = Path(os.environ.get("CATALOG_OUT", str(out_dir / "chunk-catalog.json")))
    skip_path = Path(os.environ.get("SKIP_OUT", str(out_dir / "skip.json")))
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "node",
        str(ROOT / "scripts" / "conjugation_chunk_pipeline.js"),
        "slice",
        "--inventory",
        str(inventory),
        "--chunk",
        str(chunk),
        "--provider",
        provider,
        "--voice",
        voice,
        "--out",
        str(catalog_out),
        "--plan",
        str(out_dir / "chunk-plan.json"),
    ]
    if os.environ.get("LEGACY_CATALOG"):
        cmd += ["--legacy-catalog", os.environ["LEGACY_CATALOG"]]
    subprocess.check_call(cmd)
    plan = load_json(out_dir / "chunk-plan.json")
    if plan.get("allReused"):
        skip_path.write_text(
            json.dumps(
                {
                    "skip": True,
                    "reason": "ALREADY COMPLETE",
                    "reused": True,
                    "chunk": chunk,
                    "expected": plan.get("expected"),
                    "reusedCount": len(plan.get("reused") or []),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print("all readings reused; skip synth", flush=True)
        return 0
    if not (plan.get("toGenerate") or []):
        skip_path.write_text(
            json.dumps({"skip": True, "reason": "EMPTY CHUNK", "chunk": chunk}, indent=2) + "\n",
            encoding="utf-8",
        )
        print("empty generate set", flush=True)
        return 0

    env = os.environ.copy()
    env["CATALOG"] = str(catalog_out)
    env["SHARD"] = "0"
    if provider == "supertonic3":
        env["VOICE"] = voice
        env["OUT_DIR"] = str(out_dir)
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "generate_word_supertonic_shard.py")], env=env)
        src = out_dir / f"{voice}-shard0.tar"
        srcj = out_dir / f"{voice}-shard0.json"
    elif provider == "voicevox":
        env["OUTPUT_DIR"] = str(out_dir)
        env["SPEAKER_KEY"] = voice
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "generate_word_voicevox_shard.py")], env=env)
        src = out_dir / f"{voice}-shard0.tar"
        srcj = out_dir / f"{voice}-shard0.json"
    elif provider == "aivis":
        model_path = Path(os.environ["MODEL"])
        model = load_json(model_path)
        styles = [s for s in model.get("styles") or [] if s.get("key") == voice]
        if not styles:
            raise SystemExit(f"Aivis style {voice} not in model")
        one = dict(model)
        one["styles"] = styles
        filtered = out_dir / "aivis-model-one.json"
        filtered.write_text(json.dumps(one, ensure_ascii=False), encoding="utf-8")
        env["MODEL"] = str(filtered)
        env["OUT_DIR"] = str(out_dir)
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "generate_word_aivis_shard.py")], env=env)
        src = out_dir / f"{voice}-shard0.tar"
        srcj = out_dir / f"{voice}-shard0.json"
    else:
        raise SystemExit("unknown provider " + provider)

    asset = os.environ.get("ASSET_NAME")
    if not asset:
        raise SystemExit("ASSET_NAME required")
    dest = out_dir / asset
    destj = out_dir / (Path(asset).stem + ".json")
    if not src.is_file():
        raise SystemExit(f"generator did not write {src}")
    src.replace(dest)
    if srcj.is_file():
        manifest = load_json(srcj)
        manifest["asset"] = asset
        manifest["chunk"] = chunk
        manifest["provider"] = provider
        destj.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        srcj.unlink(missing_ok=True)
    print("generated", dest, dest.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
