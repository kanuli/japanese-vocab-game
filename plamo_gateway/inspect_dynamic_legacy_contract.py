#!/usr/bin/env python3
"""Step 9AK: inspect only validated route report + readonly DB schema.

No sudo, Docker start, SQLite copies, password, audio reads or prod changes.
Never print vocabulary entries, tokens, private paths or database payloads.
"""
import json
import os
import sqlite3
import sys
import urllib.parse
from pathlib import Path

HOME = Path.home()
REPORT = HOME / "japanese-api-candidates" / "plamo-8443-20261112_141623" / "step9aj-report.json"
DB = Path("/volume2/docker/japanese-api/data/japanese.sqlite3")
CRITICAL = {"vocabulary", "audio_assets", "conjugation_audio", "api_voice_stats"}

def stop(msg):
    print("STEP_9AK=FAIL", flush=True)
    raise SystemExit(msg)

def safe_name(name):
    return isinstance(name, str) and name and len(name) < 90 and all(
        c.isalnum() or c in "_-" for c in name)

def main():
    print("=== STEP 9AK: REAL DATA ROUTE CONTRACT INVENTORY ===", flush=True)
    if not REPORT.is_file() or REPORT.is_symlink():
        stop("STEP_9AJ_H_REPORT_MISSING")
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        old = data["baseline"]
        new = data["candidate"]
        oldroutes = {(r["path"], tuple(r["methods"])) for r in old["routes"]}
        newroutes = {(r["path"], tuple(r["methods"])) for r in new["routes"]}
    except (ValueError, KeyError, TypeError) as exc:
        stop("REPORT_INVALID_%s" % type(exc).__name__)
    expected = {
        ("/api/v1/translate/plamo", ("OPTIONS",)),
        ("/api/v1/translate/plamo", ("POST",)),
    }
    if len(oldroutes) != 16 or len(newroutes) != 18 or oldroutes - newroutes or newroutes - oldroutes != expected:
        stop("STEP_9AJ_H_ROUTE_PARITY_INCOMPATIBLE")
    print("VERIFIED_ORIGINAL_ROUTES=16", flush=True)
    print("VERIFIED_CANDIDATE_ROUTES=18", flush=True)
    print("ORIGINAL_GET_ROUTE_CONTRACT_BEGIN", flush=True)
    for path, methods in sorted(oldroutes):
        if "GET" in methods:
            print("GET_ROUTE=%s" % path, flush=True)
    print("ORIGINAL_GET_ROUTE_CONTRACT_END", flush=True)
    print("DYNAMIC_GET_ROUTES=%d" %
          sum("GET" in methods and "{" in path for path, methods in oldroutes), flush=True)

    if not DB.is_file() or DB.is_symlink():
        stop("PRODUCTION_DATABASE_MISSING_OR_LINK")
    uri = "file:" + urllib.parse.quote(str(DB), safe="/") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=8)
    try:
        conn.execute("PRAGMA query_only=ON")
        names = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        print("SQLITE_READONLY_SCHEMA=PASS", flush=True)
        print("SQLITE_TABLE_COUNT=%d" % len(names), flush=True)
        for name in names:
            if not safe_name(name):
                continue
            # Names and columns only: no personal data, rows or payloads.
            if (name.lower() in CRITICAL or
                    any(t in name.lower() for t in ("vocab", "audio", "conjug", "voice", "lexicon"))):
                cols = list(conn.execute('PRAGMA table_info("%s")' % name))
                colnames = [c[1] for c in cols if safe_name(c[1])]
                print("SCHEMA_TABLE=%s COLUMNS=%s" % (name, ",".join(colnames[:32])), flush=True)
        print("PRODUCTION_DATABASE_ROWS_READ=0", flush=True)
    finally:
        conn.close()

    print("PRODUCTION_SQLITE_WRITES=NO", flush=True)
    print("DOCKER_CONTAINERS_STARTED=NO", flush=True)
    print("PRODUCTION_SOURCE_MODIFIED=NO", flush=True)
    print("STEP_9AK=PASS", flush=True)

if __name__ == "__main__":
    main()
