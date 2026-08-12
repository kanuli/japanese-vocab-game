#!/usr/bin/env python3
"""Download VOICEVOX GitHub Release assets and prepare a Hugging Face mirror.

This lets an already-generated GitHub Releases library be mirrored without running
VOICEVOX synthesis again. It also upgrades older single-origin index records to
GitHub-primary + Hugging-Face-fallback records.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

INDEX_PATH = Path(os.environ.get("VOICEVOX_PUBLIC_INDEX", "voicevox-release-index.json"))
OUT_DIR = Path(os.environ.get("HF_MIRROR_DIR", "hf-mirror"))
HF_REPO = os.environ.get(
    "HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup"
).strip()
WORKERS = max(1, min(12, int(os.environ.get("MIRROR_WORKERS", "8"))))


def quote_path(path: str) -> str:
    return "/".join(urllib.parse.quote(p, safe="") for p in path.split("/") if p)


def hf_url(path: str) -> str:
    return f"https://huggingface.co/datasets/{HF_REPO}/resolve/main/{quote_path(path)}"


def primary_url(rec: dict) -> str:
    urls = rec.get("urls") if isinstance(rec.get("urls"), list) else []
    for url in [*urls, rec.get("url", "")]:
        if isinstance(url, str) and "github.com/" in url and "/releases/download/" in url:
            return url
    return str(rec.get("url", "")).strip()


def target_path(qid: str, rec: dict) -> str:
    existing = str(rec.get("path", "")).strip()
    if existing:
        return existing
    level = str(rec.get("level", "")).upper().strip()
    if not level:
        raise ValueError(f"Missing JLPT level for {qid}")
    return f"voicevox/{level}/{qid}.mp3"


def download_one(job: tuple[str, str]) -> tuple[str, int]:
    url, rel = job
    dest = OUT_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size >= 500:
        return rel, dest.stat().st_size
    last = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "japanese-listening-voicevox-backup/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r, dest.open("wb") as f:
                shutil.copyfileobj(r, f, length=1024 * 1024)
            size = dest.stat().st_size
            if size < 500:
                raise RuntimeError(f"Downloaded file too small: {rel} ({size} bytes)")
            return rel, size
        except Exception as exc:  # noqa: BLE001
            last = exc
            dest.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Failed to download {rel}: {last}")


def main() -> int:
    if not INDEX_PATH.is_file():
        raise SystemExit(f"Missing {INDEX_PATH}")
    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    items = data.get("items") or {}
    if not items:
        raise SystemExit("VOICEVOX public index is empty; finish GitHub Release publishing first")

    jobs: list[tuple[str, str]] = []
    for qid, rec in items.items():
        url = primary_url(rec)
        if not url:
            raise SystemExit(f"Missing GitHub Release URL for {qid}")
        rel = target_path(qid, rec)
        backup = hf_url(rel)
        rec["path"] = rel
        rec["url"] = url
        rec["urls"] = [url, backup]
        rec["backupUrl"] = backup
        jobs.append((url, rel))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    completed = 0
    total_bytes = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(download_one, job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            rel, size = future.result()
            completed += 1
            total_bytes += size
            if completed % 50 == 0 or completed == len(futures):
                print(f"Downloaded {completed}/{len(futures)} assets ({total_bytes / 1024 / 1024:.1f} MiB)")

    data["version"] = 2
    data["storage"] = "github-releases+hf-backup"
    data["primaryStorage"] = "github-releases"
    data["backupStorage"] = "huggingface-dataset"
    data["huggingFaceDataset"] = HF_REPO
    data["indexed"] = len(items)
    INDEX_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "voicevox-release-index.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Prepared Hugging Face mirror: {len(items)} audio files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
