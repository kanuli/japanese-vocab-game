"""Offline ASGI contract tests for opt-in 8443 PLaMo route.

Uses only FastAPI, Starlette and the Python standard library (NO httpx).
Mocks the downstream Gateway. No NAS, Supabase or GPU requests are issued.
"""
import asyncio
import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import japanese_api_router as router_module

ORIGIN = "https://kanuli.github.io"
BODY = {"source_lang": "ja", "target_lang": "zh-hant", "text": "大学教授は研究を行う。"}


def build_app():
    app = FastAPI()
    # This must match the planned production CORS allow_methods change.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGIN],
        allow_methods=["GET", "HEAD", "OPTIONS", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router_module.router)
    return app


async def asgi_request(app, method="POST", path=router_module.TRANSLATE_PATH,
                       headers=None, data=None):
    headers = dict(headers or {})
    body = b""
    if method == "POST":
        body = json.dumps(BODY if data is None else data,
                          ensure_ascii=False).encode("utf-8")
        headers.setdefault("content-type", "application/json")
        headers["content-length"] = str(len(body))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": method, "scheme": "https",
        "path": path, "raw_path": path.encode("ascii"), "root_path": "",
        "query_string": b"",
        "headers": [(str(k).lower().encode("latin1"), str(v).encode("latin1"))
                    for k, v in headers.items()],
        "client": ("192.0.2.55", 54000),
        "server": ("testserver", 443),
    }
    received = False
    output = []

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        output.append(message)

    await app(scope, receive, send)
    starts = [m for m in output if m.get("type") == "http.response.start"]
    if len(starts) != 1:
        raise AssertionError("Expected exactly one ASGI HTTP response")
    response = starts[0]
    response_headers = {k.decode("latin1"): v.decode("latin1")
                        for k, v in response["headers"]}
    response_body = b"".join(m.get("body", b"") for m in output
                             if m.get("type") == "http.response.body")
    try:
        payload = json.loads(response_body.decode("utf-8"))
    except (ValueError, UnicodeError):
        payload = {}
    return response["status"], response_headers, payload


class RouterTests(unittest.TestCase):
    def setUp(self):
        router_module.GLOBAL_HITS.clear()
        router_module.CLIENT_HITS.clear()
        self.app = build_app()

    def request(self, token=None, origin=ORIGIN, data=None, method="POST"):
        headers = {"origin": origin}
        if token is not None:
            headers["authorization"] = "Bearer " + token
        if method == "OPTIONS":
            headers["access-control-request-method"] = "POST"
            headers["access-control-request-headers"] = "authorization,content-type"
        return asyncio.run(asgi_request(self.app, method=method, headers=headers, data=data))

    def test_no_token(self):
        self.assertEqual(self.request()[0], 401)

    def test_invalid_origin(self):
        self.assertEqual(self.request(origin="https://evil.example")[0], 403)

    def test_bad_language(self):
        with patch.object(router_module, "_forward") as forward:
            bad = dict(BODY, target_lang="zh-hans")
            self.assertEqual(self.request(token="x" * 30, data=bad)[0], 400)
            forward.assert_not_called()

    def test_valid_translation(self):
        answer = {"translation": "大學教授進行研究。", "target_lang": "zh-hant",
                  "model": "plamo-3-translate"}
        with patch.object(router_module, "_forward", return_value=(200, answer)) as forward:
            code, headers, body = self.request(token="x" * 30)
        self.assertEqual(code, 200)
        self.assertEqual(body, answer)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        forward.assert_called_once()

    def test_gateway_auth_denial(self):
        with patch.object(router_module, "_forward", return_value=(401, None)):
            self.assertEqual(self.request(token="x" * 30)[0], 401)

    def test_cors_preflight_allows_post(self):
        status, headers, _ = self.request(method="OPTIONS")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        self.assertIn("POST", headers.get("access-control-allow-methods", ""))

    def test_cors_preflight_invalid_origin(self):
        code, _, _ = self.request(method="OPTIONS", origin="https://evil.example")
        self.assertEqual(code, 400)  # Starlette middleware refuses disallowed Origin.

    def test_preauth_rate_limit(self):
        with patch.object(router_module, "_allow_request", return_value=False):
            self.assertEqual(self.request(token="x" * 30)[0], 429)

    def test_concurrency_cap(self):
        with patch.object(router_module.ACTIVE_CAP, "acquire", return_value=False):
            self.assertEqual(self.request(token="x" * 30)[0], 503)

    def test_peer_quota(self):
        class Peer:
            host = "192.0.2.55"
        class Request:
            client = Peer()
        obj = Request()
        for _ in range(router_module.CLIENT_PER_MINUTE):
            self.assertTrue(router_module._allow_request(obj))
        self.assertFalse(router_module._allow_request(obj))


if __name__ == "__main__":
    unittest.main()
