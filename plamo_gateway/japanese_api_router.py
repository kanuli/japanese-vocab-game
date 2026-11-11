"""Opt-in FastAPI route for the existing Japanese API on HTTPS 8443.

NOT active until the NAS app explicitly includes this router. No modifications
to existing GET vocabulary/audio routes. Does not contain secrets or model code.

Trust boundary:
 Browser -> existing Nginx 8443 -> Japanese FastAPI -> NAS loopback gateway
 127.0.0.1:18790 -> Windows LAN PLaMo bridge -> llama-server.

The NAS loopback gateway independently validates Supabase access tokens
and the allowlisted user UUID. This outer layer rejects malformed traffic
and adds a conservative pre-auth cap; it does NOT replace Nginx rate limiting.
"""
import asyncio
import json
import threading
import time
import urllib.error
import urllib.request
from collections import deque

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

router = APIRouter()
TRANSLATE_PATH = "/api/v1/translate/plamo"
GATEWAY_URL = "http://127.0.0.1:18790" + TRANSLATE_PATH
ALLOWED_ORIGIN = "https://kanuli.github.io"
MAX_BODY_BYTES = 8192
MAX_TEXT_LENGTH = 1800
MAX_TOKEN_LENGTH = 8192
WINDOW = 60.0
GLOBAL_PER_MINUTE = 60
CLIENT_PER_MINUTE = 30
ACTIVE_CAP = threading.BoundedSemaphore(2)
RATE_LOCK = threading.Lock()
GLOBAL_HITS = deque()
CLIENT_HITS = {}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _cors(request):
    origin = request.headers.get("origin")
    if origin == ALLOWED_ORIGIN:
        return {"Access-Control-Allow-Origin": ALLOWED_ORIGIN,
                "Vary": "Origin"}
    return {}


def _reply(request, code, message):
    headers = _cors(request)
    headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
    return JSONResponse({"error": message}, status_code=code, headers=headers)


def _allow_request(request):
    """Fail-safe pre-auth quotas. Client IP is ASGI peer, not spoofable XFF."""
    now = time.monotonic()
    peer = request.client.host if request.client else "unknown"
    with RATE_LOCK:
        while GLOBAL_HITS and GLOBAL_HITS[0] <= now - WINDOW:
            GLOBAL_HITS.popleft()
        if len(GLOBAL_HITS) >= GLOBAL_PER_MINUTE:
            return False
        hits = CLIENT_HITS.setdefault(peer, deque())
        while hits and hits[0] <= now - WINDOW:
            hits.popleft()
        if len(hits) >= CLIENT_PER_MINUTE:
            return False
        GLOBAL_HITS.append(now)
        hits.append(now)
        if len(CLIENT_HITS) > 256:
            for key, q in list(CLIENT_HITS.items()):
                if not q or q[-1] <= now - WINDOW:
                    del CLIENT_HITS[key]
    return True


def _forward(token, payload):
    request = urllib.request.Request(
        GATEWAY_URL,
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token,
            "Origin": ALLOWED_ORIGIN,
        },
    )
    try:
        with OPENER.open(request, timeout=90) as response:
            raw = response.read(8193)
            status = response.status
    except urllib.error.HTTPError as exc:
        # Gateway error payloads are fixed strings, but deliberately do not relay
        # arbitrary upstream bodies or headers to the public internet.
        return exc.code if exc.code in (400, 401, 403, 413, 429, 503) else 502, None
    if status != 200 or len(raw) > 8192:
        return 502, None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return 502, None
    if (not isinstance(data, dict) or
            not isinstance(data.get("translation"), str) or
            not data["translation"].strip()):
        return 502, None
    return 200, {
        "translation": data["translation"],
        "target_lang": data.get("target_lang"),
        "model": "plamo-3-translate",
    }


@router.options(TRANSLATE_PATH)
async def plamo_options(request: Request):
    if request.headers.get("origin") != ALLOWED_ORIGIN:
        return _reply(request, 403, "Origin denied")
    headers = _cors(request)
    headers.update({
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Max-Age": "300",
        "Cache-Control": "no-store",
    })
    return Response(status_code=204, headers=headers)


@router.post(TRANSLATE_PATH)
async def plamo_translate(request: Request):
    origin = request.headers.get("origin")
    if origin is not None and origin != ALLOWED_ORIGIN:
        return _reply(request, 403, "Origin denied")

    if not _allow_request(request):
        return _reply(request, 429, "Too many requests")

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return _reply(request, 401, "Authentication required")
    token = auth[7:]
    if (len(token) < 20 or len(token) > MAX_TOKEN_LENGTH or
            any(c.isspace() for c in token)):
        return _reply(request, 401, "Invalid authorization")

    if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        return _reply(request, 415, "Expected application/json")
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        return _reply(request, 413, "Invalid length")
    # Require Content-Length to prevent streaming oversized payloads to API.
    if not 1 <= declared <= MAX_BODY_BYTES:
        return _reply(request, 413, "Invalid request length")

    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY_BYTES:
            return _reply(request, 413, "Request too large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return _reply(request, 400, "Invalid JSON")
    if not isinstance(payload, dict):
        return _reply(request, 400, "Invalid request")
    text = payload.get("text")
    if (payload.get("source_lang") != "ja" or
            payload.get("target_lang") not in ("zh-hant", "en") or
            not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH):
        return _reply(request, 400, "Invalid translation input")

    if not ACTIVE_CAP.acquire(blocking=False):
        return _reply(request, 503, "Translator busy")
    try:
        loop = asyncio.get_running_loop()
        status, result = await loop.run_in_executor(None, _forward, token, {
            "source_lang": "ja",
            "target_lang": payload["target_lang"],
            "text": text.strip(),
        })
    except Exception:
        return _reply(request, 502, "Gateway unavailable")
    finally:
        ACTIVE_CAP.release()

    if status != 200:
        return _reply(request, status, {
            401: "Authentication failed",
            403: "User not authorized",
            429: "Translation quota exceeded",
            503: "Gateway busy",
        }.get(status, "Gateway unavailable"))

    headers = _cors(request)
    headers.update({"Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff"})
    return JSONResponse(result, headers=headers)
