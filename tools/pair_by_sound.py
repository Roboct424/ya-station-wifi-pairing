#!/usr/bin/env python3
"""Генерация и проигрывание звукового кода сопряжения.

Примеры:
    python pair_by_sound.py --ssid YaRig --password 11111111
    python pair_by_sound.py --ssid Home --password secret --repeat 4 --gap 10
    python pair_by_sound.py --ssid Home --password secret --gain 0.35
    python pair_by_sound.py --ssid YaRig --password 11111111 --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sound_protocol as sp  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Звуковой код сопряжения Яндекс Станции")
    ap.add_argument("--ssid", required=True, help="имя Wi-Fi сети")
    ap.add_argument("--password", default="", help="пароль (пусто для открытой)")
    ap.add_argument("--token", default=sp.DEFAULT_TOKEN,
                    help="токен активации, колонке он не важен")
    ap.add_argument("--type", type=int, default=sp.WIFI_TYPE_WPA,
                    choices=(2, 4, 5), help="2=WPA, 4=скрытая, 5=открытая")
    ap.add_argument("--gain", type=float, default=sp.DEFAULT_GAIN,
                    help="амплитуда 0.1..0.9 (0.5 — рабочая)")
    ap.add_argument("--repeat", type=int, default=3, help="сколько раз проиграть")
    ap.add_argument("--gap", type=float, default=9.0,
                    help="пауза между повторами, с (колонка глохнет на 5-9 с)")
    ap.add_argument("--out", default="pair_sound.wav", help="куда сохранить WAV")
    ap.add_argument("--device", default=None, help="индекс устройства вывода")
    ap.add_argument("--dry-run", action="store_true", help="только показать кадр")
    a = ap.parse_args()

    frame = sp.build_frame(a.type, a.ssid, a.password, a.token)
    path = sp.make_wav(frame, a.out, gain=a.gain)
    info = sp.describe(frame, a.gain)

    print(f"SSID     : {a.ssid!r}  тип={a.type}")
    print(f"кадр     : {frame.hex()}")
    print(f"байт     : {info['frame_bytes']}  ниблов: {info['nibbles']}  "
          f"после RS: {info['encoded_nibbles']}")
    print(f"тонов    : {info['tones']}  длительность: {info['duration_sec']} с")
    print(f"WAV      : {path}  (громкость {a.gain})")

    if a.dry_run:
        return 0

    try:
        import sounddevice as sd
    except Exception as exc:  # pragma: no cover
        print(f"нет sounddevice: {exc}\nWAV сохранён, проиграйте его вручную.")
        return 0

    if a.device is not None:
        sd.default.device = (None, int(a.device))

    audio, sr = sp.read_wav(path)
    for i in range(a.repeat):
        print(f"проигрывание {i + 1}/{a.repeat}", flush=True)
        sd.play(audio, sr, blocking=True)
        if i + 1 < a.repeat:
            time.sleep(a.gap)
    print("готово")
    return 0


if __name__ == "__main__":
    sys.exit(main())
