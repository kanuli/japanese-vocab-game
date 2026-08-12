#!/usr/bin/env python3
"""Publish a generated VOICEVOX pack as public GitHub Release assets.

Designed for large packs and resumable GitHub Actions runs:
- shards each JLPT level across Releases
- uploads in small batches
- retries transient upload/API failures
- reuses already-uploaded assets when name and size match
- replaces mismatched assets with --clobber
- verifies every Release chunk before writing the public index

GitHub Releases is the primary public audio source. Each index item can also
carry a Hugging Face Dataset fallback URL using the same generated path.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

PACK_DIR = Path(os.environ.get("PACK_DIR", "voicevox-pack"))
PACK_INDEX = PACK_DIR / "voicevox-index.json"
INDEX_OUT = Path(os.environ.get("INDEX_OUT", "voicevox-release-index.json"))
REPO = os.environ.get("GITHUB_REPOSITORY", "kanuli/japanese-vocab-game")
NAMESPACE = os.environ.get("RELEASE_NAMESPACE", "voicevox-v1")
MAX_ASSETS = int(os.environ.get("RELEASE_MAX_ASSETS", "800"))
UPLOAD_BATCH = max(1, int(os.environ.get("RELEASE_UPLOAD_BATCH", "10")))
UPLOAD_RETRIES = max(1, int(os.environ.get("RELEASE_UPLOAD_RETRIES", "6")))
RETRY_BASE_SECONDS = max(1, int(os.environ.get("RELEASE_RETRY_BASE_SECONDS", "3")))
REPLACE_LEVELS = os.environ.get("REPLACE_LEVELS", "0").lower() in {"1", "true", "yes"}
HF_DATASET_REPO = os.environ.get(
    "HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup"
).strip()


def run(
    *args: str,
    check: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def run_retry(*args: str, attempts: int = UPLOAD_RETRIES, timeout: int = 300) -> subprocess.CompletedProcess:
    last: subprocess.CalledProcessError | subprocess.TimeoutExpired | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = run(*args, timeout=timeout)
            if attempt > 1:
                print(f"Recovered on retry {attempt}/{attempts}: {' '.join(args[:4])}")
            return result
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last = exc
            if isinstance(exc, subprocess.CalledProcessError):
                detail = (exc.stderr or exc.stdout or "").strip()
            else:
                detail = f"timed out after {timeout}s"
            print(
                f"Command failed ({attempt}/{attempts}): {' '.join(args)}"
                + (f"\n{detail}" if detail else ""),
                file=sys.stderr,
            )
            if attempt < attempts:
                delay = min(RETRY_BASE_SECONDS * (2 ** (attempt - 1)), 45)
                print(f"Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
    if last is None:
        raise RuntimeError("run_retry failed without an exception")
    raise last


def quote_path(path: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in str(path).split("/") if part)


def hf_public_url(relative_path: str) -> str:
    if not HF_DATASET_REPO:
        return ""
    return (
        f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/"
        f"{quote_path(relative_path)}"
    )


def release_assets(tag: str) -> dict[str, int]:
    result = run_retry(
        "gh",
        "release",
        "view",
        tag,
        "--repo",
        REPO,
        "--json",
        "assets",
        attempts=3,
        timeout=120,
    )
    payload = json.loads(result.stdout or "{}")
    assets = payload.get("assets") or []
    return {
        str(asset.get("name", "")): int(asset.get("size") or 0)
        for asset in assets
        if asset.get("name")
    }


def ensure_release(tag: str, level: str, chunk: int) -> None:
    found = run("gh", "release", "view", tag, "--repo", REPO, check=False, timeout=120)
    if found.returncode == 0:
        return
    title = f"VOICEVOX {level} audio {chunk:03d}"
    notes = (
        "Pre-generated VOICEVOX audio for the Japanese Listening Game. "
        "Each asset is referenced by voicevox-release-index.json."
    )
    run_retry(
        "gh",
        "release",
        "create",
        tag,
        "--repo",
        REPO,
        "--title",
        title,
        "--notes",
        notes,
        attempts=5,
        timeout=180,
    )


def upload_batch(tag: str, paths: list[Path], known_assets: dict[str, int]) -> tuple[int, int]:
    """Upload a small batch. Return (uploaded_or_replaced, reused)."""
    if not paths:
        return 0, 0

    reused = 0
    to_upload: list[Path] = []
    for path in paths:
        remote_size = known_assets.get(path.name)
        local_size = path.stat().st_size
        if remote_size == local_size and remote_size > 0:
            reused += 1
            continue
        to_upload.append(path)

    if not to_upload:
        return 0, reused

    cmd = [
        "gh",
        "release",
        "upload",
        tag,
        "--repo",
        REPO,
        "--clobber",
        *map(str, to_upload),
    ]
    run_retry(*cmd, attempts=UPLOAD_RETRIES, timeout=600)

    refreshed = release_assets(tag)
    for path in to_upload:
        expected = path.stat().st_size
        actual = refreshed.get(path.name)
        if actual != expected:
            raise RuntimeError(
                f"Release verification failed for {tag}/{path.name}: "
                f"expected {expected} bytes, found {actual!r}"
            )
    known_assets.clear()
    known_assets.update(refreshed)
    return len(to_upload), reused


def write_checkpoint(stable: dict) -> None:
    stable["indexed"] = len(stable.get("items") or {})
    INDEX_OUT.write_text(json.dumps(stable, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    if not PACK_INDEX.is_file():
        raise SystemExit(f"Missing {PACK_INDEX}")
    pack = json.loads(PACK_INDEX.read_text(encoding="utf-8"))
    source_items = pack.get("items") or {}
    if not source_items:
        raise SystemExit("Generated pack has no items")
    if MAX_ASSETS < 1 or MAX_ASSETS > 950:
        raise SystemExit("RELEASE_MAX_ASSETS must be between 1 and 950")

    stable = {"version": 2, "storage": "github-releases+hf-backup", "items": {}}
    if INDEX_OUT.is_file():
        try:
            old = json.loads(INDEX_OUT.read_text(encoding="utf-8"))
            if isinstance(old, dict) and isinstance(old.get("items"), dict):
                stable = old
        except Exception:
            pass

    stable["version"] = 2
    stable["storage"] = "github-releases+hf-backup"
    stable["primaryStorage"] = "github-releases"
    stable["backupStorage"] = "huggingface-dataset" if HF_DATASET_REPO else ""
    stable["huggingFaceDataset"] = HF_DATASET_REPO
    stable.setdefault("items", {})

    selected_levels = {
        str(rec.get("level", "")).upper()
        for rec in source_items.values()
        if rec.get("level")
    }
    if REPLACE_LEVELS:
        stable["items"] = {
            qid: rec
            for qid, rec in stable["items"].items()
            if str(rec.get("level", "")).upper() not in selected_levels
        }

    by_level: dict[str, list[tuple[str, dict]]] = {}
    for qid, rec in source_items.items():
        level = str(rec.get("level", "")).upper()
        if not level:
            raise SystemExit(f"Missing level for {qid}")
        by_level.setdefault(level, []).append((qid, rec))

    total_uploaded = 0
    total_reused = 0
    releases_used: set[str] = set()

    for level in sorted(by_level):
        rows = by_level[level]
        for offset in range(0, len(rows), MAX_ASSETS):
            chunk_rows = rows[offset : offset + MAX_ASSETS]
            chunk = offset // MAX_ASSETS + 1
            tag = f"{NAMESPACE}-{level.lower()}-{chunk:03d}"
            ensure_release(tag, level, chunk)
            releases_used.add(tag)

            known_assets = release_assets(tag)
            expected_assets: dict[str, int] = {}
            pending: list[Path] = []

            for qid, rec in chunk_rows:
                relative_path = str(rec["path"])
                path = PACK_DIR / relative_path
                if not path.is_file():
                    raise SystemExit(f"Missing audio: {path}")

                expected_assets[path.name] = path.stat().st_size
                asset = path.name
                public_url = (
                    f"https://github.com/{REPO}/releases/download/{urllib.parse.quote(tag)}/"
                    f"{urllib.parse.quote(asset)}"
                )
                backup_url = hf_public_url(relative_path)
                urls = [public_url] + ([backup_url] if backup_url else [])
                stable["items"][qid] = {
                    "url": public_url,
                    "urls": urls,
                    "backupUrl": backup_url,
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

                pending.append(path)
                if len(pending) >= UPLOAD_BATCH:
                    uploaded, reused = upload_batch(tag, pending, known_assets)
                    total_uploaded += uploaded
                    total_reused += reused
                    print(
                        f"{tag}: uploaded/replaced {total_uploaded}, reused {total_reused} total"
                    )
                    pending = []
                    write_checkpoint(stable)

            if pending:
                uploaded, reused = upload_batch(tag, pending, known_assets)
                total_uploaded += uploaded
                total_reused += reused
                print(
                    f"{tag}: uploaded/replaced {total_uploaded}, reused {total_reused} total"
                )
                write_checkpoint(stable)

            final_assets = release_assets(tag)
            missing_or_wrong = [
                name
                for name, expected_size in expected_assets.items()
                if final_assets.get(name) != expected_size
            ]
            if missing_or_wrong:
                preview = ", ".join(missing_or_wrong[:10])
                raise RuntimeError(
                    f"{tag}: {len(missing_or_wrong)} asset(s) missing or wrong size after upload: {preview}"
                )
            print(
                f"Verified {tag}: {len(expected_assets)} expected assets are present "
                f"({len(final_assets)} total assets in Release)"
            )

    stable["releaseNamespace"] = NAMESPACE
    stable["indexed"] = len(stable["items"])
    stable["releases"] = sorted(
        {rec.get("release") for rec in stable["items"].values() if rec.get("release")}
    )
    stable["voiceVariantCount"] = pack.get("voiceVariantCount")
    stable["speakerCount"] = pack.get("speakerCount")
    stable["publisher"] = {
        "uploadBatch": UPLOAD_BATCH,
        "uploadRetries": UPLOAD_RETRIES,
        "resumable": True,
    }
    write_checkpoint(stable)

    print(
        f"Published/replaced {total_uploaded} audio assets; reused {total_reused}; "
        f"verified {len(releases_used)} release(s)"
    )
    if HF_DATASET_REPO:
        print(
            "Backup URL namespace: "
            f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/"
        )
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
    except subprocess.TimeoutExpired as exc:
        print(f"Command timed out: {exc.cmd}", file=sys.stderr)
        raise SystemExit(124)
