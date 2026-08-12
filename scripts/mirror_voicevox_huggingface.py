#!/usr/bin/env python3
"""Mirror a generated VOICEVOX pack to a public Hugging Face Dataset.

Expected environment:
- PACK_DIR (default: voicevox-pack)
- HF_DATASET_REPO (default: kanuli1983/japanese-listening-voicevox-backup)
- HF_TOKEN (required for upload; keep it in GitHub Actions Secrets)

The folder layout is preserved so browser fallback URLs are deterministic:
  https://huggingface.co/datasets/{repo}/resolve/main/voicevox/N5/N5-0-0.mp3
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PACK_DIR = Path(os.environ.get("PACK_DIR", "voicevox-pack"))
HF_REPO = os.environ.get(
    "HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup"
).strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()


def main() -> int:
    if not HF_TOKEN:
        print("HF_TOKEN is not configured; skipping Hugging Face backup mirror.")
        return 0
    index_path = PACK_DIR / "voicevox-index.json"
    if not index_path.is_file():
        raise SystemExit(f"Missing {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    items = index.get("items") or {}
    if not items:
        raise SystemExit("VOICEVOX pack index has no items")

    missing = []
    for qid, rec in items.items():
        rel = str(rec.get("path", ""))
        if not rel or not (PACK_DIR / rel).is_file():
            missing.append((qid, rel))
    if missing:
        raise SystemExit(f"Missing generated audio files: {missing[:5]}")

    from huggingface_hub import HfApi

    api = HfApi(token=HF_TOKEN)
    # upload_folder is resumable/deduplicated by the Hub/Xet backend. Uploading a
    # partial JLPT pack updates only those paths; existing files for other levels remain.
    api.upload_folder(
        folder_path=str(PACK_DIR),
        repo_id=HF_REPO,
        repo_type="dataset",
        path_in_repo=".",
        commit_message="Mirror VOICEVOX listening audio from GitHub Actions",
    )
    print(f"Mirrored {len(items)} VOICEVOX audio records to {HF_REPO}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Hugging Face mirror failed: {exc}", file=sys.stderr)
        raise
