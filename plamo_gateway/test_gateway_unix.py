"""Offline tests for opt-in NAS PLaMo Gateway Unix-domain socket listener.

Python >=3.8 stdlib only. Never calls Supabase, model or external network.
No production ports, files, or processes are touched.
"""
import http.client
import json
import os
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch

import gateway_uds_candidate as gateway


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, pathname):
        super().__init__("localhost", timeout=5)
        self.pathname = pathname

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.pathname)


class UnixGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="plamo-uds-test-")
        cls.pathname = os.path.join(cls.directory.name, "gateway.sock")
        cls.server = gateway.ThreadingUnixHTTPServer(cls.pathname, gateway.Handler)
        os.chmod(cls.pathname, 0o600)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.directory.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = UnixConnection(self.pathname)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            content = response.read()
            headers_out = dict(response.getheaders())
            return response.status, headers_out, json.loads(content.decode("utf-8"))
        finally:
            connection.close()

    def test_socket_restricted_permissions(self):
        self.assertEqual(os.stat(self.pathname).st_mode & 0o777, 0o600)

    def test_healthz(self):
        code, headers, data = self.request("GET", "/healthz")
        self.assertEqual(code, 200)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_nonexistent_path(self):
        self.assertEqual(self.request("GET", "/missing")[0], 404)

    def test_no_token(self):
        self.assertEqual(self.request("POST", gateway.PATH)[0], 401)

    def test_wrong_origin(self):
        status = self.request("POST", gateway.PATH,
                              headers={"Origin": "https://malicious.example"})[0]
        self.assertEqual(status, 403)

    def test_allowed_preflight(self):
        status, headers, data = self.request(
            "OPTIONS", gateway.PATH,
            headers={"Origin": gateway.ORIGIN})
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Access-Control-Allow-Origin"), gateway.ORIGIN)
        self.assertIn("POST", headers.get("Access-Control-Allow-Methods", ""))

    def test_mocked_authenticated_translation(self):
        payload = json.dumps({
            "source_lang": "ja", "target_lang": "zh-hant",
            "text": "大学教授は研究を行う。"
        }, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + "x" * 40,
            "Origin": gateway.ORIGIN,
            "Content-Type": "application/json",
        }
        # The real Supabase check and model invocation are exercised separately
        # in the existing live Gateway QA, not in this offline transport test.
        with patch.object(gateway, "supabase_user", return_value="test-uid"), \
             patch.object(gateway, "rate_allowed", return_value=True), \
             patch.object(gateway, "translate", return_value="大學教授進行研究。"):
            status, response_headers, data = self.request(
                "POST", gateway.PATH, body=payload, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(data.get("translation"), "大學教授進行研究。")
        self.assertEqual(response_headers.get("Access-Control-Allow-Origin"), gateway.ORIGIN)


if __name__ == "__main__":
    unittest.main()
