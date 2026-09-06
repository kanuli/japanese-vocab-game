#!/usr/bin/env python3
"""Publish frozen conjugation v1 audio to compact range-readable runtime bundles.

This script NEVER synthesizes audio. It only downloads already-published generation
chunk tar files, compacts them into ~20 deterministic public runtime bundles per
voice, builds byte-range indexes, and verifies the uploaded GitHub Release assets.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

EXPECTED_FREEZE = "dce92b8dae91165f4e2fe7c9fee62489d24230242588d46eab7472889fcbbfc0"
EXPECTED_COUNT = 84557
EXPECTED_CHUNKS = 212
EXPECTED_CHUNK_SIZE = 400
EXPECTED_PUBLIC_BUNDLES = 20
SOURCE_TAG = "word-conj-chunks-v1"
ST_TAG = "word-supertonic3-conj-v2"
VV_TAG = "word-voicevox-conj-v1"
ST_VOICES = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "M5"]
VV_VOICES = ["s01", "s02"]
VV_META = {
    "s01": {"speaker": "四国めたん", "style": "ノーマル", "styleId": 2, "credit": "VOICEVOX:四国めたん"},
    "s02": {"speaker": "ずんだもん", "style": "ノーマル", "styleId": 3, "credit": "VOICEVOX:ずんだもん"},
}


def die(msg: str) -> None:
    raise SystemExit(msg)


def sh(cmd: list[str], *, capture: bool = False, retries: int = 1) -> str:
    last = None
    for attempt in range(1, retries + 1):
        try:
            cp = subprocess.run(cmd, check=True, text=True,
                                stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.PIPE if capture else None)
            return cp.stdout if capture else ""
        except subprocess.CalledProcessError as exc:
            last = exc
            if attempt < retries:
                print(f"retry {attempt}/{retries}: {' '.join(cmd[:4])}", file=sys.stderr)
                time.sleep(min(2 * attempt, 6))
    if capture and last is not None:
        sys.stderr.write(last.stdout or "")
        sys.stderr.write(last.stderr or "")
    raise last  # type: ignore[misc]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_inventory(path: Path) -> dict:
    inv = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "uniqueReadingCount": EXPECTED_COUNT,
        "chunkCount": EXPECTED_CHUNKS,
        "chunkSize": EXPECTED_CHUNK_SIZE,
        "publicBundleCount": EXPECTED_PUBLIC_BUNDLES,
    }
    for key, expected in checks.items():
        if inv.get(key) != expected:
            die(f"inventory mismatch {key}: {inv.get(key)!r} != {expected!r}")
    rows = inv.get("readings")
    if not isinstance(rows, list) or len(rows) != EXPECTED_COUNT:
        die("inventory readings malformed")
    ids = set()
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) < 3:
            die(f"inventory row {i} malformed")
        rid = str(row[0])
        if rid in ids:
            die(f"duplicate reading id {rid}")
        ids.add(rid)
    return inv


def provider_spec(provider: str, voice: str) -> dict:
    if provider == "supertonic3":
        if voice not in ST_VOICES:
            die(f"invalid SuperTonic voice {voice}")
        return {
            "ext": ".mp3",
            "source_asset": lambda c: f"supertonic3-{voice}-invv1-chunk{c:03d}.tar",
            "runtime_tag": ST_TAG,
            "bundle_asset": lambda b: f"word-supertonic3-conj-v2-{voice}-v1-bundle{b:02d}.tar",
            "index_name": f"word-supertonic3-conj-v2-{voice}-index.json",
        }
    if provider == "voicevox":
        if voice not in VV_VOICES:
            die(f"invalid VOICEVOX voice {voice}")
        return {
            "ext": ".wav",
            "source_asset": lambda c: f"voicevox-{voice}-invv1-chunk{c:03d}.tar",
            "runtime_tag": VV_TAG,
            "bundle_asset": lambda b: f"word-voicevox-conj-{voice}-v1-bundle{b:02d}.tar",
            "index_name": f"word-voicevox-conj-{voice}-index.json",
        }
    die(f"unsupported provider {provider}")


def release_url(repo: str, tag: str, asset: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{asset}"


def download_source(repo: str, asset: str, dest_dir: Path) -> Path:
    dest = dest_dir / asset
    if dest.exists():
        dest.unlink()
    sh(["gh", "release", "download", SOURCE_TAG, "--repo", repo,
        "--pattern", asset, "--dir", str(dest_dir), "--clobber"], retries=4)
    if not dest.is_file() or dest.stat().st_size <= 1024:
        die(f"downloaded source asset invalid: {asset}")
    return dest


def normalized_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.size = size
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o644
    return info


def verify_release_assets(repo: str, tag: str, expected: dict[str, int]) -> None:
    raw = sh(["gh", "release", "view", tag, "--repo", repo, "--json", "assets"], capture=True, retries=3)
    data = json.loads(raw)
    remote = {str(a.get("name")): int(a.get("size") or 0) for a in data.get("assets", [])}
    missing = []
    bad = []
    for name, size in expected.items():
        if name not in remote:
            missing.append(name)
        elif remote[name] != size:
            bad.append((name, size, remote[name]))
    if missing or bad:
        die(f"remote asset verification failed missing={missing[:3]} bad={bad[:3]}")


def fetch_range(url: str, start: int, length: int) -> bytes:
    end = start + length - 1
    last = None
    for attempt in range(1, 6):
        req = urllib.request.Request(url, headers={
            "Range": f"bytes={start}-{end}",
            "User-Agent": "japanese-vocab-game-runtime-publisher/1",
            "Accept": "*/*",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status = getattr(resp, "status", None) or resp.getcode()
                body = resp.read()
                if status != 206:
                    raise RuntimeError(f"range status {status}, expected 206")
                if len(body) != length:
                    raise RuntimeError(f"range length {len(body)} != {length}")
                return body
        except Exception as exc:
            last = exc
            if attempt < 5:
                time.sleep(2 * attempt)
    raise RuntimeError(f"range fetch failed {url}: {last}")


def publish_voice(args: argparse.Namespace) -> None:
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        die("--repo or GITHUB_REPOSITORY required")
    inv = load_inventory(Path(args.inventory))
    rows = inv["readings"]
    public_size = int(inv["publicBundleSize"])
    bundle_count = int(inv["publicBundleCount"])
    spec = provider_spec(args.provider, args.voice)
    ext = spec["ext"]

    expected_ids = [str(r[0]) for r in rows]
    expected_set = set(expected_ids)
    ordinal = {rid: i for i, rid in enumerate(expected_ids)}
    seen: set[str] = set()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    work_root = Path(tempfile.mkdtemp(prefix=f"publish-{args.provider}-{args.voice}-"))
    source_dir = work_root / "source"
    bundle_dir = work_root / "bundles"
    source_dir.mkdir()
    bundle_dir.mkdir()

    bundle_paths = [bundle_dir / spec["bundle_asset"](b) for b in range(bundle_count)]
    writers = [tarfile.open(p, "w") for p in bundle_paths]
    try:
        for chunk in range(EXPECTED_CHUNKS):
            asset = spec["source_asset"](chunk)
            src_path = download_source(repo, asset, source_dir)
            lo = chunk * EXPECTED_CHUNK_SIZE
            hi = min(lo + EXPECTED_CHUNK_SIZE, EXPECTED_COUNT)
            chunk_expected = set(expected_ids[lo:hi])
            chunk_seen: set[str] = set()
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    base = Path(member.name).name
                    if not base.endswith(ext):
                        continue
                    rid = base[: -len(ext)]
                    if rid not in expected_set:
                        die(f"unexpected reading id in {asset}: {rid}")
                    if rid in chunk_seen or rid in seen:
                        die(f"duplicate reading id in source assets: {rid}")
                    f = tf.extractfile(member)
                    if f is None:
                        die(f"cannot read {member.name} from {asset}")
                    data = f.read()
                    if not data:
                        die(f"zero-byte audio {member.name} in {asset}")
                    b = ordinal[rid] // public_size
                    if b >= bundle_count:
                        die(f"public bundle overflow for {rid}: {b}")
                    writers[b].addfile(normalized_info(f"{rid}{ext}", len(data)), io.BytesIO(data))
                    chunk_seen.add(rid)
                    seen.add(rid)
            src_path.unlink(missing_ok=True)
            if chunk_seen != chunk_expected:
                missing = sorted(chunk_expected - chunk_seen)
                extra = sorted(chunk_seen - chunk_expected)
                die(f"source chunk {chunk:03d} coverage mismatch missing={missing[:3]} extra={extra[:3]}")
            if chunk % 20 == 0 or chunk == EXPECTED_CHUNKS - 1:
                print(f"{args.provider}/{args.voice}: compacted chunk {chunk:03d}/{EXPECTED_CHUNKS-1:03d}")
    finally:
        for tf in writers:
            tf.close()

    if seen != expected_set:
        die(f"voice coverage mismatch seen={len(seen)} expected={len(expected_set)}")

    bundles: dict[str, dict] = {}
    indexed: set[str] = set()
    local_samples: list[tuple[str, int, int, bytes]] = []
    for b, path in enumerate(bundle_paths):
        if not path.is_file() or path.stat().st_size <= 1024:
            die(f"runtime bundle invalid {path.name}")
        members: dict[str, list[int]] = {}
        with tarfile.open(path, "r:") as tf:
            files = [m for m in tf.getmembers() if m.isfile() and Path(m.name).name.endswith(ext)]
            for idx, m in enumerate(files):
                rid = Path(m.name).name[: -len(ext)]
                if rid in indexed:
                    die(f"duplicate runtime index member {rid}")
                expected_bundle = ordinal.get(rid, -1) // public_size
                if expected_bundle != b:
                    die(f"runtime bundle partition mismatch {rid}: {b} != {expected_bundle}")
                members[rid] = [int(m.offset_data), int(m.size)]
                indexed.add(rid)
                if idx == 0 or idx == len(files) - 1:
                    with path.open("rb") as bf:
                        bf.seek(m.offset_data)
                        sample = bf.read(m.size)
                    local_samples.append((str(b), int(m.offset_data), int(m.size), sample))
        name = path.name
        url = release_url(repo, spec["runtime_tag"], name)
        bundles[str(b)] = {
            "githubUrl": url,
            "hfUrl": "",
            "url": url,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "members": members,
        }

    if indexed != expected_set:
        die(f"runtime index coverage mismatch indexed={len(indexed)} expected={len(expected_set)}")

    for b, path in enumerate(bundle_paths):
        sh(["gh", "release", "upload", spec["runtime_tag"], str(path),
            "--repo", repo, "--clobber"], retries=4)
        print(f"{args.provider}/{args.voice}: uploaded bundle {b:02d}/{bundle_count-1:02d}")

    verify_release_assets(repo, spec["runtime_tag"], {p.name: p.stat().st_size for p in bundle_paths})

    checks = []
    for bundle_id, start, length, local in local_samples[:2] + local_samples[-2:]:
        url = bundles[bundle_id]["githubUrl"]
        remote = fetch_range(url, start, length)
        if hashlib.sha256(remote).digest() != hashlib.sha256(local).digest():
            die(f"range payload hash mismatch bundle {bundle_id}")
        checks.append({"bundle": bundle_id, "offset": start, "length": length, "sha256": hashlib.sha256(remote).hexdigest()})

    index = {
        "version": 1,
        "schemaVersion": 1,
        "voice": args.voice,
        "provider": args.provider,
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "wordCount": EXPECTED_COUNT,
        "shardCount": bundle_count,
        "bundleCount": bundle_count,
        "tarRangeEncoding": "raw-member",
        "bundles": bundles,
    }
    index_path = out_dir / spec["index_name"]
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    report = {
        "status": "PASS",
        "provider": args.provider,
        "voice": args.voice,
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "uniqueReadingCount": EXPECTED_COUNT,
        "sourceChunkCount": EXPECTED_CHUNKS,
        "publicBundleCount": bundle_count,
        "runtimeReleaseTag": spec["runtime_tag"],
        "runtimeIndex": spec["index_name"],
        "rangeChecks": checks,
        "ttsSynthesisInvoked": False,
    }
    (out_dir / f"runtime-publish-{args.provider}-{args.voice}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    shutil.rmtree(work_root, ignore_errors=True)


def index_local_url(name: str, freeze: str) -> str:
    return f"./{name}?v={freeze[:12]}"


def raw_index_url(repo: str, name: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/main/{name}"


def build_catalogs(args: argparse.Namespace) -> None:
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        die("--repo or GITHUB_REPOSITORY required")
    inv = load_inventory(Path(args.inventory))
    rows = inv["readings"]
    public_size = int(inv["publicBundleSize"])
    artifact_dir = Path(args.artifact_dir)
    out_root = Path(args.out_root)

    expected_indexes = []
    for provider, voices in (("supertonic3", ST_VOICES), ("voicevox", VV_VOICES)):
        for voice in voices:
            spec = provider_spec(provider, voice)
            p = artifact_dir / spec["index_name"]
            if not p.is_file():
                die(f"missing generated index artifact {p}")
            idx = json.loads(p.read_text(encoding="utf-8"))
            if idx.get("freezeHash") != EXPECTED_FREEZE or idx.get("wordCount") != EXPECTED_COUNT:
                die(f"invalid generated index {p.name}")
            if len(idx.get("bundles", {})) != EXPECTED_PUBLIC_BUNDLES:
                die(f"bundle count mismatch {p.name}")
            member_ids = set()
            for bundle in idx["bundles"].values():
                member_ids.update((bundle.get("members") or {}).keys())
            if len(member_ids) != EXPECTED_COUNT:
                die(f"member coverage mismatch {p.name}: {len(member_ids)}")
            shutil.copy2(p, out_root / p.name)
            expected_indexes.append(p.name)

    words = {}
    for ordinal, row in enumerate(rows):
        rid, reading, written = str(row[0]), str(row[1]), str(row[2])
        key = f"{reading}|{written or reading}"
        if key not in words:
            words[key] = [rid, ordinal // public_size]
    if len(words) != EXPECTED_COUNT:
        die(f"catalog words not one-to-one with frozen readings: {len(words)} != {EXPECTED_COUNT}")

    st_voices = {}
    for voice in ST_VOICES:
        name = provider_spec("supertonic3", voice)["index_name"]
        st_voices[voice] = {
            "label": voice,
            "delivery": "range-index",
            "indexUrl": index_local_url(name, EXPECTED_FREEZE),
            "indexGithubUrl": raw_index_url(repo, name),
        }
    st_catalog = {
        "version": 1,
        "status": "ready",
        "engine": "supertonic-3-conj-v2",
        "storage": "github-releases-range-bundles",
        "wordCount": EXPECTED_COUNT,
        "uniqueReadingCount": EXPECTED_COUNT,
        "voiceCount": len(ST_VOICES),
        "bundleCountPerVoice": EXPECTED_PUBLIC_BUNDLES,
        "voices": st_voices,
        "words": words,
        "releaseTag": ST_TAG,
        "coverageComplete": True,
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "tarRangeEncoding": "raw-member",
        "coverageNote": "Frozen conjugation inventory v1 fully published for F1-F5/M1-M5.",
    }

    vv_speakers = {}
    for voice in VV_VOICES:
        name = provider_spec("voicevox", voice)["index_name"]
        vv_speakers[voice] = {
            **VV_META[voice],
            "delivery": "range-index",
            "indexUrl": index_local_url(name, EXPECTED_FREEZE),
            "indexGithubUrl": raw_index_url(repo, name),
        }
    vv_catalog = {
        "version": 1,
        "status": "ready",
        "engine": "voicevox-conj-v1",
        "storage": "github-releases-range-bundles",
        "wordCount": EXPECTED_COUNT,
        "uniqueReadingCount": EXPECTED_COUNT,
        "speakerCount": len(VV_VOICES),
        "bundleCountPerVoice": EXPECTED_PUBLIC_BUNDLES,
        "speakers": vv_speakers,
        "words": words,
        "releaseTag": VV_TAG,
        "coverageComplete": True,
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "tarRangeEncoding": "raw-member",
        "coverageNote": "Frozen conjugation inventory v1 fully published for s01/s02.",
    }

    (out_root / "word-supertonic3-conj-v2-catalog.json").write_text(
        json.dumps(st_catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out_root / "word-voicevox-conj-catalog.json").write_text(
        json.dumps(vv_catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    report = {
        "status": "PASS",
        "inventoryVersion": "v1",
        "freezeHash": EXPECTED_FREEZE,
        "uniqueReadingCount": EXPECTED_COUNT,
        "supertonicVoices": len(ST_VOICES),
        "voicevoxVoices": len(VV_VOICES),
        "runtimeIndexes": expected_indexes,
        "publicBundlesPerVoice": EXPECTED_PUBLIC_BUNDLES,
        "ttsSynthesisInvoked": False,
    }
    (out_root / "word-conjugation-runtime-publication-v1.report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("publish-voice")
    p.add_argument("--provider", choices=["supertonic3", "voicevox"], required=True)
    p.add_argument("--voice", required=True)
    p.add_argument("--repo", default="")
    p.add_argument("--inventory", default="word-conjugation-reading-inventory-v1.json")
    p.add_argument("--out", required=True)
    p.set_defaults(func=publish_voice)

    b = sub.add_parser("build-catalogs")
    b.add_argument("--repo", default="")
    b.add_argument("--inventory", default="word-conjugation-reading-inventory-v1.json")
    b.add_argument("--artifact-dir", required=True)
    b.add_argument("--out-root", default=".")
    b.set_defaults(func=build_catalogs)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
