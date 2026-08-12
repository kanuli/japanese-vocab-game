#!/usr/bin/env python3
"""Build the public full-coverage VOICEVOX index from 43x5 level manifests."""

from __future__ import annotations

import json
import os
from pathlib import Path

MANIFEST_DIR = Path(os.environ.get("MANIFEST_DIR", "voicevox-full-manifests"))
OUT = Path(os.environ.get("INDEX_OUT", "voicevox-full-index.json"))
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kanuli/japanese-vocab-game").strip()
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup").strip()
RELEASE_NAMESPACE = os.environ.get("RELEASE_NAMESPACE", "voicevox-full-v1").strip()
EXPECTED_SPEAKERS = int(os.environ.get("EXPECTED_SPEAKERS", "43"))
EXPECTED_QUESTIONS = int(os.environ.get("EXPECTED_QUESTIONS", "3310"))
LEVELS = ["N5", "N4", "N3", "N2", "N1"]


def load_manifests() -> list[dict]:
    files = sorted(MANIFEST_DIR.glob("*.json"))
    if not files:
        raise RuntimeError(f"No full-coverage manifests found in {MANIFEST_DIR}")
    rows = []
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise RuntimeError(f"Unsupported manifest version in {path}")
        rows.append(data)
    return rows


def main() -> int:
    rows = load_manifests()
    by_speaker: dict[str, dict[str, dict]] = {}
    identity: dict[str, tuple[str, str, int, str]] = {}

    for m in rows:
        key = str(m.get("speakerKey", "")).strip()
        level = str(m.get("level", "")).strip().upper()
        if not key or level not in LEVELS:
            raise RuntimeError(f"Invalid manifest identity: {key=} {level=}")
        if level in by_speaker.setdefault(key, {}):
            raise RuntimeError(f"Duplicate manifest for {key}/{level}")
        by_speaker[key][level] = m
        ident = (str(m.get("speaker", "")), str(m.get("style", "")), int(m.get("styleId")), str(m.get("credit", "")))
        if key in identity and identity[key] != ident:
            raise RuntimeError(f"Speaker identity changed across levels for {key}: {identity[key]} vs {ident}")
        identity[key] = ident

    if len(by_speaker) != EXPECTED_SPEAKERS:
        raise RuntimeError(f"Expected {EXPECTED_SPEAKERS} speakers, found {len(by_speaker)}")
    for key, levels in by_speaker.items():
        if set(levels) != set(LEVELS):
            raise RuntimeError(f"{key} is missing levels: {sorted(set(LEVELS)-set(levels))}")

    # Every speaker must cover exactly the same question ID set at every level.
    baseline_key = sorted(by_speaker)[0]
    baseline_by_level = {level: set(by_speaker[baseline_key][level]["questions"]) for level in LEVELS}
    questions: dict[str, dict] = {}
    for level in LEVELS:
        baseline_manifest = by_speaker[baseline_key][level]
        for qid, q in baseline_manifest["questions"].items():
            questions[qid] = {
                "level": level,
                "text": q["text"],
                "grammar": q.get("grammar", ""),
            }

    if len(questions) != EXPECTED_QUESTIONS:
        raise RuntimeError(f"Expected {EXPECTED_QUESTIONS} questions, found {len(questions)}")

    speakers: dict[str, dict] = {}
    for key in sorted(by_speaker):
        speaker, style, style_id, credit = identity[key]
        bundles: dict[str, dict] = {}
        total = 0
        for level in LEVELS:
            m = by_speaker[key][level]
            qids = set(m["questions"])
            if qids != baseline_by_level[level]:
                missing = sorted(baseline_by_level[level] - qids)[:5]
                extra = sorted(qids - baseline_by_level[level])[:5]
                raise RuntimeError(f"Unequal coverage for {key}/{level}; missing={missing} extra={extra}")
            asset = str(m["asset"])
            tag = f"{RELEASE_NAMESPACE}-{key}-{level.lower()}"
            github_url = f"https://github.com/{GITHUB_REPO}/releases/download/{tag}/{asset}"
            hf_url = f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/voicevox-full/{key}/{asset}"
            members = {qid: [int(q["offset"]), int(q["size"])] for qid, q in m["questions"].items()}
            bundles[level] = {
                "asset": asset,
                "release": tag,
                "githubUrl": github_url,
                "hfUrl": hf_url,
                "members": members,
                "count": len(members),
            }
            total += len(members)
        if total != EXPECTED_QUESTIONS:
            raise RuntimeError(f"Speaker {key} has {total} recordings instead of {EXPECTED_QUESTIONS}")
        speakers[key] = {
            "speaker": speaker,
            "style": style,
            "styleId": style_id,
            "credit": credit,
            "questionCount": total,
            "bundles": bundles,
        }

    index = {
        "version": 3,
        "storage": "github-releases+hf-range-bundles",
        "primaryStorage": "github-releases",
        "backupStorage": "huggingface-dataset",
        "githubRepository": GITHUB_REPO,
        "huggingFaceDataset": HF_DATASET_REPO,
        "releaseNamespace": RELEASE_NAMESPACE,
        "indexed": len(questions),
        "speakerCount": len(speakers),
        "recordingCount": len(questions) * len(speakers),
        "coverage": "full-per-speaker",
        "questions": questions,
        "speakers": speakers,
    }
    if index["recordingCount"] != 142330:
        raise RuntimeError(f"Expected 142330 recordings, got {index['recordingCount']}")

    OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Built {OUT}: {index['speakerCount']} speakers x {index['indexed']} questions = {index['recordingCount']} recordings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
