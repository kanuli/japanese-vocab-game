#!/usr/bin/env python3
"""Generate a VOICEVOX audio pack matching Listening Game question IDs.

Expected environment:
- VOICEVOX_ENGINE_URL (default http://127.0.0.1:50021)
- JLPT (ALL or N1..N5, default ALL)
- COUNT (positive integer per selected level or ALL, default ALL)
- SPEAKER_NAME (MIXED/ALL rotates available speakers; otherwise exact speaker name)
- STYLE_NAME (preferred style name, default ノーマル; falls back to first style)
- OUTPUT_DIR (default voicevox-pack)

The output layout is directly importable into the OneDrive App Folder:
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
JLPT = os.environ.get("JLPT", "ALL").upper().strip()
COUNT_RAW = os.environ.get("COUNT", "ALL").strip().upper()
SPEAKER_NAME = os.environ.get("SPEAKER_NAME", "MIXED").strip()
STYLE_NAME = os.environ.get("STYLE_NAME", "ノーマル").strip()
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "voicevox-pack"))

LEVELS = ["N5", "N4", "N3", "N2", "N1"]
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


def preferred_style(speaker: dict) -> dict | None:
    styles = speaker.get("styles") or []
    if not styles:
        return None
    if STYLE_NAME:
        exact = next((s for s in styles if str(s.get("name", "")).strip() == STYLE_NAME), None)
        if exact is not None:
            return exact
    return styles[0]


def resolve_voices() -> list[tuple[int, str, str]]:
    speakers = http_json(f"{ENGINE}/speakers")
    mode = SPEAKER_NAME.upper()

    if mode in {"MIXED", "ALL", "RANDOM"}:
        voices: list[tuple[int, str, str]] = []
        for speaker in speakers:
            style = preferred_style(speaker)
            if style is None:
                continue
            name = str(speaker.get("name", "")).strip()
            if not name:
                continue
            voices.append((int(style["id"]), name, str(style.get("name", "")).strip()))
        if not voices:
            raise RuntimeError("No VOICEVOX speakers/styles are available for MIXED mode")
        return voices

    speaker = next((s for s in speakers if str(s.get("name", "")).strip() == SPEAKER_NAME), None)
    if not speaker:
        available = ", ".join(str(s.get("name", "")) for s in speakers)
        raise RuntimeError(f"Speaker not found: {SPEAKER_NAME}. Available: {available}")
    style = preferred_style(speaker)
    if not style:
        raise RuntimeError(f"No style found for speaker: {SPEAKER_NAME}")
    return [(int(style["id"]), str(speaker.get("name", SPEAKER_NAME)).strip(), str(style.get("name", "")).strip())]


def selected_levels() -> list[str]:
    if JLPT == "ALL":
        return LEVELS.copy()
    if JLPT in FILES:
        return [JLPT]
    raise RuntimeError(f"Invalid JLPT level: {JLPT}")


def level_limit() -> int | None:
    if COUNT_RAW == "ALL":
        return None
    try:
        count = int(COUNT_RAW)
    except ValueError as exc:
        raise RuntimeError("COUNT must be a positive integer or ALL") from exc
    if count <= 0:
        raise RuntimeError("COUNT must be > 0")
    return count


def fetch_level_questions(level: str, limit: int | None) -> list[dict]:
    data = http_json(HANABIRA_BASE + FILES[level])
    rows: list[dict] = []
    for pi, point in enumerate(data):
        grammar = str(point.get("title", "")).strip()
        for ei, example in enumerate(point.get("examples") or []):
            jp = str(example.get("jp", "")).strip()
            if len(jp) < 5 or len(jp) > 95:
                continue
            rows.append({"id": f"{level}-{pi}-{ei}", "level": level, "jp": jp, "grammar": grammar})
    if limit is not None:
        rows = rows[:limit]
    return rows


def fetch_questions() -> list[dict]:
    limit = level_limit()
    rows: list[dict] = []
    for level in selected_levels():
        level_rows = fetch_level_questions(level, limit)
        print(f"Loaded {len(level_rows)} {level} sentences")
        rows.extend(level_rows)
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
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
            "-ac", "1", "-ar", "24000", "-b:a", "48k", str(out)
        ], check=True)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    wait_engine()
    voices = resolve_voices()
    questions = fetch_questions()
    if not questions:
        raise RuntimeError("No Hanabira examples found for the selected level(s)")

    levels = selected_levels()
    index = {
        "version": 1,
        "speakerMode": "mixed" if len(voices) > 1 else "single",
        "voices": [
            {"speaker": speaker, "style": style, "credit": f"VOICEVOX:{speaker}"}
            for _, speaker, style in voices
        ],
        "items": {},
    }

    if len(voices) > 1:
        print(f"VOICEVOX MIXED mode: {len(voices)} speakers")
        for _, speaker, style in voices:
            print(f"  - {speaker} / {style}")
    else:
        style_id, speaker, style = voices[0]
        print(f"VOICEVOX: {speaker} / {style} (style id {style_id})")
    print(f"Generating {len(questions)} sentences across {', '.join(levels)}")

    for i, q in enumerate(questions, 1):
        style_id, speaker, style = voices[(i - 1) % len(voices)]
        level = q["level"]
        filename = f"{q['id']}.mp3"
        relative = f"voicevox/{level}/{filename}"
        out = OUTPUT_DIR / relative
        print(f"[{i}/{len(questions)}] {q['id']} [{speaker}/{style}]  {q['jp']}")
        wav = synthesize(q["jp"], style_id)
        wav_to_mp3(wav, out)
        index["items"][q["id"]] = {
            "path": relative,
            "speaker": speaker,
            "style": style,
            "credit": f"VOICEVOX:{speaker}",
            "text": q["jp"],
            "grammar": q["grammar"],
            "level": level,
        }

    (OUTPUT_DIR / "voicevox-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    voice_lines = "\n".join(f"- {speaker} / {style} / VOICEVOX:{speaker}" for _, speaker, style in voices)
    (OUTPUT_DIR / "README.txt").write_text(
        "Japanese Listening Game VOICEVOX pack\n"
        f"JLPT: {', '.join(levels)}\n"
        f"Speaker mode: {'MIXED' if len(voices) > 1 else 'SINGLE'}\n"
        f"Audio files: {len(index['items'])}\n\n"
        "Voices / credits:\n"
        f"{voice_lines}\n\n"
        "Import this single GitHub Actions artifact ZIP from the Listening page; "
        "the page will upload the audio and index into OneDrive automatically.\n",
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
