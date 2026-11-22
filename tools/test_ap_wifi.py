#!/usr/bin/env python3
"""Проверка ap_wifi.py на локальном mock-сервере (без устройства).

Запуск:
    python test_ap_wifi.py
"""
from __future__ import annotations

import base64
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ap_wifi  # noqa: E402

PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_PEM = PRIVATE.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")

SEEN: dict = {}


def decrypt(value: str) -> str:
    raw = base64.b64decode(value)
    return PRIVATE.decrypt(raw, padding.PKCS1v15()).decode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401
        pass

    def _json(self, obj: dict, code: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/info":
            self._json({
                "crypto_key": PUBLIC_PEM,
                "mac": "3c:0b:4f:00:00:01\n",
                "uuid": "TEST0000000001",
                "version": "test",
            })
        elif self.path == "/ssid":
            self._json({"ssid": [
                {"ssid": "Home", "level": -40, "secure": True},
                {"ssid": "Other", "level": -70, "secure": True},
            ]})
        else:
            self._json({"status": "ok"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        SEEN.clear()
        SEEN["ssid"] = body.get("ssid")
        SEEN["password"] = decrypt(body["password"]) if "password" in body else None
        SEEN["token"] = decrypt(body["xtoken_code"])
        SEEN["wifi_type"] = body.get("wifi_type")
        SEEN["hidden_ssid"] = body.get("hidden_ssid")
        SEEN["stop_access_point"] = body.get("stop_access_point")
        self._json({"status": "ok"})


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    failures = 0
    try:
        info, answer = ap_wifi.connect(url, "MyWiFi", "secret123", "token-xyz")
        print("info:", info.get("uuid"), info.get("version"))
        print("answer:", answer)
        print("seen:", SEEN)
        if info.get("uuid") != "TEST0000000001":
            print("FAIL: uuid"); failures += 1
        if answer.get("status") != "ok":
            print("FAIL: status"); failures += 1
        if SEEN.get("ssid") != "MyWiFi":
            print("FAIL: ssid"); failures += 1
        if SEEN.get("password") != "secret123":
            print("FAIL: password"); failures += 1
        if SEEN.get("token") != "token-xyz":
            print("FAIL: token"); failures += 1
        if SEEN.get("wifi_type") != "WPA" or SEEN.get("hidden_ssid") is not False:
            print("FAIL: wireless type"); failures += 1
        if SEEN.get("stop_access_point") is not True:
            print("FAIL: wireless stop_access_point"); failures += 1

        _, answer = ap_wifi.connect(url, wired=True)
        print("wired:", answer, "seen:", SEEN)
        if SEEN.get("ssid") != "Home" or SEEN.get("password") != "":
            print("FAIL: wired body (ssid must be a non-empty placeholder)")
            failures += 1
        if SEEN.get("wifi_type") != "NONE":
            print("FAIL: wired wifi_type"); failures += 1
        if SEEN.get("hidden_ssid") is not False:
            print("FAIL: wired hidden_ssid"); failures += 1
        if SEEN.get("stop_access_point") is not True:
            print("FAIL: wired stop_access_point"); failures += 1
        if SEEN.get("token") != ap_wifi.DEFAULT_TOKEN:
            print("FAIL: wired token"); failures += 1
    finally:
        server.shutdown()
        server.server_close()

    print("OK" if failures == 0 else f"FAILED: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
