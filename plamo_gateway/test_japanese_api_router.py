"""HTTP contract tests for the opt-in 8443 Japanese API PLaMo router.

Requires FastAPI + Starlette + compatible httpx, as present in existing
Japanese API container. Uses mock gateway: no real Supabase/token/GPU calls.
"""
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

import japanese_api_router as router_module

PAYLOAD = {"source_lang": "ja", "target_lang": "zh-hant",
           "text": "大学教授は研究を行う。"}


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        router_module.GLOBAL_HITS.clear()
        router_module.CLIENT_HITS.clear()
        app = FastAPI()
        app.include_router(router_module.router)
        self.client = TestClient(app)
        self.url = router_module.TRANSLATE_PATH

    def post(self, token=None, origin="https://kanuli.github.io", data=None):
        headers = {"content-type": "application/json", "Origin": origin}
        if token is not None:
            headers["authorization"] = "Bearer " + token
        return self.client.post(self.url, json=data or PAYLOAD, headers=headers)

    def test_missing_token_rejected(self):
        self.assertEqual(self.post().status_code, 401)

    def test_invalid_origin_rejected(self):
        self.assertEqual(self.post(origin="https://other.example").status_code, 403)

    def test_bad_target_rejected_without_gpu(self):
        bad = dict(PAYLOAD, target_lang="zh-hans")
        with patch.object(router_module, "_forward") as forward:
            self.assertEqual(self.post(token="t" * 30, data=bad).status_code, 400)
            forward.assert_not_called()

    def test_valid_request_forwarded(self):
        with patch.object(router_module, "_forward",
                          return_value=(200, {"translation": "大學教授進行研究。",
                                              "target_lang": "zh-hant",
                                              "model": "plamo-3-translate"})) as forward:
            response = self.post(token="x" * 30)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["target_lang"], "zh-hant")
        self.assertEqual(response.headers.get("access-control-allow-origin"),
                         "https://kanuli.github.io")
        forward.assert_called_once()

    def test_invalid_token_downstream_rejected(self):
        with patch.object(router_module, "_forward", return_value=(401, None)):
            response = self.post(token="x" * 30)
        self.assertEqual(response.status_code, 401)

    def test_allowed_preflight(self):
        response = self.client.options(
            self.url,
            headers={"origin": "https://kanuli.github.io",
                     "access-control-request-method": "POST",
                     "access-control-request-headers": "authorization,content-type"})
        self.assertEqual(response.status_code, 204)
        self.assertIn("Authorization", response.headers["access-control-allow-headers"])

    def test_disallowed_preflight(self):
        response = self.client.options(self.url, headers={"origin": "https://other.example"})
        self.assertEqual(response.status_code, 403)

    def test_preauth_throttle(self):
        with patch.object(router_module, "_allow_request", return_value=False):
            response = self.post(token="x" * 30)
        self.assertEqual(response.status_code, 429)

    def test_model_busy(self):
        with patch.object(router_module.ACTIVE_CAP, "acquire", return_value=False):
            response = self.post(token="x" * 30)
        self.assertEqual(response.status_code, 503)

    def test_client_limit_in_memory(self):
        class Dummy:
            class Peer:
                host = "192.0.2.99"
            client = Peer()
        obj = Dummy()
        for i in range(router_module.CLIENT_PER_MINUTE):
            self.assertTrue(router_module._allow_request(obj))
        self.assertFalse(router_module._allow_request(obj))


if __name__ == "__main__":
    unittest.main()
