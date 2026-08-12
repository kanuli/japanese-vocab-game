#!/usr/bin/env python3
"""Build the public VOICEVOX multi-origin index from a generated pack.

This does not upload anything. It is used by recovery/mirror workflows so a
complete Hugging Face fallback index can be published even when GitHub Release
asset uploads are temporarily rate-limited.
"""
from __future__ import annotations

import json
import os
import urllib.parse
from pathlib import Path

PACK_DIR = Path(os.environ.get("PACK_DIR", "voicevox-pack"))
PACK_INDEX = PACK_DIR / "voicevox-index.json"
INDEX_OUT = Path(os.environ.get("INDEX_OUT", "voicevox-release-index.json"))
REPO = os.environ.get("GITHUB_REPOSITORY", "kanuli/japanese-vocab-game")
NAMESPACE = os.environ.get("RELEASE_NAMESPACE", "voicevox-v1")
MAX_ASSETS = int(os.environ.get("RELEASE_MAX_ASSETS", "800"))
HF_DATASET_REPO = os.environ.get(
    "HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup"
).strip()


def quote_path(path: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in str(path).split("/") if part)


def hf_public_url(relative_path: str) -> str:
    if not HF_DATASET_REPO:
        return ""
    return (
        f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/"
        f"{quote_path(relative_path)}"
    )


def main() -> int:
    if not PACK_INDEX.is_file():
        raise SystemExit(f"Missing {PACK_INDEX}")
    pack = json.loads(PACK_INDEX.read_text(encoding="utf-8"))
    source_items = pack.get("items") or {}
    if not source_items:
        raise SystemExit("Generated pack has no items")
    if MAX_ASSETS < 1 or MAX_ASSETS > 950:
        raise SystemExit("RELEASE_MAX_ASSETS must be between 1 and 950")

    by_level: dict[str, list[tuple[str, dict]]] = {}
    for qid, rec in source_items.items():
        level = str(rec.get("level", "")).upper()
        if not level:
            raise SystemExit(f"Missing level for {qid}")
        path = PACK_DIR / str(rec.get("path", ""))
        if not path.is_file():
            raise SystemExit(f"Missing audio: {path}")
        by_level.setdefault(level, []).append((qid, rec))

    items: dict[str, dict] = {}
    releases: set[str] = set()
    for level in sorted(by_level):
        rows = by_level[level]
        for offset in range(0, len(rows), MAX_ASSETS):
            chunk_rows = rows[offset : offset + MAX_ASSETS]
            chunk = offset // MAX_ASSETS + 1
            tag = f"{NAMESPACE}-{level.lower()}-{chunk:03d}"
            releases.add(tag)
            for qid, rec in chunk_rows:
                relative_path = str(rec["path"])
                asset = Path(relative_path).name
                primary = (
                    f"https://github.com/{REPO}/releases/download/{urllib.parse.quote(tag)}/"
                    f"{urllib.parse.quote(asset)}"
                )
                backup = hf_public_url(relative_path)
                urls = [primary] + ([backup] if backup else [])
                items[qid] = {
                    "url": primary,
                    "urls": urls,
                    "backupUrl": backup,
                    "path": relative_path,
                    "speaker": rec.get("speaker", ""),
                    "style": rec.get("style", ""),
                    "styleId": rec.get("styleId"),
                    "credit": rec.get("credit", ""),
                    "text": rec.get("text", ""),
                    "grammar": rec.get("grammar", ""),
                    "level": level,
                    "release": tag,
                    "asset": asset,
                }

    stable = {
        "version": 2,
        "storage": "github-releases+hf-backup",
        "primaryStorage": "github-releases",
        "backupStorage": "huggingface-dataset" if HF_DATASET_REPO else "",
        "huggingFaceDataset": HF_DATASET_REPO,
        "releaseNamespace": NAMESPACE,
        "indexed": len(items),
        "releases": sorted(releases),
        "voiceVariantCount": pack.get("voiceVariantCount"),
        "speakerCount": pack.get("speakerCount"),
        "recoveryIndex": True,
        "items": items,
    }
    INDEX_OUT.write_text(json.dumps(stable, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Built multi-origin index for {len(items)} questions across {len(releases)} release tags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
