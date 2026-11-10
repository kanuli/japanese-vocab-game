#!/usr/bin/env python3
"""Local PLaMo 3 translation bridge for the Japanese learning site.

Python standard library only. The llama.cpp model server must run separately.
This process binds to loopback by default; never expose it directly to the internet.
"""
import ipaddress
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

PATH = "/api/v1/translate/plamo"
ALLOWED_ORIGIN = "https://kanuli.github.io"
MODEL = "plamo-3-translate"
UPSTREAM = os.environ.get("PLAMO_UPSTREAM", "http://127.0.0.1:8000/v1/chat/completions")
BIND = os.environ.get("PLAMO_BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("PLAMO_BIND_PORT", "8788"))
MAX_BODY_BYTES = 10000
MAX_TEXT_CHARS = 1800
MAX_GENERATION_TOKENS = 2048
SLOTS = threading.BoundedSemaphore(2)


def validate_config():
    # The bridge may listen on an explicitly selected private LAN address,
    # but must NEVER use a wildcard or a public IP.
    ip = ipaddress.ip_address(BIND)
    if ip.is_unspecified or not (ip.is_loopback or ip.is_private):
        raise ValueError("Bind only to loopback or a specific private LAN IP")
    up = urlsplit(UPSTREAM)
    if (up.scheme != "http" or up.hostname not in ("127.0.0.1", "localhost")
            or up.username or up.password or up.query or up.fragment
            or up.path != "/v1/chat/completions"):
        raise ValueError("PLAMO_UPSTREAM must be a loopback llama-server /v1/chat/completions URL")


def call_model(text, target):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": text}],
        "chat_template_kwargs": {"source_lang": "ja", "target_lang": target},
        "temperature": 0,
        "max_tokens": MAX_GENERATION_TOKENS,
        "stop": ["<|plamo:tag|>", "<|plamo:bos|>"]
    }
    request = urllib.request.Request(
        UPSTREAM,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    # Do not route local model requests via an environment proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=80) as response:
        data = json.load(response)
    result = data["choices"][0]["message"]["content"]
    if not isinstance(result, str) or not result.strip():
        raise ValueError("Missing model translation")
    return result.strip()


class Handler(BaseHTTPRequestHandler):
    server_version = "PLaMoTranslationBridge/0.1"

    def log_message(self, fmt, *args):
        # Never log source text or translated content.
        print("%s [%s] %s" % (self.client_address[0], self.log_date_time_string(), fmt % args))

    def _cors(self):
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")

    def reply(self, status, data, preflight=False):
        encoded = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if preflight:
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "300")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        if self.path != PATH or self.headers.get("Origin") != ALLOWED_ORIGIN:
            self.reply(403, {"error": "Origin not allowed"})
            return
        self.reply(200, {"status": "ok"}, preflight=True)

    def do_GET(self):
        if self.path == "/healthz":
            self.reply(200, {"status": "ok", "model": "not_checked"})
        else:
            self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != PATH:
            self.reply(404, {"error": "Not found"})
            return
        origin = self.headers.get("Origin")
        if origin and origin != ALLOWED_ORIGIN:
            self.reply(403, {"error": "Origin not allowed"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self.reply(413, {"error": "Invalid request size"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            self.reply(415, {"error": "Expected application/json"})
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.reply(400, {"error": "Invalid JSON"})
            return
        if not isinstance(body, dict):
            self.reply(400, {"error": "Expected JSON object"})
            return
        text = body.get("text")
        target = body.get("target_lang")
        if (body.get("source_lang") != "ja" or target not in ("zh-hant", "en")
                or not isinstance(text, str) or not text.strip()
                or len(text) > MAX_TEXT_CHARS):
            self.reply(400, {"error": "Invalid translation input"})
            return
        if not SLOTS.acquire(blocking=False):
            self.reply(503, {"error": "Translator busy"})
            return
        try:
            translated = call_model(text.strip(), target)
            self.reply(200, {"translation": translated, "model": MODEL, "target_lang": target})
        except (TimeoutError, urllib.error.URLError, ValueError, KeyError, IndexError):
            self.reply(502, {"error": "PLaMo backend unavailable"})
        except Exception:
            self.reply(502, {"error": "PLaMo backend failed"})
        finally:
            SLOTS.release()


if __name__ == "__main__":
    validate_config()
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    print("PLaMo bridge listening on http://%s:%s (local/LAN only)" % (BIND, PORT))
    server.serve_forever()
