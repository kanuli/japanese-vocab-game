#!/usr/bin/env python3
"""Generate a VOICEVOX audio pack matching Listening Game question IDs.

Expected environment:
- VOICEVOX_ENGINE_URL (default http://127.0.0.1:50021)
- JLPT (N1..N5, default N5)
- COUNT (positive integer or ALL, default 20)
- SPEAKER_NAME (default 四国めたん)
- STYLE_NAME (default ノーマル; empty selects the first style)
- OUTPUT_DIR (default voicevox-pack)

The output layout is directly uploadable into the OneDrive App Folder:
  voicevox/{JLPT}/{question-id}.mp3
  voicevox-index.json
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE = os.environ.get("VOICEVOX_ENGINE_URL", "http://127.0.0.1:50021").rstrip("/")
JLPT = os.environ.get("JLPT", "N5").upper().strip()
COUNT_RAW = os.environ.get("COUNT", "20").strip().upper()
SPEAKER_NAME = os.environ.get("SPEAKER_NAME", "四国めたん").strip()
STYLE_NAME = os.environ.get("STYLE_NAME", "ノーマル").strip()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "voicevox-pack"))

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
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(url: str, *, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=180) as r:
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


def resolve_style() -> tuple[int, str, str]:
    speakers = http_json(f"{ENGINE}/speakers")
    speaker = next((s for s in speakers if str(s.get("name", "")).strip() == SPEAKER_NAME), None)
    if not speaker:
        available = ", ".join(str(s.get("name", "")) for s in speakers)
        raise RuntimeError(f"Speaker not found: {SPEAKER_NAME}. Available: {available}")
    styles = speaker.get("styles") or []
    style = None
    if STYLE_NAME:
        style = next((s for s in styles if str(s.get("name", "")).strip() == STYLE_NAME), None)
    if style is None and styles:
        style = styles[0]
    if not style:
        raise RuntimeError(f"No style found for speaker: {SPEAKER_NAME}")
    return int(style["id"]), str(speaker.get("name", SPEAKER_NAME)), str(style.get("name", ""))


def fetch_questions() -> list[dict]:
    if JLPT not in FILES:
        raise RuntimeError(f"Invalid JLPT level: {JLPT}")
    data = http_json(HANABIRA_BASE + FILES[JLPT])
    rows: list[dict] = []
    for pi, point in enumerate(data):
        grammar = str(point.get("title", "")).strip()
        for ei, example in enumerate(point.get("examples") or []):
            jp = str(example.get("jp", "")).strip()
            if len(jp) < 5 or len(jp) > 95:
                continue
            rows.append(
                {
                    "id": f"{JLPT}-{pi}-{ei}",
                    "level": JLPT,
                    "jp": jp,
                    "grammar": grammar,
                }
            )
    if COUNT_RAW != "ALL":
        try:
            count = int(COUNT_RAW)
        except ValueError as exc:
            raise RuntimeError("COUNT must be a positive integer or ALL") from exc
        if count <= 0:
            raise RuntimeError("COUNT must be > 0")
        rows = rows[:count]
    return rows


def synthesize(text: str, style_id: int) -> bytes:
    qs = urllib.parse.urlencode({"text": text, "speaker": style_id})
    query = http_json(f"{ENGINE}/audio_query?{qs}", method="POST", body=b"")
    payload = json.dumps(query, ensure_ascii=False).encode("utf-8")
    return http_bytes(
        f"{ENGINE}/synthesis?{urllib.parse.urlencode({'speaker': style_id})}",
        method="POST",
        body=payload,
        headers={"Content-Type": "application/json"},
    )


def wav_to_mp3(wav: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav)
        tmp = Path(f.name)
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(tmp),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-b:a",
                "48k",
                str(out),
            ],
            check=True,
        )
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    wait_engine()
    style_id, speaker, style = resolve_style()
    questions = fetch_questions()
    if not questions:
        raise RuntimeError("No Hanabira examples found for the selected level")

    audio_root = OUTPUT_DIR / "voicevox" / JLPT
    audio_root.mkdir(parents=True, exist_ok=True)
    index = {"version": 1, "items": {}}

    print(f"VOICEVOX: {speaker} / {style} (style id {style_id})")
    print(f"Generating {len(questions)} {JLPT} sentences")

    for i, q in enumerate(questions, 1):
        filename = f"{q['id']}.mp3"
        relative = f"voicevox/{JLPT}/{filename}"
        out = audio_root / filename
        print(f"[{i}/{len(questions)}] {q['id']}  {q['jp']}")
        wav = synthesize(q["jp"], style_id)
        wav_to_mp3(wav, out)
        index["items"][q["id"]] = {
            "path": relative,
            "speaker": speaker,
            "style": style,
            "credit": f"VOICEVOX:{speaker}",
            "text": q["jp"],
            "grammar": q["grammar"],
            "level": q["level"],
        }

    (OUTPUT_DIR / "voicevox-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "README.txt").write_text(
        "Japanese Listening Game VOICEVOX pack\n"
        f"JLPT: {JLPT}\n"
        f"Speaker: {speaker}\n"
        f"Style: {style}\n"
        f"Credit: VOICEVOX:{speaker}\n\n"
        "Upload the voicevox folder and voicevox-index.json into the game's OneDrive App Folder.\n",
        encoding="utf-8",
    )
    print(f"Done: {OUTPUT_DIR.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, urllib.error.URLError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
