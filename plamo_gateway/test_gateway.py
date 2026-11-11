"""Offline HTTP contract tests. No Supabase, PLaMo, NAS proxy, or model needed."""
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import gateway


class GatewayHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:%d" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method="POST", path=gateway.PATH, data=None, auth="Bearer test-token", origin=gateway.ORIGIN):
        headers = {"Content-Type": "application/json"}
        if auth is not None:
            headers["Authorization"] = auth
        if origin is not None:
            headers["Origin"] = origin
        body = json.dumps(data if data is not None else {
            "text": "こんにちは", "source_lang": "ja", "target_lang": "zh-hant"
        }, ensure_ascii=False).encode("utf-8") if method == "POST" else None
        req = Request(self.url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as r:
                return r.status, r.headers, json.load(r)
        except HTTPError as e:
            return e.code, e.headers, json.load(e)

    def test_zh_hant(self):
        with patch.object(gateway, "supabase_user", return_value="test-user") as auth:
            with patch.object(gateway, "rate_allowed", return_value=True):
                with patch.object(gateway, "translate", return_value="大學教授也必須培育學生。") as model:
                    status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body["translation"], "大學教授也必須培育學生。")
        self.assertEqual(headers["Access-Control-Allow-Origin"], gateway.ORIGIN)
        auth.assert_called_once_with("test-token")
        model.assert_called_once_with("こんにちは", "zh-hant")

    def test_english(self):
        data = {"text": "こんにちは", "source_lang": "ja", "target_lang": "en"}
        with patch.object(gateway, "supabase_user", return_value="test-user"):
            with patch.object(gateway, "rate_allowed", return_value=True):
                with patch.object(gateway, "translate", return_value="Hello."):
                    code, _, body = self.request(data=data)
        self.assertEqual(code, 200)
        self.assertEqual(body["target_lang"], "en")

    def test_no_token(self):
        with patch.object(gateway, "translate") as model:
            code, _, _ = self.request(auth=None)
        self.assertEqual(code, 401)
        model.assert_not_called()

    def test_untrusted_origin(self):
        with patch.object(gateway, "translate") as model:
            code, _, _ = self.request(origin="https://untrusted.example")
        self.assertEqual(code, 403)
        model.assert_not_called()

    def test_forbidden_user(self):
        with patch.object(gateway, "supabase_user", side_effect=PermissionError):
            code, _, _ = self.request()
        self.assertEqual(code, 403)

    def test_wrong_language(self):
        data = {"text": "こんにちは", "source_lang": "ja", "target_lang": "zh-hans"}
        with patch.object(gateway, "supabase_user") as auth:
            code, _, _ = self.request(data=data)
        self.assertEqual(code, 400)
        auth.assert_not_called()

    def test_rate_limit(self):
        with patch.object(gateway, "supabase_user", return_value="test-user"):
            with patch.object(gateway, "rate_allowed", return_value=False):
                code, _, _ = self.request()
        self.assertEqual(code, 429)

    def test_cors_preflight(self):
        code, headers, _ = self.request(method="OPTIONS", auth=None)
        self.assertEqual(code, 200)
        self.assertIn("Authorization", headers["Access-Control-Allow-Headers"])

    def test_health_is_not_model_ready(self):
        code, _, body = self.request(method="GET", path="/healthz", auth=None)
        self.assertEqual(code, 200)
        self.assertEqual(body["model"], "not_checked")

    def test_config_fails_closed(self):
        with patch.object(gateway, "SUPABASE_URL", ""):
            with self.assertRaises(ValueError):
                gateway.verify_config()


if __name__ == "__main__":
    unittest.main()
