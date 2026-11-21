#!/usr/bin/env python3
"""Регистрация Яндекс-устройства по Wi-Fi через AP HTTP (firstrund).

Устройство поднимает открытую точку доступа (обычно ``Yandex-Hub``) и
HTTP-сервер на ``192.168.43.1:8080``. Ноутбук подключается к этой точке,
после чего скрипт:

1. ``GET /info`` — берёт публичный RSA-ключ устройства (``crypto_key``);
2. шифрует пароль Wi-Fi и токен активации RSA/PKCS1 (base64);
3. ``POST /connect`` — отдаёт SSID, шифрованный пароль и токен.

Токен активации на этом шаге устройство не проверяет: подходит любая
строка. Это локальная настройка, облако не нужно.

Примеры:
    python ap_wifi.py --ssid "MyWiFi" --password "secret"
    python ap_wifi.py --ssid "MyWiFi" --password "secret" --info
    python ap_wifi.py --wired
    python ap_wifi.py --ssid "MyWiFi" --password "secret" --url http://192.168.43.1:8080

Перед запуском ноутбук должен быть подключён к точке доступа устройства
(``Yandex-Hub``), а устройство — в режиме настройки.
"""
from __future__ import annotations

import argparse
import base64
import json
import socket
import sys
import urllib.error
import urllib.request

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except Exception as exc:  # pragma: no cover
    print(f"нет cryptography: {exc}\nустановите: pip install cryptography")
    raise SystemExit(2)

DEFAULT_URL = "http://192.168.43.1:8080"
DEFAULT_TOKEN = "localpair0000000"


class ApError(RuntimeError):
    """Ошибка обмена с устройством."""


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0) -> dict:
    """GET (payload=None) или POST JSON. Возвращает разобранный JSON."""
    data = None
    headers = {"Accept": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise ApError(f"{method} {url}: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ApError(f"{method} {url}: {exc.reason}") from exc
    except socket.timeout as exc:
        raise ApError(
            f"{method} {url}: таймаут. Устройство могло уйти в Wi-Fi и не успеть "
            "ответить — проверьте, появилось ли оно в сети."
        ) from exc

    text = raw.decode("utf-8", "replace").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def get_info(base_url: str = DEFAULT_URL, timeout: float = 5.0) -> dict:
    """Возвращает ответ ``/info``: crypto_key, mac, uuid, version."""
    return http_json(base_url.rstrip("/") + "/info", timeout=timeout)


def encrypt_field(public_pem: str, value: str) -> str:
    """RSA/PKCS1 v1.5 + base64. OAEP устройство не принимает."""
    try:
        key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    except Exception as exc:
        raise ApError(f"не разобрать crypto_key: {exc}") from exc
    ciphertext = key.encrypt(value.encode("utf-8"), padding.PKCS1v15())
    return base64.b64encode(ciphertext).decode("ascii")


def build_connect_body(
    crypto_key: str,
    ssid: str,
    password: str,
    token: str = DEFAULT_TOKEN,
    wired: bool = False,
) -> dict:
    """Собирает тело ``/connect``.

    Пароль и токен всегда шифруются ключом из ``/info``. В проводном режиме
    SSID пустой, а ``wifi_type = 4`` («скрытая сеть») — именно так приложение
    помечает «работать по уже поднятому Ethernet». Без ``wifi_type`` прошивка
    подставляет 3 и пытается искать Wi-Fi, отвечая ``WIFI_SSID_NOT_FOUND``.
    """
    body: dict = {
        "ssid": "" if wired else ssid,
        "password": encrypt_field(crypto_key, "" if wired else password),
        "wifi_type": 4 if wired else 2,
        "xtoken_code": encrypt_field(crypto_key, token),
    }
    return body


def connect(
    base_url: str = DEFAULT_URL,
    ssid: str = "",
    password: str = "",
    token: str = DEFAULT_TOKEN,
    wired: bool = False,
    timeout: float = 30.0,
) -> tuple[dict, dict]:
    """Полный цикл: /info -> шифрование -> /connect. Возвращает (info, ответ)."""
    base = base_url.rstrip("/")
    info = get_info(base)
    if "crypto_key" not in info:
        raise ApError(f"/info без crypto_key: {info}")
    body = build_connect_body(info["crypto_key"], ssid, password, token, wired)
    answer = http_json(base + "/connect", payload=body, timeout=timeout)
    return info, answer


def describe(info: dict) -> str:
    mac = str(info.get("mac", "")).strip()
    return (
        f"uuid : {info.get('uuid', '?')}\n"
        f"mac  : {mac or '?'}\n"
        f"ver  : {info.get('version', '?')}\n"
        f"key  : {str(info.get('crypto_key', ''))[:42]}…"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Подключить Яндекс-устройство к Wi-Fi через AP HTTP (firstrund)",
    )
    ap.add_argument("--ssid", default="", help="имя Wi-Fi сети (для проводного режима не нужно)")
    ap.add_argument("--password", default="", help="пароль Wi-Fi (для открытой сети пустой)")
    ap.add_argument("--token", default=DEFAULT_TOKEN,
                    help="токен активации; устройство его не проверяет")
    ap.add_argument("--url", default=DEFAULT_URL, help=f"адрес устройства (по умолчанию {DEFAULT_URL})")
    ap.add_argument("--wired", action="store_true",
                    help="проводной режим: не отправлять Wi-Fi-креды")
    ap.add_argument("--info", action="store_true", help="только показать /info и выйти")
    ap.add_argument("--timeout", type=float, default=30.0,
                    help="таймаут /connect, с (по умолчанию 30)")
    ap.add_argument("--json", action="store_true", help="печатать сырой JSON ответа")
    args = ap.parse_args(argv)

    if not args.info and not args.wired and not args.ssid:
        ap.error("нужен --ssid (или --wired)")

    try:
        if args.info:
            info = get_info(args.url)
            print(describe(info))
            if args.json:
                print(json.dumps(info, ensure_ascii=False, indent=2))
            return 0

        print(f"устройство: {args.url}")
        info, answer = connect(
            base_url=args.url,
            ssid=args.ssid,
            password=args.password,
            token=args.token,
            wired=args.wired,
            timeout=args.timeout,
        )
        print(describe(info))
        print(f"режим: {'провод (Ethernet)' if args.wired else repr(args.ssid)}")
        if args.json:
            print(json.dumps(answer, ensure_ascii=False, indent=2))
        else:
            status = answer.get("status", "?")
            data = answer.get("data", "")
            code = answer.get("error_code", "")
            print(f"ответ: status={status} data={data!r} error_code={code!r}")
            if status == "ok":
                print("готово: устройство должно подключиться к сети.")
            elif data == "WIFI_TIMEOUT":
                print("устройство не успело подключиться (нет сети/неверный пароль).")
            elif data == "WIFI_SSID_NOT_FOUND":
                print("устройство не видит SSID; проверьте диапазон 2.4 ГГц.")
        return 0 if answer.get("status") == "ok" else 1

    except ApError as exc:
        print(f"ошибка: {exc}")
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
