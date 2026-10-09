"""Synthetic public health readbacks; no network or health-state writes."""
import copy
import io
import json
from pathlib import Path
import sys
import unittest
import urllib.error
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_published_health_status as verifier

EXPECTED = {"version": 3, "status": "ok", "runId": 901, "checkedAt": "SYNTHETIC-TIME",
            "auditedSha": "b" * 40, "liveSha": "b" * 40, "deploymentAligned": True,
            "checks": {"liveBrowser": True, "revisionStillCurrent": True}}
COMMIT = "a" * 40


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, limit): return json.dumps(self.payload).encode()


class HealthCommitTests(unittest.TestCase):
    def test_exact_commit_and_entire_payload_are_verified_without_mutation(self):
        before = copy.deepcopy(EXPECTED)
        with patch.object(verifier.urllib.request, "urlopen", return_value=Response(EXPECTED)) as http:
            self.assertEqual(verifier.verify_commit(COMMIT, EXPECTED, 901), EXPECTED)
        self.assertEqual(EXPECTED, before)
        request = http.call_args.args[0]
        self.assertIn("/" + COMMIT + "/maintenance-status.json", request.full_url)
        self.assertNotIn("/health-status/", request.full_url)
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(http.call_args.kwargs["timeout"], 10)

    def test_old_run_successful_http_is_rejected_without_blind_retry(self):
        old = {**EXPECTED, "runId": 900}
        with patch.object(verifier.urllib.request, "urlopen", return_value=Response(old)) as http:
            with self.assertRaisesRegex(ValueError, "payload-mismatch"):
                verifier.verify_commit(COMMIT, EXPECTED, 901)
        http.assert_called_once()

    def test_matching_run_cannot_hide_different_sha_failed_check_or_changed_clock(self):
        for key, value in (("liveSha", "c" * 40), ("checks", {"liveBrowser": False}),
                           ("deploymentAligned", False), ("checkedAt", "OTHER"), ("status", "error")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                verifier.verify_payload(EXPECTED, {**EXPECTED, key: value}, 901)

    def test_extra_or_missing_fields_cannot_be_shape_only_success(self):
        for actual in ({**EXPECTED, "other": True}, {k: v for k, v in EXPECTED.items() if k != "checks"}):
            with self.assertRaises(ValueError): verifier.verify_payload(EXPECTED, actual, 901)

    def test_boolean_run_id_is_not_an_integer_proof(self):
        with self.assertRaises(ValueError): verifier.verify_payload({**EXPECTED, "runId": True}, {**EXPECTED, "runId": True}, 1)
        with self.assertRaises(ValueError): verifier.verify_commit(COMMIT, EXPECTED, True)

    def test_untrusted_commit_path_or_repository_injection_never_fetches(self):
        for commit in ("main", "health-status", "../main", "https://example.test/", "a" * 39, "A" * 40, None):
            with self.subTest(commit=commit), patch.object(verifier.urllib.request, "urlopen") as http:
                with self.assertRaises(ValueError): verifier.verify_commit(commit, EXPECTED, 901)
                http.assert_not_called()

    def test_transient_5xx_retry_is_bounded_and_can_recover(self):
        error = urllib.error.HTTPError("SYNTHETIC", 503, "PRIVATE-BODY", {}, io.BytesIO())
        with patch.object(verifier.urllib.request, "urlopen", side_effect=[error, Response(EXPECTED)]) as http, \
             patch.object(verifier.time, "sleep") as sleep:
            self.assertEqual(verifier.verify_commit(COMMIT, EXPECTED, 901), EXPECTED)
        self.assertEqual(http.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_persistent_transport_failure_stops_after_three_reads(self):
        with patch.object(verifier.urllib.request, "urlopen", side_effect=TimeoutError("PRIVATE-TOKEN")) as http, \
             patch.object(verifier.time, "sleep") as sleep:
            with self.assertRaisesRegex(ValueError, "transport-failed") as error:
                verifier.verify_commit(COMMIT, EXPECTED, 901)
        self.assertNotIn("PRIVATE", str(error.exception))
        self.assertEqual(http.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_semantic_or_4xx_failures_are_not_retried_or_reported_healthy(self):
        for code in (401, 403, 404, 429):
            error = urllib.error.HTTPError("SYNTHETIC", code, "PRIVATE-BODY", {}, io.BytesIO())
            with self.subTest(code=code), patch.object(verifier.urllib.request, "urlopen", side_effect=error) as http, \
                 patch.object(verifier.time, "sleep") as sleep:
                with self.assertRaisesRegex(ValueError, "http-failed") as caught:
                    verifier.verify_commit(COMMIT, EXPECTED, 901)
                self.assertNotIn("PRIVATE", str(caught.exception))
                http.assert_called_once(); sleep.assert_not_called()

    def test_exact_failed_health_record_is_not_relabelled_as_ok(self):
        failed = {**EXPECTED, "status": "error", "deploymentAligned": False}
        with patch.object(verifier.urllib.request, "urlopen", return_value=Response(failed)):
            self.assertEqual(verifier.verify_commit(COMMIT, failed, 901)["status"], "error")


if __name__ == "__main__":
    unittest.main()
