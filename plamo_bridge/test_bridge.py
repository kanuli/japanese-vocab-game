"""Offline contract tests for the PLaMo bridge. No model or network needed."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import bridge


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), bridge.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.root = "http://127.0.0.1:%s" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, path, method="POST", payload=None, origin="https://kanuli.github.io", raw=None):
        body = raw if raw is not None else json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if origin is not None:
            headers["Origin"] = origin
        req = Request(self.root + path,
                      data=body if method == "POST" else None,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=4) as response:
                return response.status, dict(response.headers), json.load(response)
        except HTTPError as e:
            return e.code, dict(e.headers), json.load(e)

    def test_translation_contract_chinese(self):
        with patch.object(bridge, "call_model", return_value="大學教授也要培育學生。") as model:
            status, headers, obj = self.request(bridge.PATH, payload={
                "source_lang": "ja", "target_lang": "zh-hant", "text": "学生を育てる。"
            })
        self.assertEqual(status, 200)
        self.assertEqual(obj["translation"], "大學教授也要培育學生。")
        self.assertEqual(headers["Access-Control-Allow-Origin"], bridge.ALLOWED_ORIGIN)
        model.assert_called_once_with("学生を育てる。", "zh-hant")

    def test_translation_contract_english(self):
        with patch.object(bridge, "call_model", return_value="The meeting is on Monday."):
            status, _, obj = self.request(bridge.PATH, payload={
                "source_lang": "ja", "target_lang": "en", "text": "会議は月曜日です。"
            })
        self.assertEqual(status, 200)
        self.assertEqual(obj["target_lang"], "en")

    def test_reject_untrusted_origin(self):
        with patch.object(bridge, "call_model") as model:
            status, _, _ = self.request(bridge.PATH, origin="https://evil.example",
                payload={"source_lang": "ja", "target_lang": "en", "text": "こんにちは"})
        self.assertEqual(status, 403)
        model.assert_not_called()

    def test_reject_invalid_language(self):
        with patch.object(bridge, "call_model") as model:
            status, _, _ = self.request(bridge.PATH, payload={
                "source_lang": "ja", "target_lang": "zh-hans", "text": "こんにちは"})
        self.assertEqual(status, 400)
        model.assert_not_called()

    def test_reject_oversized_text(self):
        status, _, _ = self.request(bridge.PATH, payload={
            "source_lang": "ja", "target_lang": "en", "text": "あ" * 1801})
        self.assertEqual(status, 400)

    def test_cors_preflight(self):
        status, headers, _ = self.request(bridge.PATH, method="OPTIONS")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], bridge.ALLOWED_ORIGIN)

    def test_health_does_not_claim_model_ready(self):
        req = Request(self.root + "/healthz", method="GET")
        with urlopen(req, timeout=4) as response:
            obj = json.load(response)
        self.assertEqual(obj, {"status": "ok", "model": "not_checked"})


if __name__ == "__main__":
    unittest.main()
