#!/usr/bin/env python3
"""Read-only API route and safe GET response probe for original/candidate image.

Called only in a network-disabled *disposable* Docker container with a private
writable SQLite snapshot at /srv/data. Never mount/write production SQLite.
Outputs a structured report to stdout only; never exposes source text or audio.
"""
import asyncio
import hashlib
import importlib
import json
import re
from fastapi.routing import APIRoute

app = importlib.import_module("app.main").app
routes = []
for route in app.routes:
    methods = sorted(route.methods or [])
    routes.append({"path": route.path, "methods": methods})
routes.sort(key=lambda row: (row["path"], ",".join(row["methods"])))

SAFE = re.compile(r"^/(healthz|api/v1/(status|voices|vocabulary|words|conjugations?|audio|catalog)(?:/.*)?)$")
DENY = re.compile(r"(?i)(delete|remove|rebuild|refresh|sync|import|clear|reset|download|archive|export)")
MAX_BODY = 262144

async def probe(path):
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path, "raw_path": path.encode("utf-8"),
        "query_string": b"", "root_path": "", "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
    }
    events = []
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        events.append(message)

    try:
        await asyncio.wait_for(app(scope, receive, send), timeout=12)
        starts = [e for e in events if e["type"] == "http.response.start"]
        if len(starts) != 1:
            return {"error": "HTTP_RESPONSE_FRAMING"}
        raw = b"".join(e.get("body", b"") for e in events
                       if e.get("type") == "http.response.body")
        # Limit output exposure: hash the body, never store the content.
        if len(raw) > MAX_BODY:
            return {"status": starts[0]["status"], "body": "OVERSIZE"}
        return {
            "status": starts[0]["status"],
            "length": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    except Exception as ex:
        return {"error": type(ex).__name__}

async def main():
    tests = {}
    # Probe only fixed non-parameter GET routes that are safe to call and
    # relevant to current site; do not invoke mutating routes in any method.
    for route in routes:
        p = route["path"]
        if ("GET" in route["methods"] and "{" not in p and
                SAFE.fullmatch(p) and not DENY.search(p)):
            tests[p] = await probe(p)

    # The critical publicly used endpoints are always exercised.
    for path in ("/healthz", "/api/v1/status", "/api/v1/voices"):
        if path not in tests:
            tests[path] = await probe(path)

    print(json.dumps({
        "routes": routes,
        "checks": tests,
    }, sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    asyncio.run(main())
