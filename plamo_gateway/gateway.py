#!/usr/bin/env python3
"""PLaMo NAS gateway: loopback-only, Supabase-authenticated, rate-limited.

Python >=3.8 standard library. This is intentionally NOT a standalone
internet-facing HTTPS service. HTTPS reverse proxy setup is a separate gate.
Never log the request body, source text, translation, or access token.
"""
import collections
import ipaddress
import json
import os
import re
import socketserver
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ORIGIN = "https://kanuli.github.io"
PATH = "/api/v1/translate/plamo"
UPSTREAM = "http://192.168.1.13:18789" + PATH
PORT = int(os.environ.get("PLAMO_GATEWAY_PORT", "18790"))
UNIX_SOCKET = os.environ.get("PLAMO_UNIX_SOCKET", "").strip()
UNIX_ONLY = os.environ.get("PLAMO_UNIX_ONLY", "") == "1"
SUPABASE_URL = os.environ.get("PLAMO_SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("PLAMO_SUPABASE_PUBLISHABLE_KEY", "")
ALLOWED_USERS = set(filter(None, (s.strip() for s in os.environ.get("PLAMO_ALLOWED_USER_IDS", "").split(","))))
WINDOW_SECONDS = 900
MAX_REQUESTS_PER_USER = 30
MAX_REQUEST_BODY = 8192
MAX_TEXT_LENGTH = 1800
SLOTS = threading.BoundedSemaphore(2)
COUNTERS = {}
LOCK = threading.Lock()
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def verify_config():
    host = urlsplit(SUPABASE_URL)
    if (host.scheme != "https" or not host.hostname or
        not re.fullmatch(r"[a-z0-9-]+\.supabase\.co", host.hostname) or
        host.path or host.query or host.fragment or host.username or host.password):
        raise ValueError("PLAMO_SUPABASE_URL must be an exact https://PROJECT.supabase.co URL")
    if not SUPABASE_KEY or len(SUPABASE_KEY) > 512 or any(c.isspace() for c in SUPABASE_KEY):
        raise ValueError("PLAMO_SUPABASE_PUBLISHABLE_KEY required")
    if not ALLOWED_USERS or any(not re.fullmatch(r"[0-9a-fA-F-]{36}", uid) for uid in ALLOWED_USERS):
        raise ValueError("PLAMO_ALLOWED_USER_IDS must contain allowed Supabase UUID(s)")
    if PORT < 1024 or PORT > 65535:
        raise ValueError("Invalid gateway port")
    if UNIX_ONLY and not UNIX_SOCKET:
        raise ValueError("PLAMO_UNIX_ONLY requires PLAMO_UNIX_SOCKET")
    if UNIX_SOCKET:
        approved = os.path.join(os.path.expanduser("~"), "plamo-gateway-run", "gateway.sock")
        if not os.path.isabs(UNIX_SOCKET) or UNIX_SOCKET != approved:
            raise ValueError("PLAMO_UNIX_SOCKET must be the private gateway home socket")
        parent = os.path.dirname(UNIX_SOCKET)
        if not os.path.isdir(parent) or os.path.islink(parent):
            raise ValueError("Create the private socket directory first")
        # Never unlink an existing socket automatically; it might belong
        # to a still-running Gateway. Clean up only after verifying shutdown.
        if os.path.lexists(UNIX_SOCKET):
            raise ValueError("Existing Unix socket; inspect before restarting")


def supabase_user(token):
    if not token or len(token) > 8192 or any(c.isspace() for c in token):
        raise ValueError("Invalid access token")
    request = urllib.request.Request(
        SUPABASE_URL + "/auth/v1/user",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + token,
            "Accept": "application/json"
        }, method="GET"
    )
    # Supabase performs signature, expiration, revocation, and user checks;
    # do not trust an unverified browser-decoded JWT or user ID.
    with NO_PROXY.open(request, timeout=10) as response:
        data = json.load(response)
    uid = data.get("id") if isinstance(data, dict) else None
    if not isinstance(uid, str) or uid not in ALLOWED_USERS:
        raise PermissionError("User is not allowed")
    return uid


