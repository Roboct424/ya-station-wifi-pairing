#!/usr/bin/env python3
"""Единый инструмент: звук + Wi-Fi через AP HTTP.

    python station_pairing.py sound --ssid "MyWiFi" --password "secret"
    python station_pairing.py wifi  --ssid "MyWiFi" --password "secret"
    python station_pairing.py gui

``sound`` — колонка принимает SSID/пароль из акустического сигнала (4.5 с).
``wifi``  — устройство с точкой доступа (``Yandex-Hub``, 192.168.43.1:8080)
            принимает те же креды по HTTP, зашифрованные RSA/PKCS1.
``gui``   — окно с двумя вкладками.

Оба способа локальные: приложение и облако не нужны, токен активации
на этих шагах не проверяется.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ap_wifi  # noqa: E402
import pair_by_sound  # noqa: E402

VERSION = "1.2.0"

USAGE = f"""Единый инструмент сопряжения Яндекс Станции (v{VERSION})

  station_pairing sound --ssid "MyWiFi" --password "secret"
      звуковой код: сгенерировать/проиграть WAV (4.5 с)

  station_pairing wifi --ssid "MyWiFi" --password "secret"
      Wi-Fi через AP HTTP (192.168.43.1:8080, RSA/PKCS1)

  station_pairing wifi --wired
      проводной режим (Ethernet), без Wi-Fi-кредов

  station_pairing gui
      окно с двумя вкладками

Подробности: docs/01-sound-protocol.md, docs/05-ap-http.md.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    if args[0] in ("-V", "--version", "version"):
        print(VERSION)
        return 0

    cmd, rest = args[0], args[1:]
    if cmd == "sound":
        return pair_by_sound.main(rest)
    if cmd == "wifi":
        return ap_wifi.main(rest)
    if cmd == "gui":
        from station_pairing_gui import App

        App().mainloop()
        return 0

    print(f"неизвестная команда: {cmd}\n")
    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
