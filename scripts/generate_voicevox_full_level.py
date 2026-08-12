#!/usr/bin/env python3
"""Generate one JLPT-level VOICEVOX bundle for one speaker.

This generator is used by the full-coverage 43-speaker workflow.  Each matrix
job synthesizes every Hanabira question in one JLPT level with one canonical
VOICEVOX style, compresses the MP3s, and writes an uncompressed TAR plus a
small manifest containing byte offsets for HTTP Range playback.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE = os.environ.get("VOICEVOX_ENGINE_URL", "http://127.0.0.1:50021").rstrip("/")
LEVEL = os.environ.get("JLPT", "").upper().strip()
SPEAKER_KEY = os.environ.get("SPEAKER_KEY", "").strip()
SPEAKER_NAME = os.environ.get("SPEAKER_NAME", "").strip()
STYLE_ID_RAW = os.environ.get("STYLE_ID", "").strip()
STYLE_NAME = os.environ.get("STYLE_NAME", "").strip()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "voicevox-full-out"))

FILES = {
    "N5": "grammar_ja_N5_full_alphabetical_0001.json",
    "N4": "grammar_ja_N4_full_alphabetical_0001.json",
    "N3": "grammar_ja_N3_full_alphabetical_0001.json",
    "N2": "grammar_ja_N2_full_alphabetical_0001.json",
    "N1": "grammar_ja_N1_full_alphabetical_0001.json",
}
HANABIRA_BASE = "https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/"


def http_json(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=240) as r:
        return r.read()


def wait_engine() -> None:
    last = None
    for _ in range(90):
        try:
            http_bytes(f"{ENGINE}/version")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise RuntimeError(f"VOICEVOX Engine did not become ready: {last}")


def fetch_questions() -> list[dict]:
    if LEVEL not in FILES:
        raise RuntimeError(f"Invalid JLPT level: {LEVEL}")
    data = http_json(HANABIRA_BASE + FILES[LEVEL])
    rows: list[dict] = []
    for pi, point in enumerate(data):
        grammar = str(point.get("title", "")).strip()
        for ei, example in enumerate(point.get("examples") or []):
            jp = str(example.get("jp", "")).strip()
            if len(jp) < 5 or len(jp) > 95:
                continue
            rows.append({"id": f"{LEVEL}-{pi}-{ei}", "level": LEVEL, "jp": jp, "grammar": grammar})
    return rows


def verify_voice() -> tuple[int, str, str]:
    if not SPEAKER_KEY or not SPEAKER_NAME or not STYLE_ID_RAW:
        raise RuntimeError("SPEAKER_KEY, SPEAKER_NAME and STYLE_ID are required")
    try:
        style_id = int(STYLE_ID_RAW)
    except ValueError as exc:
        raise RuntimeError(f"Invalid STYLE_ID: {STYLE_ID_RAW}") from exc
    speakers = http_json(f"{ENGINE}/speakers")
    speaker = next((s for s in speakers if str(s.get("name", "")).strip() == SPEAKER_NAME), None)
    if not speaker:
        raise RuntimeError(f"VOICEVOX speaker not found: {SPEAKER_NAME}")
    style = next((s for s in (speaker.get("styles") or []) if int(s.get("id", -1)) == style_id), None)
    if not style:
        raise RuntimeError(f"VOICEVOX style id {style_id} is not available for {SPEAKER_NAME}")
    actual_style = str(style.get("name", "")).strip()
    if STYLE_NAME and STYLE_NAME != actual_style:
        raise RuntimeError(f"VOICEVOX style mismatch: expected {STYLE_NAME}, engine returned {actual_style}")
    return style_id, SPEAKER_NAME, actual_style


def synthesize(text: str, style_id: int) -> bytes:
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            qs = urllib.parse.urlencode({"text": text, "speaker": style_id})
            query = http_json(f"{ENGINE}/audio_query?{qs}", method="POST", body=b"")
            payload = json.dumps(query, ensure_ascii=False).encode("utf-8")
            return http_bytes(
                f"{ENGINE}/synthesis?{urllib.parse.urlencode({'speaker': style_id})}",
                method="POST",
                body=payload,
                headers={"Content-Type": "application/json"},
            )
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt == 4:
                break
            time.sleep(min(8, attempt * 2))
    raise RuntimeError(f"VOICEVOX synthesis failed after retries: {last}")


def wav_to_mp3(wav: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav)
        tmp = Path(f.name)
    try:
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
                "-ac", "1", "-ar", "24000", "-b:a", "48k", str(out),
            ],
            check=True,
        )
    finally:
        tmp.unlink(missing_ok=True)


def build_tar(mp3_dir: Path, qids: list[str], tar_path: Path) -> dict[str, list[int]]:
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "w", format=tarfile.USTAR_FORMAT) as tf:
        for qid in qids:
            src = mp3_dir / f"{qid}.mp3"
            if not src.is_file() or src.stat().st_size < 500:
                raise RuntimeError(f"Missing/invalid MP3 before TAR creation: {src}")
            info = tf.gettarinfo(str(src), arcname=f"{qid}.mp3")
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            with src.open("rb") as fh:
                tf.addfile(info, fh)

    members: dict[str, list[int]] = {}
    with tarfile.open(tar_path, "r:") as tf:
        for member in tf.getmembers():
            if not member.isfile() or not member.name.endswith(".mp3"):
                continue
            qid = Path(member.name).stem
            members[qid] = [int(member.offset_data), int(member.size)]
    if set(members) != set(qids):
        raise RuntimeError("TAR member index does not match generated question IDs")
    return members


def main() -> int:
    wait_engine()
    style_id, speaker, style = verify_voice()
    questions = fetch_questions()
    if not questions:
        raise RuntimeError(f"No Hanabira questions found for {LEVEL}")

    out = OUTPUT_DIR
    work = out / "mp3"
    work.mkdir(parents=True, exist_ok=True)
    print(f"Generating {len(questions)} {LEVEL} questions for {speaker} / {style} (style_id={style_id})")

    for i, q in enumerate(questions, 1):
        dest = work / f"{q['id']}.mp3"
        if dest.is_file() and dest.stat().st_size >= 500:
            continue
        print(f"[{i}/{len(questions)}] {q['id']} {q['jp']}")
        wav_to_mp3(synthesize(q["jp"], style_id), dest)

    asset = f"{SPEAKER_KEY}-{LEVEL}.tar"
    tar_path = out / asset
    qids = [q["id"] for q in questions]
    members = build_tar(work, qids, tar_path)

    manifest = {
        "version": 1,
        "speakerKey": SPEAKER_KEY,
        "speaker": speaker,
        "style": style,
        "styleId": style_id,
        "credit": f"VOICEVOX:{speaker}",
        "level": LEVEL,
        "count": len(questions),
        "asset": asset,
        "questions": {
            q["id"]: {
                "text": q["jp"],
                "grammar": q["grammar"],
                "offset": members[q["id"]][0],
                "size": members[q["id"]][1],
            }
            for q in questions
        },
    }
    manifest_path = out / f"{SPEAKER_KEY}-{LEVEL}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # The TAR is the publishable object; remove intermediates to minimize runner disk usage.
    for f in work.glob("*.mp3"):
        f.unlink(missing_ok=True)
    try:
        work.rmdir()
    except OSError:
        pass

    print(f"Bundle: {tar_path} ({tar_path.stat().st_size} bytes)")
    print(f"Manifest: {manifest_path} ({len(questions)} questions)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
