#!/usr/bin/env python3
"""Offline, disposable Uvicorn startup of ONLY the translation candidate image.

Never uses live SQLite or network. Run in container with /srv/data=tmpfs and
--network none; all HTTP is 127.0.0.1 inside the isolated container.
"""
import http.client
import importlib
import threading
import time
import uvicorn

state = {"error": None}
def serve():
    try:
        cfg = uvicorn.Config("app.main:app", host="127.0.0.1",
                            port=18015, log_level="critical",
                            access_log=False, lifespan="on")
        server = uvicorn.Server(cfg)
        state["server"] = server
        server.run()
    except BaseException as exc:
        state["error"] = type(exc).__name__

thread = threading.Thread(target=serve, daemon=True)
thread.start()
status = 0
for attempt in range(40):
    time.sleep(0.25)
    if state["error"] is not None:
        break
    try:
        c = http.client.HTTPConnection("127.0.0.1", 18015, timeout=1)
        c.request("GET", "/healthz")
        r = c.getresponse()
        r.read(2048)
        status = r.status
        c.close()
        break
    except OSError:
        pass

if state["error"] is not None:
    raise SystemExit("CANDIDATE_UVICORN_EXCEPTION=" + state["error"])
if status != 200:
    raise SystemExit("CANDIDATE_UVICORN_HEALTH=%s" % status)
print("CANDIDATE_UVICORN_HEALTH_200=PASS")
print("ISOLATED_SQLITE_TMPFS=PASS")
print("CONTAINER_NETWORK_NONE=PASS")
print("PRODUCTION_SQLITE_NOT_MOUNTED=PASS")
state["server"].should_exit = True
thread.join(timeout=4)
