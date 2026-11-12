#!/bin/sh
# STEP 9AI — Recover only a STALE UDS-only shadow Gateway and relaunch
# detached from SSH. Never stop/restart the live TCP Gateway or Docker.
set -eu
umask 077

STAGE="$HOME/plamo-gateway-staging"
CONFIG="$HOME/.config/plamo-gateway/config.env"
ROOT="$HOME/plamo-gateway-run"
SOCK="$ROOT/gateway.sock"
PIDFILE="$ROOT/shadow.pid"
LOG="$ROOT/shadow.log"

echo "=== STEP 9AI: REPAIR DETACHED UDS SHADOW ==="
test -f "$STAGE/gateway_uds_candidate.py"
test -f "$CONFIG" && test -r "$CONFIG" && test ! -L "$CONFIG"
test -d "$ROOT" && test ! -L "$ROOT"
chmod 700 "$ROOT"
python3 -m py_compile "$STAGE/gateway_uds_candidate.py"
echo "STAGED_CANDIDATE=PASS"

python3 - <<'PY'
import http.client
connection = http.client.HTTPConnection("127.0.0.1", 18790, timeout=4)
connection.request("GET", "/healthz")
response = connection.getresponse()
response.read()
connection.close()
if response.status != 200:
    raise SystemExit("ORIGINAL_GATEWAY_HEALTH=FAIL")
print("ORIGINAL_GATEWAY_HEALTH=200")
PY

# This inspection/cleanup never signals a running PID. Refuse to overwrite
# a socket that is healthy or may belong to a currently running process.
python3 - "$ROOT" <<'PY'
import os
import socket
import stat
import sys

root = sys.argv[1]
sockpath = os.path.join(root, "gateway.sock")
pidpath = os.path.join(root, "shadow.pid")

def healthy(path):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect(path)
        s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        data = s.recv(1024)
        return b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data
    except (OSError, ValueError):
        return False
    finally:
        s.close()

def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

if os.path.lexists(sockpath):
    if os.path.islink(sockpath) or not stat.S_ISSOCK(os.lstat(sockpath).st_mode):
        raise SystemExit("SHADOW_SOCKET_UNEXPECTED_FILE=STOP")
    if healthy(sockpath):
        print("SHADOW_SOCKET_ALREADY_HEALTHY=PASS")
        raise SystemExit(0)

if os.path.lexists(pidpath):
    if os.path.islink(pidpath) or not stat.S_ISREG(os.lstat(pidpath).st_mode):
        raise SystemExit("PIDFILE_UNEXPECTED=STOP")
    data = open(pidpath, "r").read().strip()
    if not data.isdigit() or int(data) <= 1:
        raise SystemExit("PIDFILE_INVALID=STOP")
    if alive(int(data)):
        raise SystemExit("SHADOW_PID_STILL_ALIVE_SOCKET_NOT_HEALTHY=STOP")
    os.unlink(pidpath)
    print("STALE_PID_REMOVED=PASS")

if os.path.lexists(sockpath):
    os.unlink(sockpath)
    print("STALE_SOCKET_REMOVED=PASS")
else:
    print("NO_STALE_SOCKET=PASS")
PY

# If the socket is already healthy, do not launch another shadow process.
if python3 - "$SOCK" <<'PY'
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(sys.argv[1])
    s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    data = s.recv(1024)
    if b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data:
        print("UDS_SHADOW_ALREADY_RUNNING=PASS")
        sys.exit(0)
except OSError:
    pass
finally:
    s.close()
sys.exit(1)
PY
then
    echo "SHADOW_RESTART_NEEDED=NO"
else
    # nohup + fully redirected file descriptors survive an interactive SSH
    # session's SIGHUP. The child sources the existing private env file.
    nohup sh -c '
        set -eu
        set -a
        . "$1"
        set +a
        : "${PLAMO_SUPABASE_URL:?}"
        : "${PLAMO_SUPABASE_PUBLISHABLE_KEY:?}"
        : "${PLAMO_ALLOWED_USER_IDS:?}"
        export PLAMO_UNIX_ONLY=1
        export PLAMO_UNIX_SOCKET="$2"
        exec python3 "$3"
    ' sh "$CONFIG" "$SOCK" "$STAGE/gateway_uds_candidate.py" \
      >"$LOG" 2>&1 </dev/null &
    pid=$!
    printf '%s\n' "$pid" > "$PIDFILE"
    ready=0
    for n in 1 2 3 4 5 6 7 8; do
        if ! kill -0 "$pid" 2>/dev/null; then break; fi
        if [ -S "$SOCK" ]; then
            if python3 - "$SOCK" <<'PY'
import socket, sys
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(sys.argv[1])
    s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    data=s.recv(1024)
    assert b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data
finally:
    s.close()
PY
            then
                ready=1
                break
            fi
        fi
        sleep 1
    done
    if [ "$ready" -ne 1 ]; then
        # Terminate ONLY the PID created by this invocation.
        kill "$pid" 2>/dev/null || true
        echo "SHADOW_START=FAIL"
        exit 4
    fi
    echo "SHADOW_STARTED_DETACHED=PASS"
fi

python3 - <<'PY'
import http.client
connection = http.client.HTTPConnection("127.0.0.1", 18790, timeout=4)
connection.request("GET", "/healthz")
response = connection.getresponse()
response.read()
connection.close()
if response.status != 200:
    raise SystemExit("ORIGINAL_GATEWAY_AFTER=FAIL")
print("ORIGINAL_GATEWAY_AFTER=200")
PY
echo "PRODUCTION_API_MODIFIED=NO"
echo "PRODUCTION_API_RESTARTED=NO"
echo "EXISTING_GATEWAY_RESTARTED=NO"
echo "STEP_9AI_START=PASS"