def rate_allowed(uid):
    now = time.monotonic()
    with LOCK:
        current = COUNTERS.get(uid)
        if current is None or now >= current[0] + WINDOW_SECONDS:
            current = (now, 0)
        if current[1] >= MAX_REQUESTS_PER_USER:
            return False
        COUNTERS[uid] = (current[0], current[1] + 1)
        # Avoid unbounded memory growth if allowed users expand.
        if len(COUNTERS) > 500:
            for key, value in list(COUNTERS.items()):
                if now >= value[0] + WINDOW_SECONDS:
                    del COUNTERS[key]
        return True


def translate(text, target):
    data = json.dumps({
        "text": text,
        "source_lang": "ja",
        "target_lang": target
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        UPSTREAM, data=data, method="POST",
        headers={"Content-Type": "application/json"}
    )
    with NO_PROXY.open(request, timeout=85) as response:
        result = json.load(response)
    value = result.get("translation") if isinstance(result, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Invalid upstream translation")
    return value.strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "PLaMoNASGateway/0.1"

    def log_message(self, fmt, *args):
        # Log only the method and response status (never query strings or bodies).
        pass

    def reply(self, status, data, cors=True, preflight=False):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if cors and self.headers.get("Origin") == ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ORIGIN)
            self.send_header("Vary", "Origin")
            if preflight:
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Max-Age", "300")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/healthz":
            self.reply(200, {"status": "ok", "model": "not_checked"}, cors=False)
        else:
            self.reply(404, {"error": "Not found"}, cors=False)

    def do_OPTIONS(self):
        if self.path != PATH or self.headers.get("Origin") != ORIGIN:
            return self.reply(403, {"error": "Origin denied"}, cors=False)
        return self.reply(200, {"status": "ok"}, preflight=True)

    def do_POST(self):
        if self.path != PATH:
            return self.reply(404, {"error": "Not found"}, cors=False)
        origin = self.headers.get("Origin")
        if origin and origin != ORIGIN:
            return self.reply(403, {"error": "Origin denied"}, cors=False)
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return self.reply(401, {"error": "Authentication required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 1 or length > MAX_REQUEST_BODY:
            return self.reply(413, {"error": "Invalid request length"})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.reply(415, {"error": "Expected application/json"})
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.reply(400, {"error": "Invalid JSON"})
        if not isinstance(request, dict):
            return self.reply(400, {"error": "Invalid JSON object"})
        text, target = request.get("text"), request.get("target_lang")
        if (request.get("source_lang") != "ja" or target not in ("zh-hant", "en") or
            not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH):
            return self.reply(400, {"error": "Invalid translation input"})
        try:
            uid = supabase_user(auth[7:])
        except urllib.error.HTTPError:
            return self.reply(401, {"error": "Authentication failed"})
        except PermissionError:
            return self.reply(403, {"error": "User not authorized"})
        except ValueError:
            return self.reply(401, {"error": "Invalid authorization"})
        except Exception:
            return self.reply(503, {"error": "Authentication unavailable"})
        if not rate_allowed(uid):
            return self.reply(429, {"error": "Translation quota exceeded"})
        if not SLOTS.acquire(blocking=False):
            return self.reply(503, {"error": "Translator busy"})
        try:
            translated = translate(text.strip(), target)
            self.reply(200, {"translation": translated, "model": "plamo-3-translate", "target_lang": target})
        except Exception:
            self.reply(502, {"error": "PLaMo model unavailable"})
        finally:
            SLOTS.release()


class ThreadingUnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


def run_gateway():
    verify_config()
    unix_server = None
    if UNIX_SOCKET:
        unix_server = ThreadingUnixHTTPServer(UNIX_SOCKET, Handler)
        os.chmod(UNIX_SOCKET, 0o600)
        print("PLaMo Gateway UDS: enabled", flush=True)

    if UNIX_ONLY:
        # Keep existing live 127.0.0.1:18790 Gateway completely untouched.
        try:
            unix_server.serve_forever()
        finally:
            unix_server.server_close()
        return

    if unix_server is not None:
        threading.Thread(target=unix_server.serve_forever, daemon=True).start()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        print("PLaMo gateway (loopback only): 127.0.0.1:%s" % PORT, flush=True)
        server.serve_forever()
    finally:
        if unix_server is not None:
            unix_server.shutdown()
            unix_server.server_close()


if __name__ == "__main__":
    run_gateway()
