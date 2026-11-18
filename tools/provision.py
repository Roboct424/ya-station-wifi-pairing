#!/usr/bin/env python3
"""Провижининг «под ключ»: играет звук, пока колонка не появится в сети.

Никаких серверов, рута и приложения: только динамик рядом с колонкой.

    python provision.py --ssid YaRig --password 11111111
    python provision.py --ssid Home --password secret --timeout 180 --mac-prefix b8-87-6e

Успех определяется по появлению новой записи в ARP-таблице (колонка получила
адрес по DHCP и ответила). Если хотите проверять конкретную модель — укажите
--mac-prefix.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sound_protocol as sp  # noqa: E402


def arp_table() -> dict[str, str]:
    """{ip: mac} из arp -a."""
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True,
                             errors="replace", timeout=10).stdout
    except Exception:
        return {}
    table = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].count(".") == 3:
            mac = parts[1].lower()
            if "-" in mac or ":" in mac:
                table[parts[0]] = mac
    return table


def find_new(before: dict[str, str], prefix: str | None) -> tuple[str, str] | None:
    after = arp_table()
    for ip, mac in after.items():
        if ip in before:
            continue
        if prefix and prefix.lower() not in mac:
            continue
        return ip, mac
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Авто-сопряжение колонки по звуку")
    ap.add_argument("--ssid", required=True)
    ap.add_argument("--password", default="")
    ap.add_argument("--token", default=sp.DEFAULT_TOKEN)
    ap.add_argument("--type", type=int, default=sp.WIFI_TYPE_WPA, choices=(2, 4, 5))
    ap.add_argument("--gains", default="0.5,0.35,0.65,0.8",
                    help="порядок перебора громкости")
    ap.add_argument("--timeout", type=float, default=150)
    ap.add_argument("--gap", type=float, default=10)
    ap.add_argument("--mac-prefix", default=None,
                    help="например b8-87-6e, чтобы не спутать с другими устройствами")
    ap.add_argument("--out", default="provision.wav")
    a = ap.parse_args()

    try:
        import sounddevice as sd
    except Exception as exc:  # pragma: no cover
        print(f"нет sounddevice: {exc}")
        return 1

    gains = [float(x) for x in a.gains.split(",") if x.strip()]
    before = arp_table()
    deadline = time.time() + a.timeout
    attempt = 0

    print(f"SSID={a.ssid}  таймаут={a.timeout:.0f}s  громкости={gains}")
    while time.time() < deadline:
        gain = gains[attempt % len(gains)]
        attempt += 1

        frame = sp.build_frame(a.type, a.ssid, a.password, a.token)
        path = sp.make_wav(frame, a.out, gain=gain)
        audio, sr = sp.read_wav(path)
        print(f"[{attempt}] играю (gain={gain}) …", flush=True)
        sd.play(audio, sr, blocking=True)

        for _ in range(int(a.gap)):
            time.sleep(1)
            found = find_new(before, a.mac_prefix)
            if found:
                ip, mac = found
                print(f"\nГОТОВО: колонка в сети {ip} ({mac}) — "
                      f"попытка {attempt}, gain={gain}")
                print(f"кадр: {frame.hex()}")
                return 0
        print("   пока не видно", flush=True)

    print("\nне дождались. Проверьте: колонка в режиме настройки, громкость не на нуле, "
          "она рядом; при необходимости --gain/--gains.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
