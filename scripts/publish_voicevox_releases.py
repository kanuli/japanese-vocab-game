#!/usr/bin/env python3
"""Publish a generated VOICEVOX pack as public GitHub Release assets.

The generated stable index is committed to the Pages repository. Each item gets a
permanent public GitHub Release download URL, so the Listening page needs no login.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

PACK_DIR = Path(os.environ.get("PACK_DIR", "voicevox-pack"))
PACK_INDEX = PACK_DIR / "voicevox-index.json"
INDEX_OUT = Path(os.environ.get("INDEX_OUT", "voicevox-release-index.json"))
REPO = os.environ.get("GITHUB_REPOSITORY", "kanuli/japanese-vocab-game")
NAMESPACE = os.environ.get("RELEASE_NAMESPACE", "voicevox-v1")
MAX_ASSETS = int(os.environ.get("RELEASE_MAX_ASSETS", "800"))
REPLACE_LEVELS = os.environ.get("REPLACE_LEVELS", "0").lower() in {"1", "true", "yes"}


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ensure_release(tag: str, level: str, chunk: int) -> None:
    found = run("gh", "release", "view", tag, "--repo", REPO, check=False)
    if found.returncode == 0:
        return
    title = f"VOICEVOX {level} audio {chunk:03d}"
    notes = (
        "Pre-generated VOICEVOX audio for the Japanese Listening Game. "
        "Each asset is referenced by voicevox-release-index.json."
    )
    run("gh", "release", "create", tag, "--repo", REPO, "--title", title, "--notes", notes)


def upload_batch(tag: str, paths: list[Path]) -> None:
    if not paths:
        return
    cmd = ["gh", "release", "upload", tag, "--repo", REPO, "--clobber", *map(str, paths)]
    run(*cmd)


def main() -> int:
    if not PACK_INDEX.is_file():
        raise SystemExit(f"Missing {PACK_INDEX}")
    pack = json.loads(PACK_INDEX.read_text(encoding="utf-8"))
    source_items = pack.get("items") or {}
    if not source_items:
        raise SystemExit("Generated pack has no items")

    stable = {"version": 2, "storage": "github-releases", "items": {}}
    if INDEX_OUT.is_file():
        try:
            old = json.loads(INDEX_OUT.read_text(encoding="utf-8"))
            if isinstance(old, dict) and isinstance(old.get("items"), dict):
                stable = old
        except Exception:
            pass
    stable["version"] = 2
    stable["storage"] = "github-releases"
    stable.setdefault("items", {})

    selected_levels = {str(rec.get("level", "")) for rec in source_items.values() if rec.get("level")}
    if REPLACE_LEVELS:
        stable["items"] = {
            qid: rec for qid, rec in stable["items"].items()
            if str(rec.get("level", "")) not in selected_levels
        }

    by_level: dict[str, list[tuple[str, dict]]] = {}
    for qid, rec in source_items.items():
        level = str(rec.get("level", "")).upper()
        if not level:
            raise SystemExit(f"Missing level for {qid}")
        by_level.setdefault(level, []).append((qid, rec))

    total_uploaded = 0
    releases_used: set[str] = set()
    for level in sorted(by_level):
        rows = by_level[level]
        for offset in range(0, len(rows), MAX_ASSETS):
            chunk_rows = rows[offset: offset + MAX_ASSETS]
            chunk = offset // MAX_ASSETS + 1
            tag = f"{NAMESPACE}-{level.lower()}-{chunk:03d}"
            ensure_release(tag, level, chunk)
            releases_used.add(tag)

            batch: list[Path] = []
            for qid, rec in chunk_rows:
                path = PACK_DIR / str(rec["path"])
                if not path.is_file():
                    raise SystemExit(f"Missing audio: {path}")
                batch.append(path)
                asset = path.name
                public_url = (
                    f"https://github.com/{REPO}/releases/download/{urllib.parse.quote(tag)}/"
                    f"{urllib.parse.quote(asset)}"
                )
                stable["items"][qid] = {
                    "url": public_url,
                    "speaker": rec.get("speaker", ""),
                    "style": rec.get("style", ""),
                    "styleId": rec.get("styleId"),
                    "credit": rec.get("credit", ""),
                    "text": rec.get("text", ""),
                    "grammar": rec.get("grammar", ""),
                    "level": level,
                    "release": tag,
                }
                if len(batch) >= 50:
                    upload_batch(tag, batch)
                    total_uploaded += len(batch)
                    print(f"Uploaded {total_uploaded} assets")
                    batch = []
            if batch:
                upload_batch(tag, batch)
                total_uploaded += len(batch)
                print(f"Uploaded {total_uploaded} assets")

    stable["releaseNamespace"] = NAMESPACE
    stable["indexed"] = len(stable["items"])
    stable["releases"] = sorted({rec.get("release") for rec in stable["items"].values() if rec.get("release")})
    stable["voiceVariantCount"] = pack.get("voiceVariantCount")
    stable["speakerCount"] = pack.get("speakerCount")
    INDEX_OUT.write_text(json.dumps(stable, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Published {total_uploaded} audio assets across {len(releases_used)} release(s)")
    print(f"Stable index: {INDEX_OUT} ({len(stable['items'])} questions)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, file=sys.stderr)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise SystemExit(exc.returncode or 1)
