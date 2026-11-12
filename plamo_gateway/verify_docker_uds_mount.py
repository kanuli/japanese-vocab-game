#!/usr/bin/env python3
"""STEP 9AF: prove NAS-host-to-production-image Unix socket bind-mount.

Runs an offline mock UDS server in a temporary user directory and connects
using the REAL japanese_api_router._forward code in the EXISTING production
Docker image. No production processes, ports, config or stored secrets change.

Python 3.8+ stdlib on NAS. Requires interactive sudo permission for Docker.
"""
import http.server
import json
import os
from pathlib import Path
import socketserver
import subprocess
import tempfile
import threading


ROOT = Path(__file__).resolve().parent
DOCKER = "/usr/local/bin/docker"
SOCKET_NAME = "gateway.sock"
TRANSLATE_PATH = "/api/v1/translate/plamo"


class UnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class FakeGateway(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            valid = (
                self.path == TRANSLATE_PATH
                and self.headers.get("Authorization") == "Bearer offline-9af-test-token"
                and self.headers.get("Origin") == "https://kanuli.github.io"
                and payload.get("source_lang") == "ja"
                and payload.get("target_lang") == "zh-hant"
                and payload.get("text") == "大学教授は研究を行う。"
            )
            if not valid:
                raise ValueError("Invalid mock request")
            body = json.dumps({
                "translation": "大學教授進行研究。",
                "target_lang": "zh-hant",
                "model": "plamo-3-translate",
            }, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
        except Exception:
            body = b'{"error":"invalid mock request"}'
            self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


CONTAINER_CODE = r'''
from japanese_api_router import _forward
status, result = _forward("offline-9af-test-token", {
    "source_lang": "ja",
    "target_lang": "zh-hant",
    "text": "大学教授は研究を行う。",
})
if status != 200 or not result or result.get("translation") != "大學教授進行研究。":
    raise SystemExit("CONTAINER_UDS_HTTP=FAIL STATUS=%s" % status)
print("CONTAINER_UDS_HTTP=PASS")
print("MOCK_TRANSLATION=PASS")
'''


def main():
    print("=== STEP 9AF: DOCKER UDS BIND-MOUNT CHECK ===", flush=True)
    if not (ROOT / "japanese_api_router.py").is_file():
        raise RuntimeError("Staged japanese_api_router.py not found")
    if not Path(DOCKER).is_file():
        raise RuntimeError("NAS Docker CLI not found")

    print("=== FIND CURRENT IMAGE ID ===", flush=True)
    image_id = subprocess.check_output(
        ["sudo", DOCKER, "inspect", "--format", "{{.Image}}", "japanese-api"],
        text=True,
    ).strip()
    if not image_id.startswith("sha256:"):
        raise RuntimeError("Invalid Docker image ID")
    print("CURRENT_IMAGE_FOUND=PASS", flush=True)

    # Exact UDS mount shape, but in an isolated temporary directory.
    # No secrets are loaded and the running Gateway is never contacted.
    with tempfile.TemporaryDirectory(prefix="plamo-9af-", dir=str(ROOT)) as tmp:
        path = os.path.join(tmp, SOCKET_NAME)
        with UnixServer(path, FakeGateway) as server:
            os.chmod(path, 0o600)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                print("NAS_TEMP_UNIX_SOCKET=PASS", flush=True)
                cmd = [
                    "sudo", DOCKER, "run", "--rm",
                    "--network", "none", "--read-only",
                    "--security-opt", "no-new-privileges",
                    "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m",
                    "-e", "PYTHONDONTWRITEBYTECODE=1",
                    "-v", tmp + ":/run/plamo-gateway:ro",
                    "-v", str(ROOT) + ":/staging:ro",
                    "-w", "/staging",
                    "--entrypoint", "python",
                    image_id, "-c", CONTAINER_CODE,
                ]
                subprocess.run(cmd, check=True, timeout=60)
                print("DOCKER_UDS_MOUNT=PASS", flush=True)
            finally:
                server.shutdown()
                thread.join(timeout=5)

    print("TEMP_SOCKET_CLEANUP=PASS")
    print("PRODUCTION_SOURCE_MODIFIED=NO")
    print("PRODUCTION_CONTAINER_RESTARTED=NO")
    print("=== STEP 9AF COMPLETE ===")


if __name__ == "__main__":
    main()
