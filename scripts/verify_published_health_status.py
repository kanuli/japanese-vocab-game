#!/usr/bin/env python3
"""Verify the exact off-Pages health commit, not a cached mutable branch URL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

REPOSITORY = "kanuli/japanese-vocab-game"


def verify_payload(expected, actual, run_id):
    if (not isinstance(expected, dict) or not isinstance(actual, dict)
        or type(expected.get("runId")) is not int or expected["runId"] != run_id
        or type(actual.get("runId")) is not int or actual["runId"] != run_id
        or expected.get("version") != 3 or expected.get("status") not in {"ok", "error"}
        or actual != expected):
        raise ValueError("published-health-payload-mismatch")


def verify_commit(commit_sha, expected, run_id):
    if not isinstance(commit_sha, str) or re.fullmatch(r"[0-9a-f]{40}", commit_sha) is None:
        raise ValueError("published-health-commit-invalid")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("published-health-run-invalid")
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit_sha}/maintenance-status.json"
    for attempt in range(3):
        request = urllib.request.Request(url, headers={"User-Agent": "Vocab-Health-Commit-Verifier/1",
                                                      "Cache-Control": "no-cache"}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                # A changed/unparseable HTTP200 payload is not a transient
                # success and is never replaced by the local expected record.
                actual = json.loads(response.read(1_000_001).decode("utf-8"))
            verify_payload(expected, actual, run_id)
            return actual
        except urllib.error.HTTPError as exc:
            if not 500 <= exc.code < 600 or attempt == 2:
                raise ValueError("published-health-http-failed") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ValueError("published-health-transport-failed") from None
        time.sleep(attempt + 1)
    raise ValueError("published-health-not-verified")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    result = verify_commit(args.commit, expected, args.run_id)
    print("Published health status", result["status"], result.get("auditedSha"), result.get("liveSha"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("PUBLISHED_HEALTH_NOT_VERIFIED type=" + type(exc).__name__)
        raise SystemExit(1) from None
