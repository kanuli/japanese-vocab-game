#!/usr/bin/env python3
"""Validate a generated conjugation chunk tar: IDs, non-zero audio, tar opens, sha256, sample decode."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path


def main() -> int:
    tar_path = Path(os.environ["TAR"])
    catalog = json.loads(Path(os.environ["CATALOG"]).read_text(encoding="utf-8"))
    out = Path(os.environ.get("OUT", str(tar_path.with_suffix(".validation.json"))))
    expected = [x["id"] for x in catalog.get("items") or []]
    report = {
        "ok": False,
        "tar": tar_path.name,
        "expectedCount": len(expected),
        "memberCount": 0,
        "idsMatch": False,
        "tarOpens": False,
        "sha256": None,
        "size": 0,
        "nonZeroAudio": False,
        "sampleDecode": False,
        "failedReadingIds": [],
        "errors": [],
    }
    if not tar_path.is_file():
        report["errors"].append("missing tar")
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(1)
    data = tar_path.read_bytes()
    report["size"] = len(data)
    report["sha256"] = hashlib.sha256(data).hexdigest()
    try:
        with tarfile.open(tar_path, "r:") as tf:
            members = [m for m in tf.getmembers() if m.isfile()]
            report["tarOpens"] = True
            got = []
            tiny = []
            for m in members:
                wid = Path(m.name).stem
                got.append(wid)
                if int(m.size) < 400:
                    tiny.append(wid)
            report["memberCount"] = len(got)
            report["idsMatch"] = set(got) == set(expected)
            report["nonZeroAudio"] = not tiny and len(got) > 0
            if not report["idsMatch"]:
                report["errors"].append("IDs mismatch")
                report["failedReadingIds"] = sorted(set(expected) ^ set(got))
            if tiny:
                report["errors"].append("tiny audio")
                report["failedReadingIds"] = sorted(set(report["failedReadingIds"]) | set(tiny))
            sample = members[0] if members else None
            if sample:
                with tempfile.TemporaryDirectory() as td:
                    tf.extract(sample, path=td)
                    mp3 = Path(td) / sample.name
                    r = subprocess.run(
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(mp3), "-f", "null", "-"],
                        capture_output=True,
                        text=True,
                    )
                    report["sampleDecode"] = r.returncode == 0
                    if r.returncode != 0:
                        report["errors"].append("sample decode failed")
                        report["failedReadingIds"] = sorted(set(report["failedReadingIds"]) | {Path(sample.name).stem})
    except tarfile.TarError as e:
        report["errors"].append(f"tar open failed: {e}")
    report["ok"] = (
        report["tarOpens"]
        and report["idsMatch"]
        and report["nonZeroAudio"]
        and report["sampleDecode"]
        and not report["errors"]
        and report["size"] > 0
        and bool(report["sha256"])
    )
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
